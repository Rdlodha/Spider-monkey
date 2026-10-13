from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import BearerTokenMiddleware, ensure_token_exists
from app.api.router import api_router
from app.services.checklist_service import seed_templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_token_exists()
    try:
        engine = create_engine(settings.database_url)
        with Session(engine) as db:
            seed_templates(db)
    except Exception:
        pass
    yield


def create_app():
    app = FastAPI(title="ReconForge", lifespan=lifespan)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(BearerTokenMiddleware)
    
    app.include_router(api_router, prefix="/api")
    
    return app


app = create_app()
