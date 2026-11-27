"""GitHub Actions OIDC verification for the local webhook."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import jwt


ISSUER = "https://token.actions.githubusercontent.com"
JWKS_URL = f"{ISSUER}/.well-known/jwks"


class AuthenticationError(ValueError):
    """Raised when a GitHub OIDC token is not trusted."""


@dataclass(frozen=True, slots=True)
class OIDCPolicy:
    audience: str
    repository: str
    ref: str
    leeway_seconds: int = 30


class GitHubOIDCVerifier:
    """Verify GitHub Actions ID tokens against GitHub's published JWKS."""

    def __init__(self, policy: OIDCPolicy) -> None:
        if not policy.audience or not policy.repository or not policy.ref:
            raise ValueError("OIDC audience, repository and ref must be configured")
        self.policy = policy
        self._jwks = jwt.PyJWKClient(JWKS_URL, cache_jwk_set=True, lifespan=300)

    def verify(self, token: str) -> dict[str, Any]:
        if not token or len(token) > 16_384:
            raise AuthenticationError("missing or oversized bearer token")
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.policy.audience,
                issuer=ISSUER,
                leeway=self.policy.leeway_seconds,
                options={
                    "require": ["exp", "iat", "iss", "aud", "jti", "repository", "ref"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                },
            )
        except (jwt.PyJWTError, Exception) as exc:
            # Network/JWKS errors are authentication failures too; never fail open.
            raise AuthenticationError("OIDC token verification failed") from exc

        if claims.get("repository") != self.policy.repository:
            raise AuthenticationError("OIDC repository claim mismatch")
        if claims.get("ref") != self.policy.ref:
            raise AuthenticationError("OIDC ref claim mismatch")
        if not isinstance(claims.get("jti"), str) or not claims["jti"]:
            raise AuthenticationError("OIDC token has no jti")
        now = int(time.time())
        if claims.get("iat", now + 1) > now + self.policy.leeway_seconds:
            raise AuthenticationError("OIDC token issued in the future")
        return claims
