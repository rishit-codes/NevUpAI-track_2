import jwt
from datetime import datetime, timezone
from app.core.config import settings

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "iat", "exp", "role"]}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}")

def create_access_token(user_id: str, role: str = "trader", name: str = None) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + 86400,
        "role": role
    }
    if name:
        payload["name"] = name
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
