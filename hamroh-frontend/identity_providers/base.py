"""Identity provider registry — new extension point added in Module A.

Every login method (Google, Telegram, and eventually dmed) satisfies the same
contract: given whatever raw data the provider hands back, produce an
`ExternalProfile`. The HTTP shape of each provider's flow differs wildly
(Google is a redirect + code exchange, Telegram is a signed widget payload,
dmed is unknown until it exists) — the contract is deliberately just the
*output*, not the flow, so `services/auth_service.py` and every route never
need to know which provider was used.

Adding a fourth provider later = a new file here + a route that calls it.
Nothing in `core/auth.py` or `services/auth_service.py` changes.
"""

from dataclasses import dataclass, field


@dataclass
class ExternalProfile:
    provider: str
    external_id: str
    full_name: str
    phone: str = None
    email: str = None
    raw: dict = field(default_factory=dict)


class ProviderUnavailable(Exception):
    """Raised by a stubbed-out provider (dmed) when someone tries to use it."""


REGISTRY = {}


def register(key, module):
    REGISTRY[key] = module


def get(key):
    return REGISTRY.get(key)
