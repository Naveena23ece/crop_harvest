"""
Authentication, Password Hashing, and Role-Based Access Control (RBAC) for GrainGuard AI.
Uses NIST-standard PBKDF2-HMAC-SHA256 password hashing and PyJWT tokens.
"""

import os
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, Set
import jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.database.db import get_db, DATA_DIR
from backend.database.models import User

# ── JWT Configuration ─────────────────────────────────────────────
SECRET_FILE = os.path.join(DATA_DIR, ".jwt_secret")
if not os.path.exists(SECRET_FILE):
    with open(SECRET_FILE, "w") as f:
        f.write(secrets.token_hex(32))

with open(SECRET_FILE, "r") as f:
    _DEFAULT_SECRET = f.read().strip()

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", _DEFAULT_SECRET)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 12))  # 12 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# In-memory blacklist for revoked tokens (persists per server run, backed by DB if needed)
_TOKEN_BLACKLIST: Set[str] = set()


# ── Password Hashing ──────────────────────────────────────────────
def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations and random salt."""
    salt = secrets.token_hex(16)
    iterations = 100_000
    hash_bytes = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2:sha256:{iterations}${salt}${hash_bytes.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored PBKDF2 hash using constant-time comparison."""
    if not hashed_password or not plain_password:
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) == 3 and parts[0].startswith("pbkdf2:sha256:"):
            iterations = int(parts[0].split(":")[-1])
            salt = parts[1]
            stored_hash = parts[2]
            computed_bytes = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations)
            return hmac.compare_digest(computed_bytes.hex(), stored_hash)
        # Fallback for plain SHA256 if migrating legacy formats
        if len(parts) == 1 and len(hashed_password) == 64:
            computed = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
            return hmac.compare_digest(computed, hashed_password)
        return False
    except Exception:
        return False


# ── Token Management ──────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token containing user claims."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decodes and validates a JWT token. Returns claims dict or None if invalid/expired."""
    if token in _TOKEN_BLACKLIST:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except (jwt.PyJWTError, Exception):
        return None


def revoke_token(token: str) -> None:
    """Blacklists a token so it cannot be reused."""
    if token:
        _TOKEN_BLACKLIST.add(token)


# ── FastAPI Dependencies (RBAC) ───────────────────────────────────
def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Validates token from Authorization header or 'access_token' cookie.
    Retrieves active user from database.
    """
    auth_token = token
    if not auth_token:
        # Check cookie fallback for secure browser session
        auth_token = request.cookies.get("access_token")

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(auth_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject identifier.",
        )

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this token no longer exists.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account has been deactivated.",
        )

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Enforces that the authenticated user possesses the Admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Administrative privileges required.",
        )
    return user


def require_viewer_or_admin(user: User = Depends(get_current_user)) -> User:
    """Enforces that the user is authenticated as either Viewer or Admin."""
    if user.role not in ("admin", "viewer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Valid role required.",
        )
    return user


def get_optional_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Returns the authenticated user if token is provided and valid, otherwise None."""
    auth_token = token or request.cookies.get("access_token")
    if not auth_token:
        return None
    payload = decode_access_token(auth_token)
    if not payload or not payload.get("sub"):
        return None
    return db.query(User).filter(User.username == payload["sub"], User.is_active == True).first()
