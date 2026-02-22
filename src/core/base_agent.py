"""
BaseAgent - Agent 基类
职责：定义 Agent 的基础能力：加载上下文、保存上下文、请求文件变更。
所有具体 Agent 继承此类。
"""

import json
import os
from datetime import datetime
from typing import Optional

from .file_manager import FileManager, ChangeRequest


class BaseAgent:
    """
    Agent 基类
    
    每个 Agent 对应一个目录：
    workspace_xxx/agent_yyy/
    ├── config.json          # Agent 配置
    ├── context/
    │   ├── static/          # 静态资源库 (READ-ONLY)
    │   ├── active/          # 动态项目文档 (READ-WRITE w/ Diff)
    │   └── archives/        # 归档与交付 (APPEND)
    ├── knowledge_base/      # RAG 知识库
    └── vector_store/        # 向量数据库
    """

    def __init__(self, agent_id: str, workspace_id: str,
                 file_manager: FileManager, config: Optional[dict] = None):
        self.agent_id = agent_id
        self.workspace_id = workspace_id
        self.fm = file_manager
        self.base_path = os.path.join(workspace_id, agent_id)

        # 加载 Agent 配置
        if config:
            self.config = config
        else:
            self.config = self._load_config()

        # 从配置中提取属性
        self.name = self.config.get("name", agent_id)
        self.system_prompt = self.config.get("system_prompt", "你是一个 AI 助手。")
        self.model_tier = self.config.get("model_tier", "tier1")
        self.tool_names = self.config.get("tools", [])
        self.skill_names = self.config.get("skills", [])
        self.tags = self.config.get("tags", [])

    def _load_config(self) -> dict:
        """从 config.json 加载 Agent 配置"""
        config_path = os.path.join(self.base_path, "config.json")
        try:
            content = self.fm.read_file(config_path)
            return json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "name": self.agent_id,
                "system_prompt": "你是一个 AI 助手。",
                "model_tier": "tier1",
                "tools": [],
                "skills": [],
                "tags": [],
            }

    def load_context(self) -> str:
        """
        读取 active/ 目录下所有文件，拼接为上下文字符串。
        用于注入到 LLM 的 system prompt 中。
        """
        context_files = self.fm.get_agent_context(self.workspace_id, self.agent_id)
        if not context_files:
            return ""

        parts = ["## 当前项目上下文\n"]
        for filename, content in context_files.items():
            parts.append(f"### 📄 {filename}\n```\n{content}\n```\n")
        return "\n".join(parts)

    def save_context(self, session_data: dict) -> None:
        """
        保存会话上下文到 context/active/session_memory.json
        """
        memory_path = os.path.join(
            self.base_path, "context", "active", "session_memory.json"
        )
        # 强制写入（会话记忆不需要审批）
        self.fm.write_file(
            memory_path,
            json.dumps(session_data, ensure_ascii=False, indent=2),
            force=True
        )

    def request_file_change(self, relative_path: str,
                            content: str) -> Optional[ChangeRequest]:
        """
        请求修改文件。
        - 对于 context/active/ 下的文件，返回 ChangeRequest 待审批
        - 对于 context/archives/ 下的文件，直接写入
        """
        full_path = os.path.join(self.base_path, relative_path)
        return self.fm.write_file(full_path, content)

    def save_output(self, filename: str, content: str) -> str:
        """
        保存输出到 context/archives/ 目录（无需审批）
        返回文件路径。
        """
        archives_path = os.path.join(
            self.base_path, "context", "archives", filename
        )
        self.fm.write_file(archives_path, content)
        return archives_path

    def get_static_files(self) -> list[dict]:
        """列出 context/static/ 目录下的文件"""
        static_path = os.path.join(self.base_path, "context", "static")
        try:
            return self.fm.list_directory(static_path)
        except (NotADirectoryError, FileNotFoundError):
            return []

    def get_active_files(self) -> list[dict]:
        """列出 context/active/ 目录下的文件"""
        active_path = os.path.join(self.base_path, "context", "active")
        try:
            return self.fm.list_directory(active_path)
        except (NotADirectoryError, FileNotFoundError):
            return []

    def get_archives_files(self) -> list[dict]:
        """列出 context/archives/ 目录下的文件"""
        archives_path = os.path.join(self.base_path, "context", "archives")
        try:
            return self.fm.list_directory(archives_path)
        except (NotADirectoryError, FileNotFoundError):
            return []

    def get_full_system_prompt(self) -> str:
        """构建完整的 system prompt（基础人设 + 项目上下文）"""
        context = self.load_context()
        prompt_parts = [self.system_prompt]

        if context:
            prompt_parts.append("\n---\n")
            prompt_parts.append(context)

        prompt_parts.append(
            "\n---\n## 重要规则\n"
            "1. 修改 context/active/ 目录的文件时，你必须使用 write_file 工具，系统会生成变更审批请求。\n"
            "2. 你不能修改 context/static/ 目录的文件，只能读取。\n"
            "3. 生成的输出物请保存到 context/archives/ 目录。\n"
            "4. 请用中文回复用户。\n"
        )

        return "\n".join(prompt_parts)
