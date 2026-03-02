"""
Market Router — 智能体市场的全局发布/浏览/导入 API
数据存储在全局 data/market_agents.json，所有用户共享可见。
"""
import os
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.core.meta_agent import MetaAgent
from backend.user_deps import (
    get_user_file_manager,
    get_user_agent_registry,
    get_user_id,
    get_user_data_root,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKET_FILE = os.path.join(PROJECT_ROOT, "data", "market_agents.json")

router = APIRouter(prefix="/api/market", tags=["market"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_market() -> list[dict]:
    if not os.path.exists(MARKET_FILE):
        return []
    with open(MARKET_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_market(data: list[dict]):
    os.makedirs(os.path.dirname(MARKET_FILE), exist_ok=True)
    with open(MARKET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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
    market = _load_market()

    entry = {
        "id": f"market_{uuid.uuid4().hex[:8]}",
        "name": req.name,
        "description": req.description or "",
        "system_prompt": req.system_prompt,
        "tools": req.tools or [],
        "skills": req.skills or [],
        "mcp_servers": req.mcp_servers or [],
        "knowledge_base": req.knowledge_base or [],
        "publisher_id": user_id,
        "published_at": datetime.now().isoformat(),
        "downloads": 0,
        "rating": 5.0,
    }

    market.append(entry)
    _save_market(market)
    return {"status": "success", "market_agent_id": entry["id"]}


@router.get("/agents")
def list_market_agents():
    """获取所有已发布的市场 Agent（公开）。"""
    return _load_market()


@router.post("/import")
def import_market_agent(req: ImportRequest, request: Request):
    """将市场中的 Agent 导入到用户指定的工作区。"""
    market = _load_market()
    agent_data = next((a for a in market if a["id"] == req.market_agent_id), None)
    if not agent_data:
        raise HTTPException(status_code=404, detail="Market agent not found")

    # Increment download count
    agent_data["downloads"] = agent_data.get("downloads", 0) + 1
    _save_market(market)

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
        tools=agent_data.get("tools", []),
        skills=agent_data.get("skills", []),
        mcp_servers=agent_data.get("mcp_servers", []),
    )

    return {"status": "success", "agent_id": agent_id}
