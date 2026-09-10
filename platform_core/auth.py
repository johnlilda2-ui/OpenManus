from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform_core.database import get_db
from platform_core.models import User
from platform_core.secrets import get_secret
from platform_core.settings import settings


password_hash = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=True)


def _jwt_secret() -> str:
    if settings.jwt_secret_file:
        try:
            return get_secret(settings.jwt_secret_file, required=True)
        except Exception:
            pass
    return settings.jwt_secret


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": user_id, "type": "access", "exp": expires}
    return jwt.encode(payload, _jwt_secret(), algorithm=settings.jwt_algorithm)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    session: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, _jwt_secret(), algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if not user_id or payload.get("type") != "access":
            raise credentials_exception
    except jwt.PyJWTError as exc:
        raise credentials_exception from exc

    user = await session.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        raise credentials_exception
    return user
