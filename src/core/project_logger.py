"""
ProjectLogger - Project Flight Recorder
自动记录对话、工具调用、文件修改到 context/archives/Project_Activity_Log.md
支持 2MB 自动轮转。
"""

import os
import shutil
from datetime import datetime
from typing import Optional


class ProjectLogger:
    """
    Project Flight Recorder — 自动追加日志到 archives/

    日志类型:
    - 🗣️ Interaction: 用户-AI 对话
    - 🛠️ Tool Call: 工具调用
    - 📝 File Change: 文件修改 (Diff)
    """

    LOG_FILE = "Project_Activity_Log.md"
    MAX_SIZE = 2 * 1024 * 1024  # 2MB

    def __init__(self, data_root: str, workspace: str, agent_id: str):
        self.data_root = data_root
        self.workspace = workspace
        self.agent_id = agent_id
        self.log_dir = os.path.join(
            data_root, workspace, agent_id, "context", "archives"
        )
        self.log_path = os.path.join(self.log_dir, self.LOG_FILE)
        os.makedirs(self.log_dir, exist_ok=True)

        # 初始化日志文件
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w", encoding="utf-8") as f:
                f.write(f"# Project Activity Log\n\n")
                f.write(f"> Agent: {agent_id} | Workspace: {workspace}\n")
                f.write(f"> Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")

    def log_interaction(self, user_msg: str, ai_msg: str) -> None:
        """记录用户-AI对话"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 截断过长消息
        user_short = user_msg[:500] + "..." if len(user_msg) > 500 else user_msg
        ai_short = ai_msg[:500] + "..." if len(ai_msg) > 500 else ai_msg

        entry = (
            f"### 🗣️ [{ts}] Interaction\n"
            f"**User**: \"{user_short}\"\n"
            f"**AI**: \"{ai_short}\"\n\n"
        )
        self._append(entry)

    def log_tool_call(self, tool_name: str, args: dict, status: str = "Success") -> None:
        """记录工具调用"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        import json
        args_str = json.dumps(args, ensure_ascii=False)
        if len(args_str) > 300:
            args_str = args_str[:300] + "..."

        entry = (
            f"### 🛠️ [{ts}] Tool Call\n"
            f"**Tool**: `{tool_name}`\n"
            f"**Args**: `{args_str}`\n"
            f"**Status**: {status}\n\n"
        )
        self._append(entry)

    def log_file_change(self, file_path: str, diff: str) -> None:
        """记录文件变更 (Diff)"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        diff_short = diff[:1000] + "\n..." if len(diff) > 1000 else diff

        entry = (
            f"### 📝 [{ts}] File Change\n"
            f"**File**: `{file_path}`\n"
            f"**Change**:\n```diff\n{diff_short}\n```\n\n"
        )
        self._append(entry)

    def _append(self, content: str) -> None:
        """追加内容，并检查轮转"""
        self._check_rotation()
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass  # 日志失败不应中断主流程

    def _check_rotation(self) -> None:
        """检查文件大小，超过 2MB 自动轮转"""
        if not os.path.exists(self.log_path):
            return

        try:
            size = os.path.getsize(self.log_path)
            if size > self.MAX_SIZE:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_name = f"Project_Activity_Log_ARCHIVE_{ts}.md"
                archive_path = os.path.join(self.log_dir, archive_name)
                shutil.move(self.log_path, archive_path)

                # 创建新的空日志文件
                with open(self.log_path, "w", encoding="utf-8") as f:
                    f.write(f"# Project Activity Log (Continued)\n\n")
                    f.write(f"> Rotated from: {archive_name}\n")
                    f.write(f"> Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("---\n\n")
        except Exception:
            pass  # 轮转失败不应中断主流程
