from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.security import BearerTokenMiddleware, ensure_token_exists
from app.api.router import api_router

def create_app():
    ensure_token_exists()
    
    app = FastAPI(title="ReconForge")
    
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
