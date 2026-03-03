from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Annotated

from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class User(BaseModel):
    username: str
    role: str


def _seed_users() -> dict[str, dict[str, str]]:
    admin_pass = os.getenv("ADMIN_PASSWORD", "Admin@123")
    operator_pass = os.getenv("OPERATOR_PASSWORD", "Operator@123")
    return {
        "admin": {"hashed_password": pwd_context.hash(admin_pass), "role": "Admin"},
        "operator": {"hashed_password": pwd_context.hash(operator_pass), "role": "Operator"},
    }


FAKE_USERS_DB = _seed_users()


@lru_cache
def get_secret_key() -> str:
    return os.getenv("JWT_SECRET_KEY", "change-me-in-production-super-secret-key")


@lru_cache
def get_fernet() -> Fernet:
    raw = os.getenv("CRED_ENCRYPTION_KEY")
    if raw:
        key = raw.encode()
    else:
        key = Fernet.generate_key()
    return Fernet(key)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str) -> User | None:
    record = FAKE_USERS_DB.get(username)
    if not record:
        return None
    if not verify_password(password, record["hashed_password"]):
        return None
    return User(username=username, role=record["role"])


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        return User(username=username, role=role)
    except JWTError as exc:
        raise credentials_exception from exc


def require_role(user: User, allowed: set[str]) -> None:
    if user.role not in allowed:
        raise HTTPException(status_code=403, detail="Insufficient privilege")


def encrypt_secret(plain_text: str) -> str:
    return get_fernet().encrypt(plain_text.encode()).decode()


def decrypt_secret(cipher_text: str) -> str:
    return get_fernet().decrypt(cipher_text.encode()).decode()
