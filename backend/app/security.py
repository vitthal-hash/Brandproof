"""Password hashing, JWT tokens and role checks."""
import datetime as dt
import hashlib
import hmac
import os

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from . import config
from .db import User, get_db

ROLES = ("creator", "external", "manager", "reviewer", "owner")


def hash_password(pw: str, salt: str | None = None) -> str:
    salt = salt or os.urandom(8).hex()
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${h}"


def verify_password(pw: str, stored: str) -> bool:
    salt, _ = stored.split("$", 1)
    return hmac.compare_digest(hash_password(pw, salt), stored)


def make_token(user: User) -> str:
    payload = {"sub": str(user.id), "role": user.role,
               "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=12)}
    return jwt.encode(payload, config.secret(), algorithm="HS256")


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing token")
    try:
        data = jwt.decode(authorization[7:], config.secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, int(data["sub"]))
    if not user:
        raise HTTPException(401, "Unknown user")
    return user


def require(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, f"Role '{user.role}' is not allowed to do this")
        return user
    return dep
