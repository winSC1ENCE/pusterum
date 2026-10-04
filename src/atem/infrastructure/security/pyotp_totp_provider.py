"""pyotp-based implementation of ITotpProvider (RFC 6238, 30 s steps, 6 digits)."""

import hmac
import time

import pyotp

from atem.domain.interfaces.totp_provider import ITotpProvider

ISSUER = "PUSTERUM"
STEP_SECONDS = 30
# Accept the previous and next time step to tolerate small clock drift on phones.
DRIFT_STEPS = 1


class PyotpTotpProvider(ITotpProvider):
    """TOTP with replay protection via the last accepted time step."""

    def generate_secret(self) -> str:
        return pyotp.random_base32()

    def provisioning_uri(self, secret: str, account_name: str) -> str:
        return pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=ISSUER)

    def verify(self, secret: str, code: str, last_used_step: int | None) -> int | None:
        code = code.strip().replace(" ", "")
        if not code.isdigit():
            return None
        totp = pyotp.TOTP(secret)
        current = int(time.time()) // STEP_SECONDS
        for step in range(current - DRIFT_STEPS, current + DRIFT_STEPS + 1):
            if last_used_step is not None and step <= last_used_step:
                continue
            if hmac.compare_digest(totp.at(step * STEP_SECONDS), code):
                return step
        return None
