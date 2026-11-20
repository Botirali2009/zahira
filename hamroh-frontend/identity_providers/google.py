"""Google OAuth2 (authorization-code flow, no SDK — just `requests`).

Three network-facing pieces: build the consent-screen URL, exchange the
returned `code` for tokens, then ask Google's userinfo endpoint who signed
in. Like every other network integration in this codebase, a bad code, a
timeout, or a malformed response never crashes the request — the caller
(`routes/auth_pages.py`) turns a `None`/exception into a clean redirect back
to the login page with an error message.
"""

from urllib.parse import urlencode

import requests

import sys

from config import Config
from identity_providers.base import ExternalProfile, register

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
SCOPE = "openid email profile"
TIMEOUT_SECONDS = 10


def is_configured():
    return bool(Config.GOOGLE_CLIENT_ID and Config.GOOGLE_CLIENT_SECRET
                and Config.GOOGLE_REDIRECT_URI)


def authorize_url(state):
    params = {
        "client_id": Config.GOOGLE_CLIENT_ID,
        "redirect_uri": Config.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return AUTHORIZE_URL + "?" + urlencode(params)


class GoogleAuthError(Exception):
    pass


def fetch_profile(code):
    """Exchange an authorization `code` for the signed-in user's profile."""
    if not is_configured():
        raise GoogleAuthError("not_configured")

    try:
        token_response = requests.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": Config.GOOGLE_CLIENT_ID,
                "client_secret": Config.GOOGLE_CLIENT_SECRET,
                "redirect_uri": Config.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=TIMEOUT_SECONDS,
        )
        token_payload = token_response.json()
        access_token = token_payload.get("access_token")
        if not access_token:
            raise GoogleAuthError("token_exchange_failed")

        profile_response = requests.get(
            USERINFO_URL,
            headers={"Authorization": "Bearer %s" % access_token},
            timeout=TIMEOUT_SECONDS,
        )
        profile = profile_response.json()
    except requests.RequestException as exc:
        raise GoogleAuthError("network_error") from exc

    sub = profile.get("sub")
    if not sub:
        raise GoogleAuthError("no_profile")

    return ExternalProfile(
        provider="google",
        external_id=sub,
        full_name=profile.get("name") or profile.get("email") or "Google user",
        phone=None,  # not returned by the openid/email/profile scopes
        email=profile.get("email"),
        raw=profile,
    )


register("google", sys.modules[__name__])
