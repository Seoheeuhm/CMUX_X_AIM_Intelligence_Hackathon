import os
import requests as _requests
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, jwk, JWTError
from dotenv import load_dotenv

load_dotenv()

_bearer = HTTPBearer(auto_error=False)
_jwks_cache: list = []


def _get_jwks() -> list:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    supabase_url = os.environ["SUPABASE_URL"]
    r = _requests.get(f"{supabase_url}/auth/v1/.well-known/jwks.json", timeout=10)
    r.raise_for_status()
    _jwks_cache = r.json().get("keys", [])
    return _jwks_cache


def _decode(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        kid = header.get("kid")

        if alg in ("ES256", "RS256"):
            keys = _get_jwks()
            matched = next((k for k in keys if k.get("kid") == kid), None) or (keys[0] if keys else None)
            if not matched:
                raise JWTError("No matching public key found")
            public_key = jwk.construct(matched)
            return jwt.decode(token, public_key, algorithms=[alg], audience="authenticated")
        else:
            return jwt.decode(
                token,
                os.environ["SUPABASE_JWT_SECRET"],
                algorithms=["HS256"],
                audience="authenticated",
            )
    except (JWTError, Exception):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return _decode(creds.credentials)


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    if not creds:
        return None
    try:
        return _decode(creds.credentials)
    except HTTPException:
        return None
