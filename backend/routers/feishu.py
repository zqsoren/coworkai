"""
Feishu (飞书) Bot Router — 接收飞书消息并转发给 AgentOS Agent
"""
import os
import uuid
import logging
import hashlib
import time
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.supabase_client import supabase

logger = logging.getLogger("feishu")
logger.setLevel(logging.INFO)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = os.path.join(PROJECT_ROOT, "data")

router = APIRouter(prefix="/api/feishu", tags=["feishu"])

# 消息去重缓存 (message_id -> timestamp)
_processed_messages: dict[str, float] = {}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class FeishuBindRequest(BaseModel):
    app_id: str
    app_secret: str
    agent_id: str
    workspace_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_tenant_access_token(app_id: str, app_secret: str) -> str:
    """获取飞书 tenant_access_token（用于发送消息）"""
    resp = httpx.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"Failed to get token: {data}")
    return data["tenant_access_token"]


def _reply_feishu_message(token: str, message_id: str, text: str):
    """通过飞书 API 回复一条消息"""
    import json
    resp = httpx.post(
        f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        },
        timeout=60,
    )
    data = resp.json()
    if data.get("code") != 0:
        logger.warning(f"[Feishu] Reply failed: {data}")


def _invoke_agent(user_id: str, agent_id: str, workspace_id: str, message: str) -> str:
    """调用 Agent Graph 获取回复（参考 scheduler._execute_task）"""
    from src.graph.agent_graph import create_compiled_graph
    from src.core.agent_registry import AgentRegistry
    from src.core.file_manager import FileManager
    from langchain_core.messages import HumanMessage

    user_root = os.path.join(DATA_ROOT, user_id)
    ar = AgentRegistry(user_id)
    fm = FileManager(user_root)

    agent_config = ar.get_agent(agent_id)
    if not agent_config:
        return "⚠️ Agent 未找到，请检查配置。"

    agent_config["_user_id"] = user_id
    agent_config["_workspace_id"] = workspace_id

    # Build context
    context = ""
    try:
        cfiles = fm.get_agent_context(workspace_id, agent_id)
        if cfiles:
            parts = ["## Context"]
            for k, v in cfiles.items():
                parts.append(f"### {k}\n```\n{v[:1000]}\n```")
            context = "\n".join(parts)
    except Exception:
        pass

    initial_state = {
        "messages": [HumanMessage(content=message)],
        "current_agent": agent_id,
        "current_workspace": workspace_id,
        "agent_config": agent_config,
        "pending_changes": [],
        "context": context,
        "needs_approval": False,
        "user_id": user_id,
    }

    graph = create_compiled_graph()
    final_response = ""

    for step in graph.stream(initial_state):
        for node_name, node_output in step.items():
            if node_name == "agent":
                msgs = node_output.get("messages", [])
                for msg in msgs:
                    if hasattr(msg, "content") and msg.content and not (hasattr(msg, "tool_calls") and msg.tool_calls):
                        content = msg.content
                        if isinstance(content, list):
                            content = "\n".join(
                                item.get("text", str(item)) if isinstance(item, dict) else str(item)
                                for item in content
                            )
                        final_response = str(content)

    return final_response or "⚠️ Agent 没有返回内容。"


def _find_binding(app_id: str) -> Optional[dict]:
    """根据 app_id 查找飞书绑定记录"""
    result = supabase.table("feishu_bindings") \
        .select("*") \
        .eq("app_id", app_id) \
        .eq("enabled", True) \
        .execute()
    return result.data[0] if result.data else None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def feishu_webhook(request: Request):
    """
    飞书事件订阅回调端点。
    处理：1) URL 验证 challenge  2) im.message.receive_v1 消息事件
    """
    body = await request.json()

    # 1. URL 验证（飞书首次配置时发送 challenge）
    if "challenge" in body:
        return {"challenge": body["challenge"]}

    # 2. 事件处理
    header = body.get("header", {})
    event = body.get("event", {})
    event_type = header.get("event_type", "")
    app_id = header.get("app_id", "")

    if event_type != "im.message.receive_v1":
        return {"code": 0, "msg": "ignored"}

    # 提取消息内容
    message = event.get("message", {})
    message_id = message.get("message_id", "")
    msg_type = message.get("message_type", "")
    chat_type = message.get("chat_type", "")

    # 消息去重
    now = time.time()
    if message_id in _processed_messages:
        return {"code": 0, "msg": "duplicate"}
    _processed_messages[message_id] = now
    # 清理 5 分钟前的缓存
    expired = [k for k, v in _processed_messages.items() if now - v > 300]
    for k in expired:
        del _processed_messages[k]

    # 只处理文本消息
    if msg_type != "text":
        return {"code": 0, "msg": "only text supported"}

    # 解析文本
    import json
    try:
        content_obj = json.loads(message.get("content", "{}"))
        user_text = content_obj.get("text", "").strip()
    except Exception:
        user_text = ""

    if not user_text:
        return {"code": 0, "msg": "empty"}

    # 去掉 @Bot 的 mention 前缀
    # 飞书群聊中 @Bot 的格式是 @_user_1 后面跟文本
    import re
    user_text = re.sub(r"@_user_\d+\s*", "", user_text).strip()
    if not user_text:
        return {"code": 0, "msg": "empty after mention strip"}

    # 查找绑定
    binding = _find_binding(app_id)
    if not binding:
        logger.warning(f"[Feishu] No binding for app_id={app_id}")
        return {"code": 0, "msg": "no binding"}

    # 异步处理（先返回 200，后台处理回复）
    import asyncio
    asyncio.get_event_loop().run_in_executor(
        None,
        _handle_message,
        binding,
        message_id,
        user_text,
    )

    return {"code": 0, "msg": "ok"}


def _handle_message(binding: dict, message_id: str, user_text: str):
    """在后台线程中处理消息并回复"""
    try:
        # 调用 Agent
        response = _invoke_agent(
            user_id=binding["user_id"],
            agent_id=binding["agent_id"],
            workspace_id=binding["workspace_id"],
            message=user_text,
        )

        # 获取 token 并回复
        token = _get_tenant_access_token(binding["app_id"], binding["app_secret"])
        _reply_feishu_message(token, message_id, response)

    except Exception as e:
        logger.error(f"[Feishu] Handle message failed: {e}", exc_info=True)
        try:
            token = _get_tenant_access_token(binding["app_id"], binding["app_secret"])
            _reply_feishu_message(token, message_id, f"⚠️ 处理失败：{str(e)[:200]}")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Registration API（前端安装飞书时调用）
# ---------------------------------------------------------------------------

@router.post("/register")
def register_feishu(req: FeishuBindRequest, request: Request):
    """注册飞书 Bot 绑定"""
    from backend.user_deps import get_user_id
    user_id = get_user_id(request)

    # 检查是否已绑定
    existing = supabase.table("feishu_bindings") \
        .select("id") \
        .eq("app_id", req.app_id) \
        .eq("user_id", user_id) \
        .execute()

    if existing.data:
        # 更新
        supabase.table("feishu_bindings") \
            .update({
                "app_secret": req.app_secret,
                "agent_id": req.agent_id,
                "workspace_id": req.workspace_id,
                "enabled": True,
            }) \
            .eq("id", existing.data[0]["id"]) \
            .execute()
        return {"status": "updated", "id": existing.data[0]["id"]}

    # 新建
    bind_id = f"feishu_{uuid.uuid4().hex[:8]}"
    supabase.table("feishu_bindings").insert({
        "id": bind_id,
        "app_id": req.app_id,
        "app_secret": req.app_secret,
        "user_id": user_id,
        "agent_id": req.agent_id,
        "workspace_id": req.workspace_id,
        "enabled": True,
    }).execute()

    return {"status": "created", "id": bind_id}


@router.delete("/unregister")
def unregister_feishu(app_id: str, request: Request):
    """解除飞书 Bot 绑定"""
    from backend.user_deps import get_user_id
    user_id = get_user_id(request)

    supabase.table("feishu_bindings") \
        .update({"enabled": False}) \
        .eq("app_id", app_id) \
        .eq("user_id", user_id) \
        .execute()

    return {"status": "disabled"}
