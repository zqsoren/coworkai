"""
Market Router — 智能体市场的全局发布/浏览/导入 API（Supabase 版）
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.core.meta_agent import MetaAgent
from backend.supabase_client import supabase
from backend.user_deps import (
    get_user_file_manager,
    get_user_agent_registry,
    get_user_id,
)

router = APIRouter(prefix="/api/market", tags=["market"])


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class PublishRequest(BaseModel):
    name: str
    system_prompt: str
    description: Optional[str] = ""
    tools: Optional[List[str]] = []
    skills: Optional[List[str]] = []
    mcp_servers: Optional[List[Dict[str, Any]]] = []
    knowledge_base: Optional[List[str]] = []
    provider_id: Optional[str] = ""
    model_name: Optional[str] = ""


class ImportRequest(BaseModel):
    market_agent_id: str
    target_workspace_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/publish")
def publish_agent(req: PublishRequest, request: Request):
    """发布一个 Agent 到全局市场。"""
    user_id = get_user_id(request)

    market_id = f"market_{uuid.uuid4().hex[:8]}"

    supabase.table("market_agents").insert({
        "id": market_id,
        "name": req.name,
        "description": req.description or "",
        "system_prompt": req.system_prompt,
        "tools": req.tools or [],
        "skills": req.skills or [],
        "mcp_servers": req.mcp_servers or [],
        "knowledge_base": req.knowledge_base or [],
        "publisher_id": user_id,
        "downloads": 0,
        "rating": 5.0,
        "provider_id": req.provider_id or "",
        "model_name": req.model_name or "",
    }).execute()

    return {"status": "success", "market_agent_id": market_id}


@router.get("/agents")
def list_market_agents():
    """获取所有已发布的市场 Agent（公开）。"""
    result = supabase.table("market_agents").select("*").execute()
    return result.data


@router.post("/import")
def import_market_agent(req: ImportRequest, request: Request):
    """将市场中的 Agent 导入到用户指定的工作区。"""
    result = supabase.table("market_agents") \
        .select("*") \
        .eq("id", req.market_agent_id) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Market agent not found")

    agent_data = result.data[0]

    # Increment download count
    supabase.table("market_agents") \
        .update({"downloads": (agent_data.get("downloads") or 0) + 1}) \
        .eq("id", req.market_agent_id) \
        .execute()

    # Create agent in target workspace using MetaAgent
    fm = get_user_file_manager(request)
    ar = get_user_agent_registry(request)
    meta_agent = MetaAgent(fm, ar)

    agent_id = f"agent_{agent_data['name'].lower().replace(' ', '_').replace('-', '_')}_{uuid.uuid4().hex[:4]}"

    meta_agent.create_agent(
        workspace_id=req.target_workspace_id,
        agent_id=agent_id,
        name=agent_data["name"],
        role_desc=agent_data.get("description", ""),
        system_prompt=agent_data["system_prompt"],
        tools=agent_data.get("tools") or [],
        skills=agent_data.get("skills") or [],
        mcp_servers=agent_data.get("mcp_servers") or [],
    )

    return {"status": "success", "agent_id": agent_id}
