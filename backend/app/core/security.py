import os
import secrets
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request
from .config import settings

def ensure_token_exists():
    path = settings.local_token_path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        token = secrets.token_hex(32)
        with open(path, "w", encoding="utf-8") as f:
            f.write(token)
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass # Windows or other OS might not support 0o600

class BearerTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path.startswith("/api/health"):
            return await call_next(request)
        if request.url.path.startswith("/api"):
            auth_header = request.headers.get("Authorization")
            
            with open(settings.local_token_path, "r", encoding="utf-8") as f:
                expected_token = f.read().strip()
                
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
                
            token = auth_header.split(" ")[1]
            if token != expected_token:
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
                
        return await call_next(request)
