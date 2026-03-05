"""
Scheduler — 定时任务调度引擎（Supabase 版）
基于 APScheduler BackgroundScheduler，随 FastAPI lifespan 启停。
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backend.supabase_client import supabase

logger = logging.getLogger("scheduler")
logger.setLevel(logging.INFO)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = os.path.join(PROJECT_ROOT, "data")

# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None


# ---------------------------------------------------------------------------
# Persistence helpers (Supabase)
# ---------------------------------------------------------------------------

def load_tasks(user_id: str) -> list[dict]:
    result = supabase.table("scheduled_tasks") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()
    return result.data


def save_tasks(user_id: str, tasks: list[dict]):
    """批量保存（先删再插）— 仅在批量操作时使用"""
    supabase.table("scheduled_tasks") \
        .delete() \
        .eq("user_id", user_id) \
        .execute()
    if tasks:
        rows = []
        for t in tasks:
            t["user_id"] = user_id
            rows.append(t)
        supabase.table("scheduled_tasks").insert(rows).execute()


# ---------------------------------------------------------------------------
# Task Execution
# ---------------------------------------------------------------------------

def _execute_task(task: dict, user_id: str):
    """Execute a scheduled task by invoking the agent graph."""
    task_id = task["id"]
    logger.info(f"[Scheduler] Executing task {task_id} for user {user_id}")

    # For interval mode: check work window
    if task["mode"] == "interval" and task.get("interval_unit") in ("minutes", "hours"):
        now = datetime.now()
        try:
            ws = datetime.strptime(task["work_start"], "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            we = datetime.strptime(task["work_end"], "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            if not (ws <= now <= we):
                logger.info(f"[Scheduler] Task {task_id} skipped — outside work window")
                return
        except Exception:
            pass

    try:
        from src.graph.agent_graph import create_compiled_graph
        from src.core.agent_registry import AgentRegistry
        from src.core.file_manager import FileManager
        from langchain_core.messages import HumanMessage, AIMessage

        user_root = os.path.join(DATA_ROOT, user_id)
        ar = AgentRegistry(user_id)
        fm = FileManager(user_root)

        agent_config = ar.get_agent(task["agent_id"])
        if not agent_config:
            logger.error(f"[Scheduler] Agent {task['agent_id']} not found")
            _mark_task_status(user_id, task_id, "error: agent not found")
            return

        # 注入用户上下文供定时任务工具使用
        agent_config["_user_id"] = user_id
        agent_config["_workspace_id"] = task.get("workspace_id", "")

        # Build context
        context = ""
        try:
            cfiles = fm.get_agent_context(task["workspace_id"], task["agent_id"])
            if cfiles:
                parts = ["## Context"]
                for k, v in cfiles.items():
                    parts.append(f"### {k}\n```\n{v[:1000]}\n```")
                context = "\n".join(parts)
        except Exception:
            pass

        # Load last 8 inbox messages as history
        history_messages = []
        inbox_result = supabase.table("inbox") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("agent_id", task["agent_id"]) \
            .order("created_at", desc=True) \
            .limit(8) \
            .execute()
        recent = list(reversed(inbox_result.data)) if inbox_result.data else []
        for rec in recent:
            history_messages.append(HumanMessage(content=rec.get("prompt", "")))
            if rec.get("response"):
                history_messages.append(AIMessage(content=rec["response"]))

        # Build messages: history + current prompt
        all_messages = history_messages + [HumanMessage(content=task["prompt"])]

        initial_state = {
            "messages": all_messages,
            "current_agent": task["agent_id"],
            "current_workspace": task["workspace_id"],
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

        # Write to inbox
        _write_inbox(user_id, task, final_response)
        _mark_task_status(user_id, task_id, "success")
        logger.info(f"[Scheduler] Task {task_id} completed successfully")

    except Exception as e:
        logger.error(f"[Scheduler] Task {task_id} failed: {e}", exc_info=True)
        _mark_task_status(user_id, task_id, f"error: {str(e)[:100]}")

    # Auto-disable one-shot tasks
    if task["mode"] == "calendar" and task.get("scope") == "this":
        _disable_task(user_id, task_id)


# ---------------------------------------------------------------------------
# Inbox — message delivery to frontend (Supabase)
# ---------------------------------------------------------------------------

def _write_inbox(user_id: str, task: dict, response: str):
    """Write the scheduled execution result into the agent's inbox."""
    supabase.table("inbox").insert({
        "user_id": user_id,
        "agent_id": task["agent_id"],
        "task_id": task["id"],
        "prompt": task["prompt"],
        "response": response,
        "read": False,
    }).execute()


def load_inbox(user_id: str, agent_id: str) -> list[dict]:
    """Public: load inbox for an agent (used by API router)."""
    result = supabase.table("inbox") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("agent_id", agent_id) \
        .order("created_at", desc=False) \
        .execute()
    return result.data


def mark_inbox_read(user_id: str, agent_id: str):
    """Public: mark all inbox messages as read."""
    supabase.table("inbox") \
        .update({"read": True}) \
        .eq("user_id", user_id) \
        .eq("agent_id", agent_id) \
        .eq("read", False) \
        .execute()


def _mark_task_status(user_id: str, task_id: str, status: str):
    supabase.table("scheduled_tasks") \
        .update({
            "last_run": datetime.now().isoformat(),
            "last_status": status,
        }) \
        .eq("id", task_id) \
        .execute()


def _disable_task(user_id: str, task_id: str):
    supabase.table("scheduled_tasks") \
        .update({"enabled": False}) \
        .eq("id", task_id) \
        .execute()

    # Remove from scheduler
    if _scheduler:
        try:
            _scheduler.remove_job(task_id)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Trigger builders
# ---------------------------------------------------------------------------

DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

def _build_trigger(task: dict):
    """Build an APScheduler trigger from a task config."""
    if task["mode"] == "calendar":
        scope = task.get("scope", "every")
        unit = task.get("calendar_unit", "day")
        time_str = task.get("time", "09:00")
        h, m = map(int, time_str.split(":"))

        if scope == "this":
            now = datetime.now()
            if unit == "day":
                run_date = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if run_date < now:
                    run_date += timedelta(days=1)
            elif unit == "week":
                dow_str = task.get("day_of_week", "mon")
                target_dow = DAY_MAP.get(dow_str, 0)
                days_ahead = target_dow - now.weekday()
                if days_ahead < 0 or (days_ahead == 0 and now.hour * 60 + now.minute >= h * 60 + m):
                    days_ahead += 7
                run_date = (now + timedelta(days=days_ahead)).replace(hour=h, minute=m, second=0, microsecond=0)
            elif unit == "month":
                dom = task.get("day_of_month", 1)
                try:
                    run_date = now.replace(day=dom, hour=h, minute=m, second=0, microsecond=0)
                except ValueError:
                    run_date = now.replace(day=28, hour=h, minute=m, second=0, microsecond=0)
                if run_date < now:
                    if now.month == 12:
                        run_date = run_date.replace(year=now.year + 1, month=1)
                    else:
                        run_date = run_date.replace(month=now.month + 1)
            else:
                run_date = now + timedelta(minutes=1)
            return DateTrigger(run_date=run_date)

        else:  # scope == "every"
            if unit == "day":
                return CronTrigger(hour=h, minute=m)
            elif unit == "week":
                dow_str = task.get("day_of_week", "mon")
                return CronTrigger(day_of_week=dow_str, hour=h, minute=m)
            elif unit == "month":
                dom = task.get("day_of_month", 1)
                return CronTrigger(day=dom, hour=h, minute=m)

    elif task["mode"] == "interval":
        val = task.get("interval_value", 1)
        unit = task.get("interval_unit", "hours")
        kwargs = {unit: val}
        return IntervalTrigger(**kwargs)

    return None


# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------

def _job_id(task: dict) -> str:
    return task["id"]


def register_task(task: dict, user_id: str):
    """Register a single task with the scheduler."""
    if not _scheduler:
        return
    trigger = _build_trigger(task)
    if not trigger:
        return

    job_id = _job_id(task)
    try:
        _scheduler.remove_job(job_id)
    except Exception:
        pass

    _scheduler.add_job(
        _execute_task,
        trigger=trigger,
        args=[task, user_id],
        id=job_id,
        name=f"sched_{task['agent_id']}_{job_id}",
        replace_existing=True,
    )
    logger.info(f"[Scheduler] Registered job {job_id} (mode={task['mode']})")


def unregister_task(task_id: str):
    """Remove a task from the scheduler."""
    if not _scheduler:
        return
    try:
        _scheduler.remove_job(task_id)
        logger.info(f"[Scheduler] Removed job {task_id}")
    except Exception:
        pass


def start_scheduler():
    """Start the background scheduler and load all tasks."""
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    _scheduler.start()
    logger.info("[Scheduler] Started")

    # Load all enabled tasks from Supabase
    result = supabase.table("scheduled_tasks") \
        .select("*") \
        .eq("enabled", True) \
        .execute()

    for task in result.data:
        user_id = task.get("user_id")
        if user_id:
            register_task(task, user_id)

    logger.info("[Scheduler] All tasks loaded")


def stop_scheduler():
    """Shut down the scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped")
        _scheduler = None
