from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analysis import router as analysis_router
from app.api.channels import router as channels_router
from app.api.hashtags import router as hashtags_router
from app.api.health import router as health_router
from app.api.prompts import router as prompts_router
from app.config import API_PREFIX
from app.config import APP_NAME
from app.config import CORS_ORIGINS
from app.config import POSTGRES_URL
from app.deepseek import DeepSeek
from app.storage import Storage
from app.storage import apply_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage = await Storage.create(POSTGRES_URL)
    await apply_migrations(storage.db)
    deepseek = DeepSeek()
    app.state.storage = storage
    app.state.deepseek = deepseek
    yield
    await deepseek.close()
    await storage.close()


app = FastAPI(title=APP_NAME, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(health_router, prefix=API_PREFIX)
app.include_router(channels_router, prefix=API_PREFIX)
app.include_router(hashtags_router, prefix=API_PREFIX)
app.include_router(prompts_router, prefix=API_PREFIX)
app.include_router(analysis_router, prefix=API_PREFIX)
