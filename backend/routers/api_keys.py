"""
API Keys Router — 用户 API Key 的生成/查询/删除
用于 MCP 外部接入认证。
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.supabase_client import supabase
from backend.user_deps import get_user_id

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])


class GenerateKeyRequest(BaseModel):
    name: Optional[str] = "Default"


@router.post("/generate")
def generate_api_key(req: GenerateKeyRequest, request: Request):
    """为当前用户生成一个新的 API Key。"""
    user_id = get_user_id(request)

    key_id = str(uuid.uuid4())
    api_key = f"ak_{uuid.uuid4().hex}"

    supabase.table("api_keys").insert({
        "id": key_id,
        "user_id": user_id,
        "key": api_key,
        "name": req.name or "Default",
        "created_at": datetime.now().isoformat(),
    }).execute()

    return {"id": key_id, "key": api_key, "name": req.name}


@router.get("")
def list_api_keys(request: Request):
    """列出当前用户的所有 API Key。"""
    user_id = get_user_id(request)

    result = supabase.table("api_keys") \
        .select("id, key, name, created_at, last_used_at") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .execute()

    return result.data or []


@router.delete("/{key_id}")
def delete_api_key(key_id: str, request: Request):
    """删除指定的 API Key。"""
    user_id = get_user_id(request)

    # Verify ownership
    existing = supabase.table("api_keys") \
        .select("id") \
        .eq("id", key_id) \
        .eq("user_id", user_id) \
        .execute()

    if not existing.data:
        raise HTTPException(status_code=404, detail="API Key not found")

    supabase.table("api_keys") \
        .delete() \
        .eq("id", key_id) \
        .eq("user_id", user_id) \
        .execute()

    return {"status": "deleted"}
