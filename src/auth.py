"""Authentication and security utilities for Phase 7.

Handles bcrypt password hashing, HS256 JWT access tokens, and FastAPI current-user
dependencies.

Rules:
1. Passwords: Never store or log plaintext passwords. Never return password hashes.
2. Tokens: JWT with HS256, ~12 hour expiry, reading secret from env var PHARMAMIND_JWT_SECRET.
3. Auth is additive: get_current_user enforces authentication, while get_current_user_optional
   allows endpoints to adapt gracefully when unauthenticated.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

import config as C
from db import get_db
from models_db import Scientist

def _load_jwt_secret() -> str:
    """Never ship a hardcoded signing key in a public repository.

    A committed default means anyone who reads the source can forge a token for any
    deployment that forgot to set the environment variable. Order of preference:
      1. PHARMAMIND_JWT_SECRET from the environment (what a real deployment uses);
      2. a random key generated on first run and cached in a gitignored local file, so
         restarting the API during a demo does not log everybody out;
      3. an in-memory random key if the file cannot be written.
    """
    env = os.getenv("PHARMAMIND_JWT_SECRET")
    if env:
        return env

    key_file = C.DATA / ".jwt_secret"
    try:
        if key_file.exists():
            cached = key_file.read_text(encoding="utf-8").strip()
            if cached:
                return cached
        generated = secrets.token_urlsafe(48)
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(generated, encoding="utf-8")
        print("Note: generated a local JWT signing key at data/.jwt_secret. "
              "Set PHARMAMIND_JWT_SECRET for any real deployment.")
        return generated
    except OSError:
        print("Warning: could not persist a JWT key; using an in-memory one. "
              "Tokens will not survive a restart.")
        return secrets.token_urlsafe(48)


JWT_SECRET = _load_jwt_secret()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 12

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=True)
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


# --- 1. Password Hashing -----------------------------------------------------

def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with automatic salt generation."""
    pwd_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored bcrypt hash."""
    pwd_bytes = plain_password.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


# --- 2. JWT Token Management -------------------------------------------------

def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Encodes a JWT payload with an expiration timestamp."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decodes and validates a JWT token signature and expiration."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None


# --- 3. FastAPI Current-User Dependencies -----------------------------------

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Scientist:
    """Dependency that requires a valid JWT token and returns the authenticated Scientist."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    scientist_id_str = payload.get("sub")
    if scientist_id_str is None:
        raise credentials_exception

    try:
        scientist_id = int(scientist_id_str)
    except (ValueError, TypeError):
        raise credentials_exception

    scientist = db.get(Scientist, scientist_id)
    if scientist is None:
        raise credentials_exception

    return scientist


def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> Scientist | None:
    """Optional dependency that returns the Scientist if a valid token is provided, else None."""
    if not token:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None

    scientist_id_str = payload.get("sub")
    if scientist_id_str is None:
        return None

    try:
        scientist_id = int(scientist_id_str)
    except (ValueError, TypeError):
        return None

    return db.get(Scientist, scientist_id)
