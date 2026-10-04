from __future__ import annotations

import hmac

from fastapi import Header, HTTPException


def auth_dependency(expected: str):
    async def require_local_auth(authorization: str | None = Header(default=None)) -> None:
        if not expected:
            raise HTTPException(status_code=503, detail="Local API key is not configured")
        supplied = authorization.removeprefix("Bearer ") if authorization else ""
        if not supplied or not hmac.compare_digest(supplied, expected):
            raise HTTPException(status_code=401, detail="Invalid local bearer token",
                                headers={"WWW-Authenticate": "Bearer"})
    return require_local_auth
