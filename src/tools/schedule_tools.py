"""
Schedule Tools - 定时任务管理工具（系统默认工具）
允许 Agent 自主创建、查看和删除定时任务。
"""

import uuid
from langchain_core.tools import tool

# 模块级上下文 — 在每次图执行前设置
_schedule_context = {
    "user_id": None,
    "workspace_id": None,
    "agent_id": None,
}


def init_schedule_context(user_id: str, workspace_id: str, agent_id: str):
    """在图执行前调用，设置当前上下文"""
    _schedule_context["user_id"] = user_id
    _schedule_context["workspace_id"] = workspace_id
    _schedule_context["agent_id"] = agent_id


@tool
def create_scheduled_task(
    prompt: str,
    mode: str = "calendar",
    time: str = "09:00",
    scope: str = "every",
    calendar_unit: str = "day",
    day_of_week: str = "",
    day_of_month: int = 0,
    interval_value: int = 0,
    interval_unit: str = "hours",
    work_start: str = "09:00",
    work_end: str = "18:00",
) -> str:
    """创建一个定时任务，让 Agent 在指定时间自动执行指定指令。

    Args:
        prompt: 定时执行的指令内容（必填）
        mode: 定时模式，"calendar"=日历模式（每天/每周/每月固定时间），"interval"=间隔模式（每隔N小时/分钟）
        time: 执行时间，格式 "HH:MM"，如 "09:00"（日历模式用）
        scope: 日历模式范围，"every"=每次，"this"=仅一次
        calendar_unit: 日历单位，"day"=每天，"week"=每周，"month"=每月
        day_of_week: 每周几执行，如 "mon"/"tue"/"wed"/"thu"/"fri"/"sat"/"sun"（周模式用）
        day_of_month: 每月几号执行，1-31（月模式用）
        interval_value: 间隔值（间隔模式用）
        interval_unit: 间隔单位，"minutes"/"hours"/"days"/"weeks"（间隔模式用）
        work_start: 工作开始时间 "HH:MM"（间隔模式用，限制执行窗口）
        work_end: 工作结束时间 "HH:MM"（间隔模式用）
    """
    user_id = _schedule_context.get("user_id")
    workspace_id = _schedule_context.get("workspace_id")
    agent_id = _schedule_context.get("agent_id")

    if not user_id or not workspace_id or not agent_id:
        return "错误：无法获取当前用户上下文，定时任务创建失败。"

    try:
        from backend.supabase_client import supabase
        from backend.scheduler import register_task

        task_id = f"sched_{uuid.uuid4().hex[:8]}"
        task = {
            "id": task_id,
            "user_id": user_id,
            "agent_id": agent_id,
            "workspace_id": workspace_id,
            "mode": mode,
            "scope": scope if mode == "calendar" else None,
            "calendar_unit": calendar_unit if mode == "calendar" else None,
            "time": time if mode == "calendar" else None,
            "day_of_week": day_of_week if mode == "calendar" and calendar_unit == "week" else None,
            "day_of_month": day_of_month if mode == "calendar" and calendar_unit == "month" else None,
            "work_start": work_start if mode == "interval" else None,
            "work_end": work_end if mode == "interval" else None,
            "interval_value": interval_value if mode == "interval" else None,
            "interval_unit": interval_unit if mode == "interval" else None,
            "prompt": prompt,
            "enabled": True,
        }

        supabase.table("scheduled_tasks").insert(task).execute()
        register_task(task, user_id)

        # 生成可读描述
        if mode == "calendar":
            if calendar_unit == "day":
                desc = f"每天 {time}"
            elif calendar_unit == "week":
                desc = f"每周{day_of_week} {time}"
            elif calendar_unit == "month":
                desc = f"每月{day_of_month}号 {time}"
            else:
                desc = f"{time}"
        else:
            desc = f"每{interval_value}{interval_unit}（{work_start}-{work_end}）"

        return f"✅ 定时任务创建成功！\n- ID: {task_id}\n- 执行频率: {desc}\n- 执行指令: {prompt}"

    except Exception as e:
        return f"创建定时任务失败: {str(e)}"


@tool
def list_scheduled_tasks() -> str:
    """查看当前 Agent 的所有定时任务。"""
    user_id = _schedule_context.get("user_id")
    agent_id = _schedule_context.get("agent_id")

    if not user_id:
        return "错误：无法获取当前用户上下文。"

    try:
        from backend.supabase_client import supabase

        query = supabase.table("scheduled_tasks") \
            .select("*") \
            .eq("user_id", user_id)
        if agent_id:
            query = query.eq("agent_id", agent_id)

        result = query.execute()
        tasks = result.data

        if not tasks:
            return "当前没有任何定时任务。"

        lines = [f"📋 共 {len(tasks)} 个定时任务：\n"]
        for t in tasks:
            status = "✅ 启用" if t.get("enabled") else "⏸ 暂停"
            mode = t.get("mode", "unknown")
            if mode == "calendar":
                unit = t.get("calendar_unit", "day")
                time_str = t.get("time", "")
                if unit == "day":
                    freq = f"每天 {time_str}"
                elif unit == "week":
                    freq = f"每周{t.get('day_of_week', '')} {time_str}"
                elif unit == "month":
                    freq = f"每月{t.get('day_of_month', '')}号 {time_str}"
                else:
                    freq = time_str
            else:
                freq = f"每{t.get('interval_value', '')}{t.get('interval_unit', '')}"

            lines.append(f"• [{status}] {t['id']}")
            lines.append(f"  频率: {freq}")
            lines.append(f"  指令: {t.get('prompt', '')[:80]}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"查询定时任务失败: {str(e)}"


@tool
def delete_scheduled_task(task_id: str) -> str:
    """删除指定的定时任务。

    Args:
        task_id: 要删除的任务 ID（格式如 sched_xxxxxxxx）
    """
    user_id = _schedule_context.get("user_id")

    if not user_id:
        return "错误：无法获取当前用户上下文。"

    try:
        from backend.supabase_client import supabase
        from backend.scheduler import unregister_task

        # 验证任务归属
        result = supabase.table("scheduled_tasks") \
            .select("*") \
            .eq("id", task_id) \
            .eq("user_id", user_id) \
            .execute()

        if not result.data:
            return f"未找到任务 {task_id}，请检查任务 ID。"

        # 从调度器注销
        unregister_task(task_id)

        # 从数据库删除
        supabase.table("scheduled_tasks") \
            .delete() \
            .eq("id", task_id) \
            .eq("user_id", user_id) \
            .execute()

        return f"✅ 定时任务 {task_id} 已删除。"

    except Exception as e:
        return f"删除定时任务失败: {str(e)}"


SCHEDULE_TOOLS = [create_scheduled_task, list_scheduled_tasks, delete_scheduled_task]
