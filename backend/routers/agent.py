from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List

from src.core.agent_registry import AgentRegistry
from src.core.meta_agent import MetaAgent
from src.core.file_manager import FileManager
from src.core.workspace import WorkspaceManager
from backend.user_deps import get_user_file_manager, get_user_agent_registry

import os

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Models
class CreateAgentRequest(BaseModel):
    workspace_id: str
    name: str
    system_prompt: str
    provider_id: str
    model_name: str

class UpdateAgentRequest(BaseModel):
    workspace_id: str
    agent_id: str
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    provider_id: Optional[str] = None
    model_name: Optional[str] = None
    persona_mode: Optional[str] = None
    tools: Optional[List[str]] = None
    skills: Optional[List[str]] = None


@router.post("/create")
def create_agent(req: CreateAgentRequest, request: Request):
    """Create a new agent."""
    try:
        fm = get_user_file_manager(request)
        ar = get_user_agent_registry(request)
        meta_agent = MetaAgent(fm, ar)
        
        agent_id = f"agent_{req.name.lower().replace(' ', '_').replace('-', '_')}"
        meta_agent.create_agent(
            workspace_id=req.workspace_id,
            agent_id=agent_id,
            name=req.name,
            role_desc=req.system_prompt,
            system_prompt=req.system_prompt,
            provider_id=req.provider_id,
            model_name=req.model_name
        )
        return {"status": "success", "agent_id": agent_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update")
def update_agent(req: UpdateAgentRequest, request: Request):
    """Update agent settings."""
    try:
        ar = get_user_agent_registry(request)
        updates = {}
        if req.name is not None: updates["name"] = req.name
        if req.system_prompt is not None: updates["system_prompt"] = req.system_prompt
        if req.provider_id is not None: updates["provider_id"] = req.provider_id
        if req.model_name is not None: updates["model_name"] = req.model_name
        if req.persona_mode is not None: updates["persona_mode"] = req.persona_mode
        if req.tools is not None: updates["tools"] = req.tools
        if req.skills is not None: updates["skills"] = req.skills
        
        ar.update_agent(req.agent_id, updates)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{agent_id}")
def delete_agent(agent_id: str, request: Request):
    """Delete an agent."""
    try:
        ar = get_user_agent_registry(request)
        ar.remove_agent(agent_id)
        return {"status": "success"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Agent not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
