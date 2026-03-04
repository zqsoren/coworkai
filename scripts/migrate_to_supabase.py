"""
数据迁移脚本：从本地 JSON 文件迁移到 Supabase
用法: python scripts/migrate_to_supabase.py

⚠️ 注意：此脚本应在设置好 .env 中的 Supabase 凭证后运行。
   脚本是幂等的：重复运行会跳过已存在的记录。
"""

import os
import sys
import json
import glob
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from backend.supabase_client import supabase

DATA_ROOT = os.path.join(PROJECT_ROOT, "data")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")


def log(msg):
    print(f"[Migrate] {msg}")


def migrate_users():
    """迁移 data/users.json → users 表"""
    users_file = os.path.join(DATA_ROOT, "users.json")
    if not os.path.exists(users_file):
        log("users.json 不存在，跳过。")
        return

    with open(users_file, "r", encoding="utf-8") as f:
        users = json.load(f)

    count = 0
    for user_id, info in users.items():
        # 检查是否已存在
        existing = supabase.table("users").select("id").eq("id", user_id).execute()
        if existing.data:
            log(f"  用户 {user_id} 已存在，跳过。")
            continue

        supabase.table("users").insert({
            "id": user_id,
            "username": info.get("username", ""),
            "phone": info.get("phone", ""),
            "password_hash": info.get("password_hash", ""),
            "created_at": info.get("created_at", datetime.now().isoformat()),
        }).execute()
        count += 1
        log(f"  ✓ 用户 {user_id} ({info.get('username', '')}) 已迁移。")

    log(f"用户迁移完成：{count} 个新用户。")


def migrate_agents(user_id: str):
    """迁移 agents_registry.json → agents 表"""
    registry_file = os.path.join(DATA_ROOT, user_id, "agents_registry.json")
    if not os.path.exists(registry_file):
        log(f"  {user_id}/agents_registry.json 不存在，跳过。")
        return

    with open(registry_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    agents = data.get("agents", data)  # 兼容两种格式
    if isinstance(agents, dict):
        # {agent_id: config} 格式
        items = agents.items()
    elif isinstance(agents, list):
        items = [(a.get("id", f"agent_{i}"), a) for i, a in enumerate(agents)]
    else:
        log(f"  未知 agents_registry.json 格式，跳过。")
        return

    count = 0
    for agent_id, config in items:
        existing = supabase.table("agents") \
            .select("id") \
            .eq("id", agent_id) \
            .eq("user_id", user_id) \
            .execute()
        if existing.data:
            continue

        row = {
            "id": agent_id,
            "user_id": user_id,
            "workspace": config.get("workspace"),
            "name": config.get("name", agent_id),
            "system_prompt": config.get("system_prompt", ""),
            "provider_id": config.get("provider_id"),
            "model_name": config.get("model_name"),
            "persona_mode": config.get("persona_mode", "efficient"),
            "tools": config.get("tools", []),
            "skills": config.get("skills", []),
            "mcp_servers": config.get("mcp_servers", []),
            "tags": config.get("tags", []),
            "knowledge_base": config.get("knowledge_base", []),
        }
        supabase.table("agents").insert(row).execute()
        count += 1

    log(f"  ✓ {count} 个智能体已迁移。")


def migrate_workspaces(user_id: str):
    """扫描 workspace_* 目录 → workspaces 表"""
    user_dir = os.path.join(DATA_ROOT, user_id)
    count = 0
    for item in os.listdir(user_dir):
        if not item.startswith("workspace_"):
            continue
        ws_path = os.path.join(user_dir, item)
        if not os.path.isdir(ws_path):
            continue

        existing = supabase.table("workspaces") \
            .select("id") \
            .eq("id", item) \
            .eq("user_id", user_id) \
            .execute()
        if existing.data:
            continue

        # Try to read metadata
        meta_file = os.path.join(ws_path, "_workspace_meta.json")
        meta = {}
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                pass

        name = meta.get("name", item.replace("workspace_", ""))

        supabase.table("workspaces").insert({
            "id": item,
            "user_id": user_id,
            "name": name,
            "description": meta.get("description", ""),
        }).execute()
        count += 1

    log(f"  ✓ {count} 个工作区已迁移。")


def migrate_llm_providers(user_id: str):
    """迁移 llm_providers.json → llm_providers 表"""
    llm_file = os.path.join(DATA_ROOT, user_id, "llm_providers.json")
    if not os.path.exists(llm_file):
        log(f"  {user_id}/llm_providers.json 不存在，跳过。")
        return

    with open(llm_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    providers = data.get("providers", [])
    count = 0
    for p in providers:
        existing = supabase.table("llm_providers") \
            .select("id") \
            .eq("id", p["id"]) \
            .eq("user_id", user_id) \
            .execute()
        if existing.data:
            continue

        supabase.table("llm_providers").insert({
            "id": p["id"],
            "user_id": user_id,
            "type": p.get("type", "openai_compatible"),
            "name": p.get("name", p["id"]),
            "models": p.get("models", []),
            "base_url": p.get("base_url"),
            "api_key_env": p.get("api_key_env", "EMPTY"),
            "is_builtin": p.get("is_builtin", False),
        }).execute()
        count += 1

    log(f"  ✓ {count} 个 LLM Provider 已迁移。")


def migrate_scheduled_tasks(user_id: str):
    """迁移 scheduled_tasks.json → scheduled_tasks 表"""
    tasks_file = os.path.join(DATA_ROOT, user_id, "scheduled_tasks.json")
    if not os.path.exists(tasks_file):
        return

    with open(tasks_file, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    count = 0
    for t in tasks:
        existing = supabase.table("scheduled_tasks") \
            .select("id") \
            .eq("id", t["id"]) \
            .execute()
        if existing.data:
            continue

        row = {
            "id": t["id"],
            "user_id": user_id,
            "agent_id": t.get("agent_id", ""),
            "workspace_id": t.get("workspace_id", ""),
            "mode": t.get("mode", "calendar"),
            "scope": t.get("scope"),
            "calendar_unit": t.get("calendar_unit"),
            "time": t.get("time"),
            "day_of_week": t.get("day_of_week"),
            "day_of_month": t.get("day_of_month"),
            "work_start": t.get("work_start"),
            "work_end": t.get("work_end"),
            "interval_value": t.get("interval_value"),
            "interval_unit": t.get("interval_unit"),
            "prompt": t.get("prompt", ""),
            "enabled": t.get("enabled", False),
        }
        supabase.table("scheduled_tasks").insert(row).execute()
        count += 1

    if count > 0:
        log(f"  ✓ {count} 个定时任务已迁移。")


def migrate_inbox(user_id: str):
    """迁移 inbox/*.json → inbox 表"""
    inbox_dir = os.path.join(DATA_ROOT, user_id, "inbox")
    if not os.path.isdir(inbox_dir):
        return

    count = 0
    for fname in os.listdir(inbox_dir):
        if not fname.endswith(".json"):
            continue
        agent_id = fname[:-5]
        fpath = os.path.join(inbox_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            continue

        for rec in records:
            supabase.table("inbox").insert({
                "user_id": user_id,
                "agent_id": agent_id,
                "task_id": rec.get("task_id"),
                "prompt": rec.get("prompt"),
                "response": rec.get("response"),
                "read": rec.get("read", False),
            }).execute()
            count += 1

    if count > 0:
        log(f"  ✓ {count} 条收件箱消息已迁移。")


def migrate_group_chats(user_id: str):
    """迁移群聊配置和消息"""
    user_dir = os.path.join(DATA_ROOT, user_id)
    total_groups = 0
    total_messages = 0

    for item in os.listdir(user_dir):
        ws_dir = os.path.join(user_dir, item)
        if not os.path.isdir(ws_dir) or not item.startswith("workspace_"):
            continue

        # 群聊配置
        chats_file = os.path.join(ws_dir, "_group_chats.json")
        if not os.path.exists(chats_file):
            continue

        try:
            with open(chats_file, "r", encoding="utf-8") as f:
                groups = json.load(f)
        except Exception:
            continue

        for g in groups:
            group_id = g.get("id", g.get("group_id", ""))
            if not group_id:
                continue

            existing = supabase.table("group_chats") \
                .select("id") \
                .eq("id", group_id) \
                .eq("user_id", user_id) \
                .execute()
            if existing.data:
                continue

            supabase.table("group_chats").insert({
                "id": group_id,
                "user_id": user_id,
                "workspace_id": item,
                "name": g.get("name", group_id),
                "members": g.get("members", []),
                "supervisor_id": g.get("supervisor_id"),
                "supervisor_prompt": g.get("supervisor_prompt", ""),
                "workflow_supervisor_prompt": g.get("workflow_supervisor_prompt", ""),
            }).execute()
            total_groups += 1

            # 群聊消息
            msg_file = os.path.join(ws_dir, f"_group_messages_{group_id}.json")
            if os.path.exists(msg_file):
                try:
                    with open(msg_file, "r", encoding="utf-8") as f:
                        messages = json.load(f)
                    for msg in messages:
                        supabase.table("group_messages").insert({
                            "user_id": user_id,
                            "group_id": group_id,
                            "role": msg.get("role", "user"),
                            "content": msg.get("content", ""),
                            "agent_id": msg.get("agent_id"),
                            "agent_name": msg.get("agent_name") or msg.get("name"),
                            "extra": {k: v for k, v in msg.items()
                                      if k not in ("role", "content", "agent_id", "agent_name", "name", "timestamp")},
                        }).execute()
                        total_messages += 1
                except Exception as e:
                    log(f"    ⚠ 消息迁移失败 ({msg_file}): {e}")

    if total_groups > 0 or total_messages > 0:
        log(f"  ✓ {total_groups} 个群聊, {total_messages} 条消息已迁移。")


def migrate_output_modes():
    """迁移 config/output_modes.json → output_modes 表（跳过已有的内建模式）"""
    modes_file = os.path.join(CONFIG_DIR, "output_modes.json")
    if not os.path.exists(modes_file):
        log("config/output_modes.json 不存在，跳过。")
        return

    with open(modes_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    modes = data.get("modes", data) if isinstance(data, dict) else data
    if isinstance(modes, dict):
        items = modes.items()
    elif isinstance(modes, list):
        items = [(m.get("id", m.get("name", f"mode_{i}")), m) for i, m in enumerate(modes)]
    else:
        return

    count = 0
    for mode_id, mode in items:
        existing = supabase.table("output_modes") \
            .select("id") \
            .eq("id", mode_id) \
            .execute()
        if existing.data:
            continue

        supabase.table("output_modes").insert({
            "id": mode_id,
            "name": mode.get("name", mode_id),
            "description": mode.get("description", ""),
            "prompt": mode.get("prompt", ""),
            "is_builtin": mode.get("is_builtin", False),
        }).execute()
        count += 1

    if count > 0:
        log(f"✓ {count} 个输出模式已迁移。")


def main():
    log("=" * 50)
    log("AgentOS → Supabase 数据迁移开始")
    log("=" * 50)

    # 1. 用户
    log("\n[1/7] 迁移用户...")
    migrate_users()

    # 2. 遍历每个用户目录
    user_dirs = [d for d in os.listdir(DATA_ROOT)
                 if d.startswith("user_") and os.path.isdir(os.path.join(DATA_ROOT, d))]

    for user_id in user_dirs:
        log(f"\n--- 用户: {user_id} ---")

        log(f"[2/7] 迁移智能体...")
        migrate_agents(user_id)

        log(f"[3/7] 迁移工作区...")
        migrate_workspaces(user_id)

        log(f"[4/7] 迁移 LLM 配置...")
        migrate_llm_providers(user_id)

        log(f"[5/7] 迁移定时任务...")
        migrate_scheduled_tasks(user_id)

        log(f"[6/7] 迁移收件箱...")
        migrate_inbox(user_id)

        log(f"[7/7] 迁移群聊...")
        migrate_group_chats(user_id)

    # 8. 输出模式
    log(f"\n[额外] 迁移输出模式...")
    migrate_output_modes()

    log("\n" + "=" * 50)
    log("迁移完成！")
    log("请打开 Supabase Table Editor 验证数据。")
    log("=" * 50)


if __name__ == "__main__":
    main()
