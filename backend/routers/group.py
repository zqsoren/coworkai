from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json

from src.core.group_manager import GroupChatManager
from src.core.file_manager import FileManager
from src.core.agent_registry import AgentRegistry
from src.core.model_agent import ModelAgent
from src.core.group_chat import GroupChat
from backend.user_deps import get_user_file_manager, get_user_agent_registry, get_user_group_manager

import os
from datetime import datetime

router = APIRouter(prefix="/api/group", tags=["group"])

with open("backend_debug.log", "a", encoding="utf-8") as f:
     f.write(f"[{datetime.now()}] [GroupRouter] Module loaded.\n")

# Models
class CreateGroupRequest(BaseModel):
    workspace_id: str
    name: str
    member_agent_ids: List[str]
    supervisor_id: str

class UpdateGroupRequest(BaseModel):
    workspace_id: str
    group_id: str
    supervisor_id: Optional[str] = None
    supervisor_prompt: Optional[str] = None
    workflow_supervisor_prompt: Optional[str] = None
    name: Optional[str] = None
    members: Optional[List[str]] = None

class GroupChatRequest(BaseModel):
    workspace_id: str
    group_id: str
    message: str
    history: List[Dict[str, Any]] = []

class GenerateWorkflowRequest(BaseModel):
    workspace_id: str
    group_id: str
    user_request: str

class ExecuteWorkflowRequest(BaseModel):
    workspace_id: str
    group_id: str
    workflow: Dict[str, Any]
    history: List[Dict[str, Any]] = []

@router.get("/list")
def list_groups(workspace_id: str, request: Request):
    gm = get_user_group_manager(request); return gm.list_groups(workspace_id)

@router.post("/create")
def create_group(req: CreateGroupRequest, request: Request):
    try:
        group = get_user_group_manager(request).create_group(
            req.workspace_id,
            req.name,
            req.member_agent_ids,
            req.supervisor_id
        )
        return group
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update")
def update_group(req: UpdateGroupRequest, request: Request):
    """Update group settings (supervisor, prompt, name)."""
    try:
        updates = {}
        if req.supervisor_id is not None:
            updates["supervisor_id"] = req.supervisor_id
        if req.supervisor_prompt is not None:
            updates["supervisor_prompt"] = req.supervisor_prompt
        if req.workflow_supervisor_prompt is not None:
            updates["workflow_supervisor_prompt"] = req.workflow_supervisor_prompt
        if req.name is not None:
            updates["name"] = req.name
        if req.members is not None:
            updates["members"] = req.members

        result = get_user_group_manager(request).update_group(req.workspace_id, req.group_id, updates)
        if not result:
            raise HTTPException(status_code=404, detail="Group not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{group_id}")
def delete_group(group_id: str, workspace_id: str, request: Request):
    try:
        get_user_group_manager(request).delete_group(workspace_id, group_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{group_id}/messages")
def get_group_messages(group_id: str, workspace_id: str, request: Request, limit: int = 100):
    """获取群聊历史消息（最近 limit 条）"""
    try:
        messages = get_user_group_manager(request).get_messages(workspace_id, group_id, limit)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{group_id}/clear")
def clear_group_messages(group_id: str, workspace_id: str, request: Request):
    """清空群聊历史消息"""
    try:
        get_user_group_manager(request).clear_messages(workspace_id, group_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# Workflow Mode Endpoints (New)
# ============================================================

@router.post("/plan")
async def generate_workflow_plan(req: GenerateWorkflowRequest, request: Request):
    """Generate a complete workflow plan using the Supervisor."""
    try:
        group_config = get_user_group_manager(request).get_group(req.workspace_id, req.group_id)
        if not group_config:
            raise HTTPException(status_code=404, detail="Group not found")

        supervisor_id = group_config.get("supervisor_id")
        if not supervisor_id:
            raise HTTPException(status_code=400, detail="Group has no supervisor configured")

        supervisor_agent = ModelAgent(supervisor_id, req.workspace_id, get_user_file_manager(request), get_user_agent_registry(request))
        chat = GroupChat(supervisor_agent=supervisor_agent)

        for agent_id in group_config["members"]:
            if agent_id == supervisor_id:
                continue
            try:
                agent = ModelAgent(agent_id, req.workspace_id, get_user_file_manager(request), get_user_agent_registry(request))
                chat.add_agent(agent)
            except Exception:
                print(f"Warning: Member {agent_id} not found, skipping.")

        workflow = await chat.generate_workflow(req.user_request)
        
        return {"workflow": workflow, "status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import StreamingResponse
import asyncio
import json

@router.post("/execute")
async def execute_workflow_plan(req: ExecuteWorkflowRequest, request: Request):
    """Execute a pre-generated workflow plan with SSE streaming."""
    try:
        group_config = get_user_group_manager(request).get_group(req.workspace_id, req.group_id)
        if not group_config:
            raise HTTPException(status_code=404, detail="Group not found")

        supervisor_id = group_config.get("supervisor_id")
        if not supervisor_id:
            raise HTTPException(status_code=400, detail="Group has no supervisor configured")

        try:
            supervisor_agent = ModelAgent(supervisor_id, req.workspace_id, get_user_file_manager(request), get_user_agent_registry(request))
        except Exception as e:
            print(f"[GroupRouter] CRITICAL ERROR: Supervisor agent '{supervisor_id}' failed to initialize: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Supervisor agent '{supervisor_id}' initialization failed: {str(e)}")

        chat = GroupChat(supervisor_agent=supervisor_agent)

        for agent_id in group_config["members"]:
            if agent_id == supervisor_id:
                continue
            try:
                agent = ModelAgent(agent_id, req.workspace_id, get_user_file_manager(request), get_user_agent_registry(request))
                chat.add_agent(agent)
            except Exception as e:
                print(f"[GroupRouter] ERROR: Failed to initialize member {agent_id} in workflow: {e}")
                import traceback
                traceback.print_exc()
                print(f"Warning: Member {agent_id} not found, skipping.")

        # SSE Setup
        queue = asyncio.Queue()
        task_done_event = asyncio.Event()

        async def save_progress(step_data: Dict[str, Any]):
            """Callback to save agent response and push to SEE queue."""
            try:
                agent_name = step_data.get("agent_name", "System")
                content = step_data.get("content", "")
                
                # ... (Agent ID lookup logic from before) ...
                agent_id = None
                agent = chat.members.get(agent_name)
                agent_id = agent.agent_id if agent else None
                
                # 1. Save to DB
                message = get_user_group_manager(request).add_message(
                    req.workspace_id, 
                    req.group_id, 
                    role="assistant",
                    content=content,
                    agent_id=agent_id,
                    agent_name=agent_name
                )
                print(f"[GroupRouter] Saved message from {agent_name}")

                # 2. Push to Queue (SSE)
                # Format: event: agent_message\ndata: {json}\n\n
                sse_data = {
                    "role": "assistant",
                    "content": content,
                    "name": agent_name,
                    "shouldAnimate": True
                }
                await queue.put(f"event: agent_message\ndata: {json.dumps(sse_data, ensure_ascii=False)}\n\n")

            except Exception as ex:
                print(f"[GroupRouter] Error saving/streaming progress: {ex}")

        async def run_workflow_background():
            """Background task to run workflow."""
            try:
                print("[GroupRouter] Starting background workflow execution...")
                await chat.execute_workflow(req.workflow, req.history, on_step_complete=save_progress)
                print("[GroupRouter] Workflow execution finished.")
            except Exception as e:
                print(f"[GroupRouter] Workflow failed: {e}")
                err_data = {"role": "system", "content": f"Error: {str(e)}"}
                await queue.put(f"event: error\ndata: {json.dumps(err_data)}\n\n")
            finally:
                task_done_event.set()
                # Push a final keep-alive or finish signal if needed, or just let generator exit
                await queue.put(None) # Sentinel

        async def event_generator():
            """Yield sse events from queue."""
            # Start background task
            asyncio.create_task(run_workflow_background())

            while True:
                # Wait for next item
                data = await queue.get()
                
                if data is None: # Sentinel
                    # Workflow finished
                    yield "event: finish\ndata: {}\n\n"
                    break
                
                yield data

                # Optional: periodic heartbeat if queue is empty for a while?
                # For now, simple consume is enough.

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# Legacy Step-by-Step Mode
# ============================================================

@router.post("/chat")
async def group_chat_turn(req: GroupChatRequest, request: Request):
    """
    Run one turn of the Group Chat.
    Uses group's supervisor_id from config.
    """
    with open("backend_debug.log", "a", encoding="utf-8") as f:
         f.write(f"[{datetime.now()}] Incoming request to /chat: {req.group_id}\n")

    try:
        # 1. Load Group Config
        group_config = get_user_group_manager(request).get_group(req.workspace_id, req.group_id)
        if not group_config:
            raise HTTPException(status_code=404, detail="Group not found")

        # 2. Get Supervisor from group config
        supervisor_id = group_config.get("supervisor_id")
        if not supervisor_id:
            raise HTTPException(status_code=400, detail="Group has no supervisor configured")

        supervisor_agent = ModelAgent(supervisor_id, req.workspace_id, get_user_file_manager(request), get_user_agent_registry(request))

        # Apply custom workflow supervisor prompt if set
        workflow_custom_prompt = group_config.get("workflow_supervisor_prompt", "")
        if workflow_custom_prompt:
            supervisor_agent.system_prompt = workflow_custom_prompt

        # [NEW] Load persisted state
        initial_state = group_config.get("chat_state")
        chat = GroupChat(supervisor_agent=supervisor_agent, max_turns=5, initial_state=initial_state)

        # 3. Add Members (excluding supervisor who orchestrates)
        for agent_id in group_config["members"]:
            if agent_id == supervisor_id:
                continue  # Supervisor orchestrates, doesn't participate as worker
            try:
                agent = ModelAgent(agent_id, req.workspace_id, get_user_file_manager(request), get_user_agent_registry(request))
                chat.add_agent(agent)
            except Exception as e:
                print(f"[GroupRouter] ERROR: Failed to initialize member {agent_id}: {e}")
                import traceback
                traceback.print_exc()
                print(f"Warning: Member {agent_id} not found or failed init, skipping.")

        # 4. Load History
        chat.history = req.history

        # 6. User Input & Persistence
        if req.message:
            # Save user message to storage
            get_user_group_manager(request).add_message(
                req.workspace_id,
                req.group_id,
                role="user",
                content=req.message
            )
            # Add to memory history
            chat.history.append({"role": "user", "content": req.message})

        # 7. Run one step
        with open("backend_debug.log", "a", encoding="utf-8") as f:
             f.write(f"\n[{datetime.now()}] Step started. History len: {len(chat.history)}\n")

        start_len = len(chat.history)
        should_continue = await chat.step()
        end_len = len(chat.history)
        
        # [NEW] Persist State
        try:
            get_user_group_manager(request).update_group(
                req.workspace_id,
                req.group_id,
                { "chat_state": chat.chat_state }
            )
        except Exception as e:
            print(f"[GroupRouter] Failed to save chat state: {e}")

        with open("backend_debug.log", "a", encoding="utf-8") as f:
             f.write(f"[{datetime.now()}] Step done. New len: {end_len}. Diff: {end_len - start_len}\n")

        # 8. Save all new messages
        new_messages = chat.history[start_len:end_len]
        
        for msg in new_messages:
            try:
                role = msg.get("role")
                content = msg.get("content")
                name = msg.get("name")
                
                with open("backend_debug.log", "a", encoding="utf-8") as f:
                     f.write(f"[{datetime.now()}] Saving msg: {name} - {content[:20]}...\n")

                get_user_group_manager(request).add_message(
                    req.workspace_id,
                    req.group_id,
                    role="assistant",
                    content=content,
                    agent_name=name,
                    # [NEW] Pass extra fields if present
                    is_plan=msg.get("is_plan", False),
                    plan_data=msg.get("plan_data")
                )
            except Exception as e:
                 with open("backend_debug.log", "a", encoding="utf-8") as f:
                      f.write(f"[{datetime.now()}] ERROR saving {name}: {e}\n")
                 import traceback
                 traceback.print_exc()

        # Return the last message for immediate UI feedback (or the entire history?)
        last_msg = chat.history[-1] if chat.history else {}
        
        # [NEW] Check for Plan Data to send to Right Panel
        current_plan = None
        for msg in new_messages:
            if msg.get("is_plan") and msg.get("plan_data"):
                current_plan = msg.get("plan_data")
                break
        
        response_data = {
            "response": last_msg.get("content", ""),
            "messages": new_messages,
            "status": "CONTINUE" if should_continue else "FINISH"
        }
        
        if current_plan:
            response_data["current_plan"] = current_plan
            
        return response_data

    except Exception as e:
        with open("backend_debug.log", "a", encoding="utf-8") as f:
             f.write(f"[{datetime.now()}] CRITICAL ERROR in group_chat_turn: {e}\n")
             import traceback
             traceback.print_exc(file=f)
        
        import traceback
        traceback.print_exc()
        # Return a 500 error but try to be descriptive
        raise HTTPException(status_code=500, detail=f"Group Chat Error: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SSE Streaming: Group Chat with Real-time Activity Events
# ============================================================

@router.post("/chat/stream")
async def group_chat_stream(req: GroupChatRequest, request: Request):
    """
    Streaming version of /chat. Emits SSE events as the group chat executes.
    Events: agent_thinking, tool_call, tool_result, agent_message, finish, error
    """
    queue: asyncio.Queue = asyncio.Queue()

    async def on_event(event: dict):
        print(f"[SSE] Event queued: {event.get('type')} agent={event.get('agent', 'N/A')}")
        await queue.put(event)

    async def run_step():
        try:
            group_config = get_user_group_manager(request).get_group(req.workspace_id, req.group_id)
            if not group_config:
                await queue.put({"type": "error", "content": "Group not found"})
                return

            supervisor_id = group_config.get("supervisor_id")
            if not supervisor_id:
                await queue.put({"type": "error", "content": "No supervisor configured"})
                return

            supervisor_agent = ModelAgent(supervisor_id, req.workspace_id, get_user_file_manager(request), get_user_agent_registry(request))
            workflow_custom_prompt = group_config.get("workflow_supervisor_prompt", "")
            if workflow_custom_prompt:
                supervisor_agent.system_prompt = workflow_custom_prompt

            initial_state = group_config.get("chat_state")
            chat = GroupChat(supervisor_agent=supervisor_agent, max_turns=5, initial_state=initial_state)

            for agent_id in group_config["members"]:
                if agent_id == supervisor_id:
                    continue
                try:
                    agent = ModelAgent(agent_id, req.workspace_id, get_user_file_manager(request), get_user_agent_registry(request))
                    chat.add_agent(agent)
                except Exception:
                    pass

            chat.history = req.history or []

            if req.message:
                get_user_group_manager(request).add_message(req.workspace_id, req.group_id, role="user", content=req.message)
                chat.history.append({"role": "user", "content": req.message})

            # Inject on_event into GroupChat so it threads down to agent execution
            chat._on_event = on_event

            start_len = len(chat.history)
            should_continue = await chat.step()
            end_len = len(chat.history)

            # Persist state
            try:
                get_user_group_manager(request).update_group(req.workspace_id, req.group_id, {"chat_state": chat.chat_state})
            except Exception:
                pass

            # Save new messages
            for msg in chat.history[start_len:end_len]:
                try:
                    get_user_group_manager(request).add_message(
                        req.workspace_id, req.group_id,
                        role="assistant", content=msg.get("content", ""),
                        agent_name=msg.get("name"),
                        is_plan=msg.get("is_plan", False),
                        plan_data=msg.get("plan_data")
                    )
                except Exception:
                    pass

            # Check for plan
            for msg in chat.history[start_len:end_len]:
                if msg.get("is_plan") and msg.get("plan_data"):
                    await queue.put({"type": "plan", "data": msg["plan_data"]})
                    break

            await queue.put({"type": "finish", "status": "CONTINUE" if should_continue else "FINISH"})
        except Exception as e:
            import traceback
            traceback.print_exc()
            await queue.put({"type": "error", "content": str(e)})

    async def event_generator():
        print("[SSE] Starting event generator...")
        asyncio.create_task(run_step())
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=300)
            data = json.dumps(event, ensure_ascii=False)
            event_type = event.get("type", "message")
            print(f"[SSE] Yielding event: {event_type}")
            yield f"event: {event_type}\ndata: {data}\n\n"
            if event_type in ("finish", "error"):
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")
