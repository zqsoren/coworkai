"""
GroupChatManager - 群聊管理（Supabase 版）
管理群聊配置和消息，存储在 Supabase group_chats 和 group_messages 表。
"""
from datetime import datetime
from typing import List, Dict, Any, Optional

from backend.supabase_client import supabase


class GroupChatManager:
    """群聊管理器（Supabase 版）"""

    def __init__(self, user_id: str):
        self.user_id = user_id

    def list_groups(self, workspace_id: str) -> List[Dict[str, Any]]:
        result = supabase.table("group_chats") \
            .select("*") \
            .eq("user_id", self.user_id) \
            .eq("workspace_id", workspace_id) \
            .execute()
        return result.data

    def get_group(self, workspace_id: str, group_id: str) -> Optional[Dict[str, Any]]:
        result = supabase.table("group_chats") \
            .select("*") \
            .eq("id", group_id) \
            .eq("user_id", self.user_id) \
            .execute()
        return result.data[0] if result.data else None

    def create_group(self, workspace_id: str, name: str, member_ids: List[str], supervisor_id: str) -> Dict[str, Any]:
        # 获取当前群聊数量用于 ID 生成
        existing = supabase.table("group_chats") \
            .select("id") \
            .eq("user_id", self.user_id) \
            .eq("workspace_id", workspace_id) \
            .execute()

        group_id = f"group_{name.lower().replace(' ', '_')}_{len(existing.data) + 1}"

        new_group = {
            "id": group_id,
            "user_id": self.user_id,
            "workspace_id": workspace_id,
            "name": name,
            "members": member_ids,
            "supervisor_id": supervisor_id,
            "supervisor_prompt": "",
            "workflow_supervisor_prompt": "",
        }

        supabase.table("group_chats").insert(new_group).execute()

        # 返回不含 user_id 的兼容格式
        del new_group["user_id"]
        return new_group

    def update_group(self, workspace_id: str, group_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update group fields (supervisor_id, supervisor_prompt, name, etc.)."""
        allowed = {"name", "members", "supervisor_id", "supervisor_prompt", "workflow_supervisor_prompt"}
        safe_updates = {k: v for k, v in updates.items() if k in allowed}

        if not safe_updates:
            return self.get_group(workspace_id, group_id)

        supabase.table("group_chats") \
            .update(safe_updates) \
            .eq("id", group_id) \
            .eq("user_id", self.user_id) \
            .execute()

        return self.get_group(workspace_id, group_id)

    def delete_group(self, workspace_id: str, group_id: str):
        supabase.table("group_chats") \
            .delete() \
            .eq("id", group_id) \
            .eq("user_id", self.user_id) \
            .execute()

        # 也删除相关消息
        supabase.table("group_messages") \
            .delete() \
            .eq("group_id", group_id) \
            .eq("user_id", self.user_id) \
            .execute()

    # ========== Message Management ==========

    def get_messages(self, workspace_id: str, group_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Load message history for a group (最近 limit 条)."""
        result = supabase.table("group_messages") \
            .select("*") \
            .eq("user_id", self.user_id) \
            .eq("group_id", group_id) \
            .order("created_at", desc=False) \
            .limit(limit) \
            .execute()

        messages = []
        for row in result.data:
            msg = {
                "role": row.get("role", "user"),
                "content": row.get("content", ""),
                "timestamp": row.get("created_at", ""),
            }
            if row.get("agent_id"):
                msg["agent_id"] = row["agent_id"]
            if row.get("agent_name"):
                msg["agent_name"] = row["agent_name"]
                msg["name"] = row["agent_name"]

            # Map 'agent' role to 'assistant'
            if msg["role"] == "agent":
                msg["role"] = "assistant"

            # Merge extra fields
            extra = row.get("extra") or {}
            msg.update(extra)

            messages.append(msg)
        return messages

    def add_message(self, workspace_id: str, group_id: str, role: str,
                    content: str, agent_id: Optional[str] = None,
                    agent_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Add a message to group chat history."""
        # Normalize role
        actual_role = "assistant" if role in ("agent", "assistant") else role

        row = {
            "user_id": self.user_id,
            "group_id": group_id,
            "role": actual_role,
            "content": content,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "extra": kwargs if kwargs else {},
        }

        supabase.table("group_messages").insert(row).execute()

        message = {
            "role": actual_role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        if actual_role == "assistant":
            message["agent_id"] = agent_id
            message["agent_name"] = agent_name
            message["name"] = agent_name
        message.update(kwargs)
        return message

    def clear_messages(self, workspace_id: str, group_id: str):
        """Clear all messages for a group."""
        supabase.table("group_messages") \
            .delete() \
            .eq("group_id", group_id) \
            .eq("user_id", self.user_id) \
            .execute()
        print(f"[GroupManager] Cleared messages for {group_id}")
