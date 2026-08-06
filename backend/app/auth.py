from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"
ADMIN_SUBJECT = "admin"

security = HTTPBearer()


def create_admin_token(expires_delta: timedelta = timedelta(days=365)) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"sub": ADMIN_SUBJECT, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> None:
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc

    if payload.get("sub") != ADMIN_SUBJECT:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
