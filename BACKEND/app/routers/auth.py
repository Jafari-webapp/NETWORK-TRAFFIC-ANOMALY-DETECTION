from datetime import datetime, timezone as dt_timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database.connection import get_db
from app.models.system_user import SystemUser
from app.schemas.auth import (
    ChangePasswordRequest, CurrentUser, LoginRequest, PreferencesUpdateRequest,
    ProfileUpdateRequest, TokenResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(SystemUser).filter_by(username=payload.username).one_or_none()

    password_ok = False
    if user is not None and user.is_active:
        try:
            password_ok = verify_password(payload.password, user.password_hash)
        except ValueError:
            # Stored hash isn't a value passlib can parse (e.g. corrupted/blank/
            # non-bcrypt). Treat it as a wrong password instead of a 500.
            password_ok = False

    if user is None or not user.is_active or not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    user.last_login_at = datetime.now(dt_timezone.utc)
    db.commit()

    token = create_access_token(subject=user.username, extra_claims={"role": user.role})
    return TokenResponse(access_token=token, username=user.username, full_name=user.full_name)


@router.get("/me", response_model=CurrentUser)
def me(current_user: SystemUser = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=CurrentUser)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: SystemUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    current_user: SystemUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        current_ok = verify_password(payload.current_password, current_user.password_hash)
    except ValueError:
        current_ok = False
    if not current_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password is incorrect")

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()


@router.get("/preferences", response_model=CurrentUser)
def get_preferences(current_user: SystemUser = Depends(get_current_user)):
    return current_user


@router.put("/preferences", response_model=CurrentUser)
def update_preferences(
    payload: PreferencesUpdateRequest,
    current_user: SystemUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user
