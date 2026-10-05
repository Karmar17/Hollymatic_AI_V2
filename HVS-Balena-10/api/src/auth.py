"""Autenticacion JWT: creacion/validacion de tokens y dependencia de FastAPI.

Un solo usuario, definido por API_USERNAME + API_PASSWORD_HASH (hash bcrypt) en el entorno.
Access token corto y refresh token largo; se distinguen por el claim "type".
"""
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from src.config import config

# tokenUrl apunta al endpoint de login para que /docs pueda autenticar.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

ACCESS = "access"
REFRESH = "refresh"

# bcrypt solo usa los primeros 72 bytes del password (y bcrypt>=5 lanza si se exceden).
_BCRYPT_MAX_BYTES = 72


def verify_credentials(username: str, password: str) -> bool:
    """Valida usuario+password contra las credenciales configuradas.

    Prioridad: API_PASSWORD (texto plano en .env). Si esta vacio, se usa el
    respaldo API_PASSWORD_HASH (hash bcrypt; balena/prod).
    """
    if not config.API_USERNAME or username != config.API_USERNAME:
        return False
    # 1) Password en claro (API_PASSWORD): comparacion en tiempo constante.
    if config.API_PASSWORD:
        return secrets.compare_digest(password, config.API_PASSWORD)
    # 2) Respaldo: hash bcrypt (API_PASSWORD_HASH).
    if config.API_PASSWORD_HASH:
        try:
            return bcrypt.checkpw(
                password.encode("utf-8")[:_BCRYPT_MAX_BYTES],
                config.API_PASSWORD_HASH.encode("utf-8"),
            )
        except ValueError:
            # Hash mal formado en el entorno.
            return False
    return False


def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def create_access_token(subject: str) -> str:
    return _create_token(
        subject, ACCESS, timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject, REFRESH, timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def _decode(token: str, expected_type: str) -> dict:
    """Decodifica y valida un token; exige el claim type esperado."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales invalidas o token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM],
        )
    except JWTError:
        raise credentials_error
    if payload.get("type") != expected_type or not payload.get("sub"):
        raise credentials_error
    return payload


def decode_refresh_token(token: str) -> str:
    """Valida un refresh token y devuelve el subject (username)."""
    return _decode(token, REFRESH)["sub"]


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Dependencia: exige un access token valido. Devuelve el username."""
    return _decode(token, ACCESS)["sub"]
