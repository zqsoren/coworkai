"""
AgentRegistry - Agent 注册与发现（Supabase 版）
职责：管理 Supabase agents 表，提供 Agent 的注册/查询/更新/删除。
"""

from datetime import datetime
from typing import Optional

from backend.supabase_client import supabase


class AgentRegistry:
    """全局 Agent 注册表管理（Supabase 版）"""

    def __init__(self, user_id: str):
        """
        Args:
            user_id: 当前用户 ID
        """
        self.user_id = user_id

    def register_agent(self, agent_id: str, config: dict) -> None:
        """注册新 Agent"""
        # 检查是否已存在
        existing = supabase.table("agents") \
            .select("id") \
            .eq("id", agent_id) \
            .eq("user_id", self.user_id) \
            .execute()
        if existing.data:
            raise ValueError(f"Agent 已存在: {agent_id}")

        config.setdefault("created_at", datetime.now().isoformat())

        row = {
            "id": agent_id,
            "user_id": self.user_id,
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

    def update_agent(self, agent_id: str, updates: dict) -> None:
        """更新 Agent 配置"""
        # 检查存在
        existing = supabase.table("agents") \
            .select("id") \
            .eq("id", agent_id) \
            .eq("user_id", self.user_id) \
            .execute()
        if not existing.data:
            raise KeyError(f"Agent 不存在: {agent_id}")

        # 构建更新字段
        allowed_fields = [
            "name", "system_prompt", "provider_id", "model_name",
            "persona_mode", "tools", "skills", "mcp_servers", "tags",
            "knowledge_base", "workspace"
        ]
        row_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        row_updates["updated_at"] = datetime.now().isoformat()

        supabase.table("agents") \
            .update(row_updates) \
            .eq("id", agent_id) \
            .eq("user_id", self.user_id) \
            .execute()

    def get_agent(self, agent_id: str) -> Optional[dict]:
        """获取 Agent 配置"""
        if agent_id == "meta_agent":
            return {
                "id": "meta_agent",
                "name": "元 Agent",
                "workspace": "workspace_default",
                "system_prompt": "你是系统的元 Agent (Meta Agent)，负责监督和管理整个工作区。\n你可以使用工具协助用户分析现状、搜集信息，或通过 create_new_agent 工具帮用户规划和创建新的 Agent。",
                "provider_id": "builtin_glm4air_free",
                "model_name": "z-ai/glm-4.5-air:free",
                "tools": ["create_new_agent", "list_available_agents", "list_all_files_recursive", "read_file", "write_file"],
                "skills": [],
                "tags": ["system", "meta"],
                "persona_mode": "efficient"
            }

        result = supabase.table("agents") \
            .select("*") \
            .eq("id", agent_id) \
            .eq("user_id", self.user_id) \
            .execute()

        if not result.data:
            return None

        row = result.data[0]
        # 返回与旧格式兼容的 dict
        return self._row_to_config(row)

    def list_agents(self, workspace: Optional[str] = None,
                    tag: Optional[str] = None) -> list[dict]:
        """列出所有 Agent，可按 workspace 或 tag 筛选"""
        query = supabase.table("agents") \
            .select("*") \
            .eq("user_id", self.user_id)

        if workspace:
            query = query.eq("workspace", workspace)

        result = query.execute()

        agents = []
        for row in result.data:
            config = self._row_to_config(row)
            if tag and tag not in config.get("tags", []):
                continue
            agents.append({"id": row["id"], **config})
        return agents

    def remove_agent(self, agent_id: str) -> None:
        """从注册表中移除 Agent"""
        existing = supabase.table("agents") \
            .select("id") \
            .eq("id", agent_id) \
            .eq("user_id", self.user_id) \
            .execute()
        if not existing.data:
            raise KeyError(f"Agent 不存在: {agent_id}")

        supabase.table("agents") \
            .delete() \
            .eq("id", agent_id) \
            .eq("user_id", self.user_id) \
            .execute()

    def get_all_tags(self) -> list[str]:
        """获取所有已使用的标签"""
        result = supabase.table("agents") \
            .select("tags") \
            .eq("user_id", self.user_id) \
            .execute()

        tags = set()
        for row in result.data:
            tags.update(row.get("tags") or [])
        return sorted(tags)

    @staticmethod
    def _row_to_config(row: dict) -> dict:
        """将数据库行转换为旧格式的配置 dict"""
        config = {
            "name": row.get("name", ""),
            "system_prompt": row.get("system_prompt", ""),
            "provider_id": row.get("provider_id"),
            "model_name": row.get("model_name"),
            "persona_mode": row.get("persona_mode", "efficient"),
            "tools": row.get("tools") or [],
            "skills": row.get("skills") or [],
            "mcp_servers": row.get("mcp_servers") or [],
            "tags": row.get("tags") or [],
            "knowledge_base": row.get("knowledge_base") or [],
            "workspace": row.get("workspace"),
        }
        if row.get("created_at"):
            config["created_at"] = row["created_at"]
        if row.get("updated_at"):
            config["updated_at"] = row["updated_at"]
        return config
