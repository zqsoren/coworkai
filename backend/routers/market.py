"""
Market Router — 智能体市场的全局发布/浏览/导入 API（Supabase 版）
"""
import os
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
# 系统文件过滤规则
# ---------------------------------------------------------------------------

# 发布时携带的文件（白名单）
_PUBLISH_ARCHIVES = {"soul.md", "_guide.md", "行为标准.md"}
_PUBLISH_KB_EXCLUDE_PREFIX = "里程碑_"  # knowledge_base 下排除里程碑


def _collect_publish_files(agent_dir: str) -> dict:
    """从磁盘收集要发布的系统文件内容"""
    files = {}

    # 1. archives/ 下的白名单文件
    archives_dir = os.path.join(agent_dir, "archives")
    if os.path.isdir(archives_dir):
        for fname in os.listdir(archives_dir):
            if fname in _PUBLISH_ARCHIVES:
                fpath = os.path.join(archives_dir, fname)
                if os.path.isfile(fpath):
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            content = f.read()
                        if content and len(content.strip()) > 20:
                            files[f"archives/{fname}"] = content
                    except Exception:
                        pass

    # 2. knowledge_base/ 下除里程碑外的所有文件
    kb_dir = os.path.join(agent_dir, "knowledge_base")
    if os.path.isdir(kb_dir):
        for fname in os.listdir(kb_dir):
            if fname.startswith(_PUBLISH_KB_EXCLUDE_PREFIX):
                continue  # 跳过里程碑
            if fname.startswith(".") or fname == "_metadata.json":
                continue
            fpath = os.path.join(kb_dir, fname)
            if os.path.isfile(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                    if content and len(content.strip()) > 10:
                        files[f"knowledge_base/{fname}"] = content
                except Exception:
                    pass

    return files


def _restore_system_files(agent_dir: str, system_files: dict) -> None:
    """将发布时携带的系统文件恢复到磁盘"""
    if not system_files:
        return

    for rel_path, content in system_files.items():
        full_path = os.path.join(agent_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"[Market] Failed to restore {rel_path}: {e}")


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
    # 新增：用于后端读取文件
    agent_id: Optional[str] = ""
    workspace_id: Optional[str] = ""


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

    # 收集要发布的系统文件
    system_files = {}
    if req.agent_id and req.workspace_id:
        fm = get_user_file_manager(request)
        agent_dir = os.path.join(fm.data_root, req.workspace_id, req.agent_id)
        if os.path.isdir(agent_dir):
            system_files = _collect_publish_files(agent_dir)

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
        "system_files": system_files if system_files else None,
    }).execute()

    return {"status": "success", "market_agent_id": market_id, "files_published": len(system_files)}


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

    # 恢复已发布的系统文件（覆盖空模板）
    system_files = agent_data.get("system_files")
    if system_files:
        agent_dir = os.path.join(fm.data_root, req.target_workspace_id, agent_id)
        _restore_system_files(agent_dir, system_files)

    return {"status": "success", "agent_id": agent_id}
