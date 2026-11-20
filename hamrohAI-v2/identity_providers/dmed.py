"""dmed — placeholder identity provider.

Satisfies the same shape as `google.py`/`telegram.py` (`is_configured()`,
`fetch_profile(...)`) so wiring the real thing in later is a matter of
filling this file in — no route, template, or `auth_service` change needed.
Always reports unconfigured while `FEATURE_DMED_AUTH` is off; the login page
uses that to render the button disabled with an honest "hozircha mavjud
emas" message instead of a broken link.
"""

import sys

from config import features
from identity_providers.base import ProviderUnavailable, register


def is_configured():
    return features.enabled("dmed_auth")


def fetch_profile(*_args, **_kwargs):
    raise ProviderUnavailable("dmed integratsiyasi hozircha mavjud emas.")


register("dmed", sys.modules[__name__])
