"""
Schedule Router — 定时任务 CRUD API（Supabase 版）
"""

import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.user_deps import get_user_id
from backend.supabase_client import supabase
from backend.scheduler import register_task, unregister_task

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class CreateTaskRequest(BaseModel):
    agent_id: str
    workspace_id: str

    mode: str  # "calendar" | "interval"

    # calendar mode
    scope: Optional[str] = None           # "every" | "this"
    calendar_unit: Optional[str] = None   # "day" | "week" | "month"
    time: Optional[str] = None            # "HH:MM"
    day_of_week: Optional[str] = None     # "mon"~"sun"
    day_of_month: Optional[int] = None    # 1~31

    # interval mode
    work_start: Optional[str] = None
    work_end: Optional[str] = None
    interval_value: Optional[int] = None
    interval_unit: Optional[str] = None   # "minutes"|"hours"|"days"|"weeks"

    prompt: str
    enabled: bool = True


class UpdateTaskRequest(BaseModel):
    task_id: str
    enabled: Optional[bool] = None

    mode: Optional[str] = None
    scope: Optional[str] = None
    calendar_unit: Optional[str] = None
    time: Optional[str] = None
    day_of_week: Optional[str] = None
    day_of_month: Optional[int] = None

    work_start: Optional[str] = None
    work_end: Optional[str] = None
    interval_value: Optional[int] = None
    interval_unit: Optional[str] = None

    prompt: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/create")
def create_task(req: CreateTaskRequest, request: Request):
    """Create a new scheduled task."""
    user_id = get_user_id(request)
    task_id = f"sched_{uuid.uuid4().hex[:8]}"

    task = {
        "id": task_id,
        "user_id": user_id,
        "agent_id": req.agent_id,
        "workspace_id": req.workspace_id,
        "mode": req.mode,
        "scope": req.scope,
        "calendar_unit": req.calendar_unit,
        "time": req.time,
        "day_of_week": req.day_of_week,
        "day_of_month": req.day_of_month,
        "work_start": req.work_start,
        "work_end": req.work_end,
        "interval_value": req.interval_value,
        "interval_unit": req.interval_unit,
        "prompt": req.prompt,
        "enabled": req.enabled,
    }

    supabase.table("scheduled_tasks").insert(task).execute()

    if task["enabled"]:
        register_task(task, user_id)

    return {"status": "success", "task_id": task_id}


@router.get("/list")
def list_tasks(request: Request, agent_id: Optional[str] = None):
    """List scheduled tasks, optionally filtered by agent_id."""
    user_id = get_user_id(request)
    query = supabase.table("scheduled_tasks") \
        .select("*") \
        .eq("user_id", user_id)
    if agent_id:
        query = query.eq("agent_id", agent_id)
    result = query.execute()
    return result.data


@router.post("/update")
def update_task(req: UpdateTaskRequest, request: Request):
    """Update a scheduled task."""
    user_id = get_user_id(request)

    # Check exists
    existing = supabase.table("scheduled_tasks") \
        .select("*") \
        .eq("id", req.task_id) \
        .eq("user_id", user_id) \
        .execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Task not found")

    # Apply updates
    update_fields = req.model_dump(exclude_unset=True, exclude={"task_id"})
    safe_updates = {k: v for k, v in update_fields.items() if v is not None}

    if safe_updates:
        supabase.table("scheduled_tasks") \
            .update(safe_updates) \
            .eq("id", req.task_id) \
            .execute()

    # Sync scheduler
    updated = supabase.table("scheduled_tasks") \
        .select("*") \
        .eq("id", req.task_id) \
        .execute()
    task = updated.data[0] if updated.data else existing.data[0]

    if task.get("enabled"):
        register_task(task, user_id)
    else:
        unregister_task(task["id"])

    return {"status": "success"}


@router.delete("/delete/{task_id}")
def delete_task(task_id: str, request: Request):
    """Delete a scheduled task."""
    user_id = get_user_id(request)

    existing = supabase.table("scheduled_tasks") \
        .select("id") \
        .eq("id", task_id) \
        .eq("user_id", user_id) \
        .execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Task not found")

    supabase.table("scheduled_tasks") \
        .delete() \
        .eq("id", task_id) \
        .execute()
    unregister_task(task_id)

    return {"status": "success"}


# ---------------------------------------------------------------------------
# Inbox endpoints (Supabase)
# ---------------------------------------------------------------------------

@router.get("/inbox")
def get_inbox(request: Request, agent_id: str):
    """Get unread inbox messages for an agent."""
    user_id = get_user_id(request)
    result = supabase.table("inbox") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("agent_id", agent_id) \
        .eq("read", False) \
        .order("created_at", desc=False) \
        .execute()
    return result.data


@router.post("/inbox/mark-read")
def mark_read(request: Request, agent_id: str):
    """Mark all inbox messages for an agent as read."""
    user_id = get_user_id(request)
    supabase.table("inbox") \
        .update({"read": True}) \
        .eq("user_id", user_id) \
        .eq("agent_id", agent_id) \
        .eq("read", False) \
        .execute()
    return {"status": "success"}


@router.get("/inbox/unread-agents")
def get_unread_agents(request: Request):
    """Return a list of agent IDs that have unread inbox messages."""
    user_id = get_user_id(request)
    result = supabase.table("inbox") \
        .select("agent_id") \
        .eq("user_id", user_id) \
        .eq("read", False) \
        .execute()

    # Deduplicate agent IDs
    seen = set()
    agents = []
    for row in result.data:
        aid = row.get("agent_id")
        if aid and aid not in seen:
            seen.add(aid)
            agents.append(aid)
    return agents
