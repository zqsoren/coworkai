"""
Auth Router - 用户注册/登录（Supabase 版）
"""
import os
import uuid
import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.supabase_client import supabase

router = APIRouter(prefix="/api/auth", tags=["auth"])

JWT_SECRET = os.environ.get("JWT_SECRET", "agentos-secret-key-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 30


# --- Models ---

class RegisterRequest(BaseModel):
    username: str
    phone: str
    password: str

class LoginRequest(BaseModel):
    phone: str
    password: str


# --- Helpers ---

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def _check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

def _create_token(user_id: str, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def _init_user_data(user_id: str):
    """Copy template data to new user's directory (文件系统部分保留)."""
    import shutil, json
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_ROOT = os.path.join(PROJECT_ROOT, "data")
    TEMPLATE_DIR = os.path.join(DATA_ROOT, "_template")

    user_dir = os.path.join(DATA_ROOT, user_id)
    if os.path.exists(user_dir):
        return
    if os.path.exists(TEMPLATE_DIR):
        shutil.copytree(TEMPLATE_DIR, user_dir)
        print(f"[Auth] Copied template to {user_dir}")
    else:
        os.makedirs(user_dir, exist_ok=True)
        print(f"[Auth] Created empty user dir {user_dir}")


# --- Endpoints ---

@router.post("/register")
def register(req: RegisterRequest):
    if not req.username.strip() or not req.phone.strip() or not req.password.strip():
        raise HTTPException(400, "用户名、手机号和密码不能为空")

    # Check phone uniqueness
    existing = supabase.table("users").select("id").eq("phone", req.phone).execute()
    if existing.data:
        raise HTTPException(400, "该手机号已注册")

    user_id = f"user_{uuid.uuid4().hex[:12]}"

    # Insert into Supabase
    supabase.table("users").insert({
        "id": user_id,
        "username": req.username.strip(),
        "phone": req.phone.strip(),
        "password_hash": _hash_password(req.password),
    }).execute()

    # Initialize user data directory from template (文件系统)
    _init_user_data(user_id)

    token = _create_token(user_id, req.username)
    return {
        "token": token,
        "user": {"id": user_id, "username": req.username, "phone": req.phone}
    }


@router.post("/login")
def login(req: LoginRequest):
    result = supabase.table("users").select("*").eq("phone", req.phone).execute()

    if not result.data:
        raise HTTPException(404, "该手机号未注册")

    user = result.data[0]
    if _check_password(req.password, user["password_hash"]):
        token = _create_token(user["id"], user["username"])
        return {
            "token": token,
            "user": {"id": user["id"], "username": user["username"], "phone": user["phone"]}
        }
    else:
        raise HTTPException(401, "密码错误")


@router.get("/me")
def get_me():
    """This endpoint requires the middleware to inject user info.
    We handle it in server.py via dependency."""
    raise HTTPException(401, "Not authenticated")
