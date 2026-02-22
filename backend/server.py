
import os
import sys
import json
from typing import List, Optional, Dict, Any


from fastapi import FastAPI, HTTPException, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to sys.path to allow imports from src
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import Core Modules
from src.core.file_manager import FileManager
from src.core.workspace import WorkspaceManager
from src.core.agent_registry import AgentRegistry
from src.graph.agent_graph import create_compiled_graph
from src.core.llm_manager import LLMManager
from langchain_core.messages import HumanMessage, AIMessage

# Import Routers
from backend.routers import agent, settings, knowledge, system, workspace, group, files, output_modes, util, auth
from backend.middleware.auth_middleware import JWTAuthMiddleware
from backend.user_deps import get_user_file_manager, get_user_agent_registry, get_user_workspace_manager

# ==============================================================================
# Setup & Initialization
# ==============================================================================

app = FastAPI(
    title="AgentOS Backend",
    description="Headless API for AgentOS",
    version="1.0.0"
)

# Include Routers
with open("backend_debug.log", "a", encoding="utf-8") as f:
    import datetime
    f.write(f"[{datetime.datetime.now()}] [Server] Loading routers...\n")

app.include_router(auth.router)  # Auth (public, no JWT needed)
app.include_router(agent.router)
app.include_router(settings.router)
app.include_router(knowledge.router)
app.include_router(system.router)
app.include_router(workspace.router)
app.include_router(group.router)
app.include_router(files.router)
app.include_router(output_modes.router)
app.include_router(util.router)


# CORS Configuration
origins = [
    "http://localhost:3000",  # React App
    "http://localhost:5173",  # Vite Dev Server
    "http://localhost:8000",
    "*"  # For development convenience
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Auth Middleware (added AFTER CORS so preflight works)
app.add_middleware(JWTAuthMiddleware)

# Initialize Managers (Global singletons kept for backward compat)
DATA_ROOT = os.path.join(PROJECT_ROOT, "data")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
REGISTRY_PATH = os.path.join(CONFIG_DIR, "agents_registry.json")

file_manager = FileManager(DATA_ROOT)
workspace_manager = WorkspaceManager(file_manager)
agent_registry = AgentRegistry(REGISTRY_PATH)
llm_manager = LLMManager()

# ==============================================================================
# Pydantic Models
# ==============================================================================

class ChatRequest(BaseModel):
    message: str
    agent_id: str
    workspace_id: str
    thread_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    messages: List[Dict[str, Any]]
    pending_changes: List[Dict[str, Any]]

class WorkspaceInfo(BaseModel):
    id: str
    name: str
class AgentInfo(BaseModel):
    id: str
    name: str
    role: Optional[str]
    workspace: str
    provider_id: Optional[str] = None
    model_name: Optional[str] = None
    system_prompt: Optional[str] = None
    persona_mode: Optional[str] = None  # 🆕 返回 persona_mode
    tools: Optional[List[str]] = None
    skills: Optional[List[str]] = None

class FileReadRequest(BaseModel):
    file_path: str  # Relative to data root or absolute path routed through FileManager

class FileReadResponse(BaseModel):
    content: str
    file_path: str

# ==============================================================================
# Endpoints
# ==============================================================================

@app.get("/")
def health_check():
    return {"status": "ok", "service": "AgentOS Backend", "version": "2.0.0-auth"}

from fastapi import Request

@app.get("/api/auth/me")
def get_current_user(request: Request):
    """Get current user info from JWT."""
    user_id = getattr(request.state, "user_id", None)
    username = getattr(request.state, "username", None)
    if not user_id:
        raise HTTPException(401, "Not authenticated")
    return {"id": user_id, "username": username}

@app.get("/api/workspaces", response_model=List[WorkspaceInfo])
def list_workspaces(request: Request):
    """List all available workspaces."""
    wm = get_user_workspace_manager(request)
    return [
        WorkspaceInfo(id=ws["id"], name=ws["name"])
        for ws in wm.list_workspaces()
    ]

@app.get("/api/agents", response_model=List[AgentInfo])
def list_agents(request: Request, workspace_id: Optional[str] = None):
    """List agents, optionally filtered by workspace."""
    ar = get_user_agent_registry(request)
    agents = ar.list_agents(workspace=workspace_id)
    return [
        AgentInfo(
            id=a["id"],
            name=a.get("name", a["id"]),
            role=a.get("role", ""),
            workspace=a.get("workspace", ""),
            provider_id=a.get("provider_id"),
            model_name=a.get("model_name"),
            system_prompt=a.get("system_prompt"),
            persona_mode=a.get("persona_mode"),
            tools=a.get("tools", []),
            skills=a.get("skills", [])
        )
        for a in agents
    ]

@app.get("/api/skills", response_model=List[str])
def list_available_skills():
    """List all available skill names from .agent/skills directory."""
    skills_dir = os.path.join(os.getcwd(), ".agent", "skills")
    if not os.path.exists(skills_dir):
        return []
    
    skills = []
    for item in os.listdir(skills_dir):
        if os.path.isdir(os.path.join(skills_dir, item)):
            skills.append(item)
    return sorted(skills)

@app.get("/api/tools", response_model=List[str])
def list_available_tools():
    """List all available core tools."""
    # Since tools are statically defined in python files, we can just return a fixed list
    # or scan the file_tools and web_tools. For now, returning known base tools:
    return [
        "read_file", 
        "write_file", 
        "list_dir", 
        "google_search",
        "fetch_url_content",
        "create_new_agent",
        "list_available_agents",
        "read_any_file",
        "search_files_by_keyword",
        "suggest_delegation_to_agent"
    ]

@app.post("/api/file/read", response_model=FileReadResponse)
def read_file(req: FileReadRequest, request: Request):
    """Read file content securely."""
    try:
        fm = get_user_file_manager(request)
        content = fm.read_file(req.file_path)
        return FileReadResponse(content=content, file_path=req.file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/invoke", response_model=ChatResponse)
def invoke_chat(chat_req: ChatRequest, request: Request):
    """
    Invoke the Agent LangGraph.
    This is a stateless invocation per turn (REST style).
    """
    # 1. Get Agent Config
    ar = get_user_agent_registry(request)
    agent_config = ar.get_agent(chat_req.agent_id)
    if not agent_config:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # 2. Prepare Context
    context = ""
    try:
        fm = get_user_file_manager(request)
        cfiles = fm.get_agent_context(chat_req.workspace_id, chat_req.agent_id)
        if cfiles:
             parts = ["## Context"]
             for k, v in cfiles.items(): 
                 parts.append(f"### {k}\n```\n{v[:1000]}\n```")
             context = "\n".join(parts)
    except Exception:
        pass

    # 3. Construct Graph State
    initial_state = {
        "messages": [HumanMessage(content=chat_req.message)],
        "current_agent": chat_req.agent_id,
        "current_workspace": chat_req.workspace_id,
        "agent_config": agent_config,
        "pending_changes": [],
        "context": context,
        "needs_approval": False,
    }

    # 4. Run Graph
    try:
        graph = create_compiled_graph()
        result = graph.invoke(initial_state)
    except Exception as e:
        import traceback
        with open("backend_debug.log", "a", encoding="utf-8") as f:
            f.write(f"Graph Execution Error: {str(e)}\n")
            f.write(traceback.format_exc())
            f.write("\n" + "="*50 + "\n")
        print(f"Graph Execution Error: {str(e)}") # Print to console just in case
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")

    # 5. Process Result
    messages = result.get("messages", [])
    pending_changes = result.get("pending_changes", [])
    
    # Extract final text response
    response_text = ""
    serialized_messages = []
    
    for msg in messages:
        role = "unknown"
        content = ""
        if isinstance(msg, HumanMessage):
            role = "user"
            content = msg.content
        elif isinstance(msg, AIMessage):
            role = "assistant"
            content = msg.content
        
        serialized_messages.append({"role": role, "content": content})
        
        if role == "assistant":
            response_text = content # Keep last assistant message

    return ChatResponse(
        response=response_text,
        messages=serialized_messages,
        pending_changes=pending_changes
    )

# ... (summarize endpoint removed, moved to util router)

if __name__ == "__main__":
    import uvicorn
    print("Starting AgentOS Backend on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
