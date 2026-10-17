
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


def hacher_mot_de_passe(password: str) -> str:
    return password_hash.hash(password)


def verifier_mot_de_passe(
    password: str,
    hashed_password: str,
) -> bool:
    return password_hash.verify(password, hashed_password)


def creer_access_token(
    user_id: int,
    role: str,
    expires_minutes: int = 30,
) -> str:
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY n'est pas configurée")

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decoder_access_token(token: str) -> dict:
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY n'est pas configurée")

    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
