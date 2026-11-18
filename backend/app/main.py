from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config, db, seed
from .routers import assets, auth, governance, redteam, system


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_engine()
    if config.seed_enabled():
        seed.seed_if_empty()
    yield


app = FastAPI(title="BrandProof API", version="2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.cors_origins(), allow_methods=["*"], allow_headers=["*"],
                   allow_credentials=False)
for r in (auth.router, assets.router, governance.router, redteam.router, system.router):
    app.include_router(r)
