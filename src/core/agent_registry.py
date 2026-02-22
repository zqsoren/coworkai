"""
AgentRegistry - Agent 注册与发现
职责：管理 agents_registry.json，提供 Agent 的注册/查询/更新/删除。
"""

import os
import json
from datetime import datetime
from typing import Optional


class AgentRegistry:
    """全局 Agent 注册表管理"""

    def __init__(self, registry_path: str):
        """
        Args:
            registry_path: agents_registry.json 的绝对路径
        """
        self.registry_path = registry_path
        self._ensure_registry()

    def _ensure_registry(self) -> None:
        """确保注册表文件存在"""
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        if not os.path.exists(self.registry_path):
            self._save({"version": "1.0", "agents": {}})

    def _load(self) -> dict:
        """加载注册表"""
        with open(self.registry_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: dict) -> None:
        """保存注册表"""
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def register_agent(self, agent_id: str, config: dict) -> None:
        """注册新 Agent"""
        data = self._load()
        if agent_id in data["agents"]:
            raise ValueError(f"Agent 已存在: {agent_id}")
        config.setdefault("created_at", datetime.now().isoformat())
        data["agents"][agent_id] = config
        self._save(data)

    def update_agent(self, agent_id: str, updates: dict) -> None:
        """更新 Agent 配置"""
        data = self._load()
        if agent_id not in data["agents"]:
            raise KeyError(f"Agent 不存在: {agent_id}")
        data["agents"][agent_id].update(updates)
        data["agents"][agent_id]["updated_at"] = datetime.now().isoformat()
        self._save(data)

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
                "tools": ["create_new_agent", "list_available_agents", "list_all_files_recursive", "read_file", "write_file", "google_search"],
                "skills": [],
                "tags": ["system", "meta"],
                "persona_mode": "efficient"
            }
        data = self._load()
        return data["agents"].get(agent_id)

    def list_agents(self, workspace: Optional[str] = None,
                    tag: Optional[str] = None) -> list[dict]:
        """
        列出所有 Agent，可按 workspace 或 tag 筛选
        """
        data = self._load()
        agents = []
        for aid, config in data["agents"].items():
            if workspace and config.get("workspace") != workspace:
                continue
            if tag and tag not in config.get("tags", []):
                continue
            agents.append({"id": aid, **config})
        return agents

    def remove_agent(self, agent_id: str) -> None:
        """从注册表中移除 Agent"""
        data = self._load()
        if agent_id not in data["agents"]:
            raise KeyError(f"Agent 不存在: {agent_id}")
        del data["agents"][agent_id]
        self._save(data)

    def get_all_tags(self) -> list[str]:
        """获取所有已使用的标签"""
        data = self._load()
        tags = set()
        for config in data["agents"].values():
            tags.update(config.get("tags", []))
        return sorted(tags)
