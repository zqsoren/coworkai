"""
WorkspaceManager - 工作区管理器
职责：工作区的创建、列举、删除，以及启动时确保默认工作区存在。
"""

import os
import json
from datetime import datetime
from typing import Optional

from .file_manager import FileManager


class WorkspaceManager:
    """管理所有工作区（Workspace）"""

    DEFAULT_WORKSPACE = "workspace_default"
    DEFAULT_AGENT = "agent_assistant"

    def __init__(self, file_manager: FileManager):
        self.fm = file_manager

    def ensure_default_workspace(self) -> None:
        """启动时确保默认工作区和默认 Agent 存在"""
        self.fm.ensure_agent_dirs(self.DEFAULT_WORKSPACE, self.DEFAULT_AGENT)

        # 确保默认 Agent 有 config.json
        config_path = os.path.join(
            self.DEFAULT_WORKSPACE, self.DEFAULT_AGENT, "config.json"
        )
        resolved = self.fm._resolve_and_validate(config_path)
        if not os.path.exists(resolved):
            default_config = {
                "name": "通用助手",
                "system_prompt": "你是一个通用 AI 助手，擅长文件管理、信息检索和内容生成。请用中文回复用户。",
                "model_tier": "tier1",
                "tools": [
                    "read_file", "write_file", "list_directory",
                    "google_search", "fetch_url_content", "python_repl"
                ],
                "skills": [],
                "tags": ["通用", "默认"],
                "created_at": datetime.now().isoformat(),
            }
            with open(resolved, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)

    def create_workspace(self, name: str) -> str:
        """
        创建新工作区
        返回工作区路径（相对于 data_root）
        """
        workspace_id = f"workspace_{name.lower().replace(' ', '_')}"
        ws_path = self.fm._resolve_and_validate(workspace_id)
        if os.path.exists(ws_path):
            raise FileExistsError(f"工作区已存在: {workspace_id}")
        os.makedirs(ws_path, exist_ok=True)
        # 创建工作区元数据
        meta = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "description": "",
        }
        meta_path = os.path.join(ws_path, "_workspace_meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        return workspace_id

    def rename_workspace(self, workspace_id: str, new_name: str) -> None:
        """
        重命名工作区 (仅修改显示名称)
        """
        ws_path = self.fm._resolve_and_validate(workspace_id)
        if not os.path.isdir(ws_path):
            raise FileNotFoundError(f"工作区不存在: {workspace_id}")
            
        meta_path = os.path.join(ws_path, "_workspace_meta.json")
        meta = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except: pass
            
        meta["name"] = new_name
        # Keep other metadata
        
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def list_workspaces(self) -> list[dict]:
        """列出所有工作区"""
        workspaces = []
        for item in os.listdir(self.fm.data_root):
            full = os.path.join(self.fm.data_root, item)
            if os.path.isdir(full) and item.startswith("workspace_"):
                meta = {"id": item, "name": item}
                meta_file = os.path.join(full, "_workspace_meta.json")
                if os.path.exists(meta_file):
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            meta.update(json.load(f))
                    except (json.JSONDecodeError, IOError):
                        pass
                # 统计 Agent 数量
                agents = [
                    d for d in os.listdir(full)
                    if os.path.isdir(os.path.join(full, d)) and d.startswith("agent_")
                ]
                meta["agent_count"] = len(agents)
                workspaces.append(meta)
        return workspaces

    def get_workspace_agents(self, workspace_id: str) -> list[dict]:
        """获取工作区内所有 Agent"""
        ws_path = self.fm._resolve_and_validate(workspace_id)
        if not os.path.isdir(ws_path):
            raise FileNotFoundError(f"工作区不存在: {workspace_id}")

        agents = []
        for item in sorted(os.listdir(ws_path)):
            agent_dir = os.path.join(ws_path, item)
            if os.path.isdir(agent_dir) and item.startswith("agent_"):
                agent_info = {"id": item, "name": item, "workspace": workspace_id}
                config_file = os.path.join(agent_dir, "config.json")
                if os.path.exists(config_file):
                    try:
                        with open(config_file, "r", encoding="utf-8") as f:
                            agent_info.update(json.load(f))
                    except (json.JSONDecodeError, IOError):
                        pass
                agents.append(agent_info)
        return agents

    def delete_workspace(self, workspace_id: str) -> None:
        """删除工作区（危险操作）"""
        if workspace_id == self.DEFAULT_WORKSPACE:
            raise PermissionError("不允许删除默认工作区。")
        ws_path = self.fm._resolve_and_validate(workspace_id)
        if os.path.isdir(ws_path):
            import shutil
            shutil.rmtree(ws_path)
