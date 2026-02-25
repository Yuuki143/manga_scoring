"""Authentication endpoints for the MMIP API.

Provides JWT-based login via the OAuth2 password flow and an admin-only
user registration endpoint.

Routes
------
POST /auth/token    – Exchange email/password credentials for a JWT.
POST /auth/register – Create a new user account (ADMIN role required).
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.audit import log_action
from app.auth.dependencies import (
    create_access_token,
    get_current_user,
    get_password_hash,
    require_role,
    verify_password,
)
from app.database import get_db
from app.models.publisher import Publisher
from app.models.user import User, UserRole
from app.schemas.auth import Token, UserCreate, UserResponse

router = APIRouter()


@router.post(
    "/token",
    response_model=Token,
    summary="Login and obtain a JWT access token",
    description=(
        "Authenticate with an email address and password. "
        "On success a signed JWT Bearer token is returned that must be "
        "included in the ``Authorization`` header of subsequent requests."
    ),
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Validate credentials and return a JWT access token.

    Args:
        form_data: OAuth2 ``username`` (treated as email) and ``password``.
        db: Database session injected by FastAPI.

    Raises:
        HTTPException 401: If the email is not found, the password does not
            match, or the user account is inactive.
    """
    user: User | None = (
        db.query(User).filter(User.email == form_data.username).first()
    )

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last_login timestamp
    user.last_login = datetime.utcnow()
    db.commit()

    # Record audit entry
    log_action(
        db=db,
        action="login",
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        publisher_id=user.publisher_id,
    )

    token = create_access_token(
        data={"sub": user.email, "publisher_id": user.publisher_id, "role": user.role}
    )
    return Token(access_token=token, token_type="bearer")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (admin only)",
    description=(
        "Create a new platform user associated with an existing publisher. "
        "Requires the ``ADMIN`` role. The password is stored as a bcrypt hash; "
        "the plaintext is never persisted."
    ),
)
async def register(
    user_data: UserCreate,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Create a new user account.

    Args:
        user_data: Registration payload containing email, password, full name,
            publisher ID and optional role.
        current_user: Authenticated admin user performing the registration.
        db: Database session injected by FastAPI.

    Raises:
        HTTPException 400: If a user with the supplied email already exists.
        HTTPException 404: If the target publisher does not exist or is inactive.
    """
    # Validate publisher exists and is active
    publisher: Publisher | None = (
        db.query(Publisher)
        .filter(Publisher.id == user_data.publisher_id, Publisher.is_active.is_(True))
        .first()
    )
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Publisher with id {user_data.publisher_id} not found or inactive",
        )

    # Check for duplicate email
    existing: User | None = (
        db.query(User).filter(User.email == user_data.email).first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    # Normalise role string to enum
    role_str = user_data.role.upper() if user_data.role else "VIEWER"
    try:
        role = UserRole(role_str)
    except ValueError:
        valid_roles = [r.value for r in UserRole]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{user_data.role}'. Valid roles: {valid_roles}",
        )

    new_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        publisher_id=user_data.publisher_id,
        role=role,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_action(
        db=db,
        action="register",
        resource_type="user",
        resource_id=str(new_user.id),
        user_id=current_user.id,
        publisher_id=current_user.publisher_id,
        details={
            "new_user_id": new_user.id,
            "new_user_email": new_user.email,
            "new_user_publisher_id": new_user.publisher_id,
            "new_user_role": new_user.role.value,
        },
    )

    return UserResponse.model_validate(new_user)
