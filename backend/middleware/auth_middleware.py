"""
JWT Authentication Middleware
Extracts user_id from Authorization header and injects into request.state.
"""
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import os

JWT_SECRET = os.environ.get("JWT_SECRET", "agentos-secret-key-change-me")
JWT_ALGORITHM = "HS256"

# Paths that don't require authentication
PUBLIC_PATHS = [
    "/",
    "/docs",
    "/openapi.json",
    "/api/auth/register",
    "/api/auth/login",
]


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Skip auth for public paths
        if any(path == p or path.startswith(p + "/") for p in PUBLIC_PATHS):
            return await call_next(request)
        
        # Also skip OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Extract token
        auth_header = request.headers.get("Authorization", "")
        
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                request.state.user_id = payload["user_id"]
                request.state.username = payload.get("username", "")
            except jwt.ExpiredSignatureError:
                return JSONResponse(status_code=401, content={"detail": "登录已过期，请重新登录"})
            except jwt.InvalidTokenError:
                return JSONResponse(status_code=401, content={"detail": "无效的登录凭证"})
        elif request.method == "GET":
            # Allow unauthenticated GET — read-only demo mode using _template data
            request.state.user_id = "_template"
            request.state.username = "guest"
        else:
            # POST/PUT/DELETE require auth
            return JSONResponse(
                status_code=401,
                content={"detail": "请先登录后再操作"}
            )
        
        return await call_next(request)
