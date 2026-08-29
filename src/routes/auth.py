"""Authentication endpoints for Phase 7.

Implements POST /auth/register, POST /auth/login, and GET /auth/me.
Zero plaintext passwords stored or logged. /auth/me never returns password hashes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, hash_password, verify_password
from db import get_db
from models_db import Lab, Scientist
from schemas import LoginRequest, RegisterRequest, ScientistOut, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Registers a new scientist account, creates or links a lab, and returns an access token."""
    # Check if email is already taken
    existing = db.execute(select(Scientist).where(Scientist.email == body.email.lower())).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Resolve or create lab
    lab_name = (body.lab_name or "Sample AMR Research Unit").strip()
    lab = db.execute(select(Lab).where(Lab.name == lab_name)).scalar_one_or_none()
    if lab is None:
        lab = Lab(name=lab_name)
        db.add(lab)
        db.flush()

    pwd_hash = hash_password(body.password)
    scientist = Scientist(
        lab_id=lab.id,
        email=body.email.lower(),
        full_name=body.full_name.strip(),
        password_hash=pwd_hash,
        role="scientist",
        is_seeded=False,
    )
    db.add(scientist)
    db.commit()
    db.refresh(scientist)

    access_token = create_access_token(data={"sub": str(scientist.id), "email": scientist.email})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        scientist=ScientistOut.model_validate(scientist),
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates a scientist via email and password, returning a JWT token."""
    scientist = db.execute(select(Scientist).where(Scientist.email == body.email.lower())).scalar_one_or_none()
    if scientist is None or not verify_password(body.password, scientist.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(scientist.id), "email": scientist.email})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        scientist=ScientistOut.model_validate(scientist),
    )


@router.get("/me", response_model=ScientistOut)
def get_me(current_user: Scientist = Depends(get_current_user)):
    """Returns the authenticated scientist's profile. Never returns password_hash."""
    return ScientistOut.model_validate(current_user)
