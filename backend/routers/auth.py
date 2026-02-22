"""
Auth Router - 用户注册/登录
"""
import os
import json
import uuid
import shutil
import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_ROOT = os.path.join(PROJECT_ROOT, "data")
USERS_FILE = os.path.join(DATA_ROOT, "users.json")
TEMPLATE_DIR = os.path.join(DATA_ROOT, "_template")

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

def _load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_users(users: dict):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

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
    """Copy template data to new user's directory."""
    user_dir = os.path.join(DATA_ROOT, user_id)
    if os.path.exists(user_dir):
        return
    if os.path.exists(TEMPLATE_DIR):
        shutil.copytree(TEMPLATE_DIR, user_dir)
        print(f"[Auth] Copied template to {user_dir}")
    else:
        os.makedirs(user_dir, exist_ok=True)
        # Create minimal defaults
        with open(os.path.join(user_dir, "agents_registry.json"), "w", encoding="utf-8") as f:
            json.dump({"version": "1.0", "agents": {}}, f, ensure_ascii=False, indent=2)
        with open(os.path.join(user_dir, "llm_providers.json"), "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        print(f"[Auth] Created empty user dir {user_dir}")


# --- Endpoints ---

@router.post("/register")
def register(req: RegisterRequest):
    if not req.username.strip() or not req.phone.strip() or not req.password.strip():
        raise HTTPException(400, "用户名、手机号和密码不能为空")
    
    users = _load_users()
    
    # Check phone uniqueness
    for uid, u in users.items():
        if u["phone"] == req.phone:
            raise HTTPException(400, "该手机号已注册")
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    users[user_id] = {
        "username": req.username.strip(),
        "phone": req.phone.strip(),
        "password_hash": _hash_password(req.password),
        "created_at": datetime.now().isoformat()
    }
    _save_users(users)
    
    # Initialize user data directory from template
    _init_user_data(user_id)
    
    token = _create_token(user_id, req.username)
    return {
        "token": token,
        "user": {"id": user_id, "username": req.username, "phone": req.phone}
    }


@router.post("/login")
def login(req: LoginRequest):
    users = _load_users()
    
    for uid, u in users.items():
        if u["phone"] == req.phone:
            if _check_password(req.password, u["password_hash"]):
                token = _create_token(uid, u["username"])
                return {
                    "token": token,
                    "user": {"id": uid, "username": u["username"], "phone": u["phone"]}
                }
            else:
                raise HTTPException(401, "密码错误")
    
    raise HTTPException(404, "该手机号未注册")


@router.get("/me")
def get_me():
    """This endpoint requires the middleware to inject user info.
    We handle it in server.py via dependency."""
    # This is a placeholder — actual implementation uses the middleware's user_id
    raise HTTPException(401, "Not authenticated")
