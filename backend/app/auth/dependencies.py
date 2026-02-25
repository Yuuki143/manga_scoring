"""FastAPI authentication and authorization dependencies for MMIP.

Provides JWT-based user authentication, API-key-based publisher
authentication, and role/tier enforcement via dependency factories.
"""

from datetime import datetime, timedelta
from typing import Callable

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.publisher import Publisher, PublisherTier
from app.models.user import User, UserRole

# ---------------------------------------------------------------------------
# Security scheme instances
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# Tier and role ordering
# ---------------------------------------------------------------------------

_TIER_ORDER: dict[str, int] = {
    PublisherTier.BASIC: 0,
    PublisherTier.PRO: 1,
    PublisherTier.ENTERPRISE: 2,
}

_ROLE_ORDER: dict[str, int] = {
    UserRole.VIEWER: 0,
    UserRole.EDITOR: 1,
    UserRole.ADMIN: 2,
}


# ---------------------------------------------------------------------------
# Token utilities
# ---------------------------------------------------------------------------


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token.

    Args:
        data: Claims to embed in the token payload.
        expires_delta: Lifetime override; defaults to
            ``settings.ACCESS_TOKEN_EXPIRE_MINUTES``.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches *hashed_password*.

    Args:
        plain_password: Raw password supplied by the user.
        hashed_password: Bcrypt-hashed value stored in the database.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Return the bcrypt hash of *password*.

    Args:
        password: Raw password to hash.
    """
    return pwd_context.hash(password)


# ---------------------------------------------------------------------------
# Core authentication dependencies
# ---------------------------------------------------------------------------


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: validate Bearer JWT and return the active User.

    Raises:
        HTTPException 401: If the token is missing, malformed, expired, or
            references a non-existent / inactive user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user: User | None = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user_or_api_key(
    token: str | None = Depends(oauth2_scheme),
    api_key: str | None = Security(api_key_header),
    db: Session = Depends(get_db),
) -> tuple[User | None, Publisher | None]:
    """FastAPI dependency: authenticate via JWT *or* API key.

    Tries JWT first; if no valid JWT is present, falls back to the
    ``X-API-Key`` header. At least one credential must be valid.

    Returns:
        A ``(user, publisher)`` tuple.  Exactly one element will be non-None:
        JWT auth sets *user* (publisher can be derived from ``user.publisher``);
        API-key auth sets *publisher* only.

    Raises:
        HTTPException 401: If neither JWT nor API key resolves to an active
            entity.
    """
    # --- Try JWT first ---
    if token:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            email: str | None = payload.get("sub")
            if email:
                user: User | None = db.query(User).filter(User.email == email).first()
                if user and user.is_active:
                    return (user, None)
        except JWTError:
            pass  # Fall through to API key check

    # --- Try API key ---
    if api_key:
        publisher: Publisher | None = (
            db.query(Publisher)
            .filter(Publisher.api_key == api_key, Publisher.is_active.is_(True))
            .first()
        )
        if publisher:
            return (None, publisher)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ---------------------------------------------------------------------------
# Dependency factories
# ---------------------------------------------------------------------------


def require_tier(minimum_tier: str) -> Callable:
    """Dependency factory: enforce a minimum publisher subscription tier.

    The requesting entity must be a Publisher (authenticated via API key) or
    a User whose linked Publisher meets the tier requirement.

    Args:
        minimum_tier: Minimum required tier string (``"BASIC"``, ``"PRO"``,
            or ``"ENTERPRISE"``).

    Returns:
        A FastAPI dependency function that resolves to the authenticated
        ``(user, publisher)`` tuple or raises HTTP 403.

    Example::

        @router.get("/premium-endpoint")
        async def premium(
            auth=Depends(require_tier("PRO")),
        ):
            ...
    """
    min_order = _TIER_ORDER.get(minimum_tier.upper(), 0)

    async def _check_tier(
        auth: tuple[User | None, Publisher | None] = Depends(
            get_current_user_or_api_key
        ),
        db: Session = Depends(get_db),
    ) -> tuple[User | None, Publisher | None]:
        user, publisher = auth

        # Determine the publisher to check
        resolved_publisher: Publisher | None = publisher
        if user is not None and resolved_publisher is None:
            resolved_publisher = (
                db.query(Publisher)
                .filter(Publisher.id == user.publisher_id)
                .first()
            )

        if resolved_publisher is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Publisher account not found",
            )

        tier_value = _TIER_ORDER.get(resolved_publisher.tier.upper()
                                     if isinstance(resolved_publisher.tier, str)
                                     else resolved_publisher.tier.value, -1)
        if tier_value < min_order:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"This feature requires the {minimum_tier} tier or higher. "
                    f"Current tier: {resolved_publisher.tier}"
                ),
            )
        return auth

    return _check_tier


def require_role(minimum_role: str) -> Callable:
    """Dependency factory: enforce a minimum user role.

    Only JWT-authenticated Users are subject to role checks. Publisher API
    keys are not associated with a role and will be rejected by this
    dependency.

    Args:
        minimum_role: Minimum required role string (``"VIEWER"``, ``"EDITOR"``,
            or ``"ADMIN"``).

    Returns:
        A FastAPI dependency function that resolves to the authenticated
        ``User`` or raises HTTP 403.

    Example::

        @router.post("/titles")
        async def create_title(
            user: User = Depends(require_role("EDITOR")),
        ):
            ...
    """
    min_order = _ROLE_ORDER.get(minimum_role.upper(), 0)

    async def _check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        role_str = (
            current_user.role.value
            if hasattr(current_user.role, "value")
            else str(current_user.role)
        )
        role_order = _ROLE_ORDER.get(role_str.upper(), -1)
        if role_order < min_order:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"This action requires the {minimum_role} role or higher. "
                    f"Your role: {current_user.role}"
                ),
            )
        return current_user

    return _check_role
