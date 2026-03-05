"""
Chat Sessions Router — 聊天记录持久化 CRUD
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Request
from pydantic import BaseModel
from backend.supabase_client import supabase
from backend.user_deps import get_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None
    is_plan: Optional[bool] = None


class SaveSessionRequest(BaseModel):
    session_id: str
    context_id: str  # agent_id or group_id
    title: str = "新对话"
    preview: str = ""
    messages: List[SessionMessage] = []


# ── 保存/更新会话 ──
@router.post("/save")
async def save_session(req: SaveSessionRequest, request: Request):
    user_id = get_user_id(request)
    messages_data = [m.dict() for m in req.messages]

    # Upsert: try update first, insert if not found
    existing = supabase.table("chat_sessions").select("id").eq("id", req.session_id).execute()

    row = {
        "id": req.session_id,
        "user_id": user_id,
        "context_id": req.context_id,
        "title": req.title,
        "preview": req.preview,
        "message_count": len(req.messages),
        "messages": messages_data,
        "updated_at": "now()",
    }

    if existing.data:
        supabase.table("chat_sessions").update({
            "title": req.title,
            "preview": req.preview,
            "message_count": len(req.messages),
            "messages": messages_data,
            "updated_at": "now()",
        }).eq("id", req.session_id).execute()
    else:
        supabase.table("chat_sessions").insert(row).execute()

    return {"status": "ok"}


# ── 获取会话列表（不含消息体） ──
@router.get("/list")
async def list_sessions(context_id: str, request: Request):
    user_id = get_user_id(request)
    result = supabase.table("chat_sessions") \
        .select("id, context_id, title, preview, message_count, created_at, updated_at") \
        .eq("user_id", user_id) \
        .eq("context_id", context_id) \
        .order("updated_at", desc=True) \
        .limit(50) \
        .execute()
    return {"sessions": result.data or []}


# ── 获取单个会话（含消息体） ──
@router.get("/{session_id}")
async def get_session(session_id: str, request: Request):
    user_id = get_user_id(request)
    result = supabase.table("chat_sessions") \
        .select("*") \
        .eq("id", session_id) \
        .eq("user_id", user_id) \
        .execute()
    if not result.data:
        return {"session": None}
    return {"session": result.data[0]}


# ── 删除会话 ──
@router.delete("/{session_id}")
async def delete_session(session_id: str, request: Request):
    user_id = get_user_id(request)
    supabase.table("chat_sessions") \
        .delete() \
        .eq("id", session_id) \
        .eq("user_id", user_id) \
        .execute()
    return {"status": "ok"}
