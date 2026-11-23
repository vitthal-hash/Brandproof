from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import asyncio

from . import config, db, limits, schedule, seed
from .routers import assets, auth, governance, redteam, stale as stale_router, system, verify


def _ensure_admin_user() -> None:
    """Optional own account: set BP_ADMIN_EMAIL and BP_ADMIN_PASSWORD (and optionally BP_ADMIN_NAME, BP_ADMIN_ROLE).
    Created on start; changing the password variable and redeploying updates the password."""
    import logging
    import os
    from sqlalchemy import select
    from .db import User
    from .security import ROLES, hash_password
    email = (os.getenv("BP_ADMIN_EMAIL") or "").strip().lower()
    password = os.getenv("BP_ADMIN_PASSWORD") or ""
    if not email or not password:
        return
    role = (os.getenv("BP_ADMIN_ROLE") or "owner").strip().lower()
    if role not in ROLES:
        logging.getLogger("brandproof").warning("BP_ADMIN_ROLE %r is not valid; using owner", role)
        role = "owner"
    s = db.session()
    try:
        u = s.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if u is None:
            s.add(User(email=email, name=os.getenv("BP_ADMIN_NAME") or "Admin", role=role, team="Brand",
                       pw_hash=hash_password(password)))
        else:
            u.pw_hash = hash_password(password)
            u.role = role
        s.commit()
    except Exception:
        s.rollback()
        logging.getLogger("brandproof").exception("could not create the admin user")
    finally:
        s.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    limits.check_secrets()
    db.init_engine()
    if config.seed_enabled():
        seed.seed_if_empty()
    seed.ensure_core_rules()
    _ensure_admin_user()
    try:  # facts may have expired since the last start
        from . import stale
        s = db.session()
        try:
            stale.scan(s, "system", "startup (date check)")
        finally:
            s.close()
    except Exception:
        import logging; logging.getLogger("brandproof").exception("startup stale scan skipped")
    task = asyncio.create_task(schedule.loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="BrandProof API", version="2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.cors_origins(), allow_methods=["*"], allow_headers=["*"],
                   allow_credentials=False)
limits.install(app)
for r in (auth.router, assets.router, governance.router, redteam.router, system.router, verify.router, stale_router.router):
    app.include_router(r)

# Health check endpoint for Render and UptimeRobot
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "BrandProof API"
    }