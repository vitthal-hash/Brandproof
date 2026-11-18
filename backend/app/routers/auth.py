from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..db import User, get_db
from ..security import current_user, make_token, verify_password

router = APIRouter(prefix="/api")


class Login(BaseModel):
    email: str
    password: str


def ser_user(u: User) -> dict:
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role, "team": u.team}


@router.post("/auth/login")
def login(body: Login, db: Session = Depends(get_db)):
    u = db.execute(select(User).where(User.email == body.email.strip().lower())).scalar_one_or_none()
    if not u or not verify_password(body.password, u.pw_hash):
        raise HTTPException(401, "Wrong email or password")
    return {"token": make_token(u), "user": ser_user(u)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return ser_user(user)


@router.get("/demo-users")
def demo_users(db: Session = Depends(get_db)):
    """Lists seeded demo accounts for one-click demo sign-in. Disabled when BP_SEED=0 (production)."""
    if not config.seed_enabled():
        return []
    return [ser_user(u) for u in db.execute(select(User).order_by(User.id)).scalars()]
