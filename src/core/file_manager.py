"""
FileManager - 文件管理器 V2
核心职责：
1. Root Lock 安全 (防止路径逃逸)
2. Metadata Locking (基于 _metadata.json 的文件锁)
3. Change Request (Diff 审批流)
"""

import os
import json
import shutil
import difflib
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class ChangeRequest:
    """文件变更请求对象，用于 Diff 审批流"""
    file_path: str
    original_content: str
    new_content: str
    diff_lines: list[str] = field(default_factory=list)
    status: str = "pending"  # pending / approved / rejected
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    comment: str = ""

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "original_content": self.original_content,
            "new_content": self.new_content,
            "diff_lines": self.diff_lines,
            "status": self.status,
            "created_at": self.created_at,
            "comment": self.comment,
        }


@dataclass
class FileMetadata:
    """文件元数据"""
    locked: bool = False
    type: str = "doc"  # doc, resource, etc.


class FileManager:
    """
    文件管理器 V2 - 支持文件锁与灵活目录结构
    
    核心变更:
    1. 废弃基于目录名 (static/active) 的权限控制。
    2. 引入 _metadata.json 存储文件锁状态。
    3. 支持任意深度的文件夹结构。
    
    目录结构:
      data/{workspace}/
        shared/                 # 工作区共享（所有 Agent 可访问）
          _metadata.json        # 存储 Lock 状态
          任意文件夹/
        {agent}/                # Agent 私有
          _metadata.json        # 存储 Lock 状态
          archives/             # 日志归档
          knowledge_base/       # RAG 原始文件
          vector_store/         # 向量数据库
    """

    # 目录层级名称
    SHARED_DIR = "shared"
    ARCHIVES_DIR = "archives"
    KNOWLEDGE_DIR = "knowledge_base"
    VECTOR_DIR = "vector_store"
    CONTEXT_DIR = "context" # Legacy support

    METADATA_FILE = "_metadata.json"

    def __init__(self, data_root: str):
        """
        Args:
            data_root: data/ 目录的绝对路径，所有操作被锁定在此目录内
        """
        self.data_root = os.path.realpath(data_root)
        self.base_dir = self.data_root  # Alias for backward compatibility
        os.makedirs(self.data_root, exist_ok=True)

    def _resolve_and_validate(self, path: str) -> str:
        """Root Lock: 解析路径并确保在 data_root 内"""
        # 处理 Windows 路径分隔符
        path = path.replace("\\", "/")
        resolved = os.path.realpath(os.path.join(self.data_root, path))
        if not resolved.startswith(self.data_root):
            raise PermissionError(
                f"安全违规：路径 '{path}' 试图逃逸出数据根目录 '{self.data_root}'"
            )
        return resolved

    def _get_metadata_path(self, resolved_path: str) -> str:
        """
        获取当前文件所属的元数据文件路径
        规则: 
        1. shared/下的文件 -> data/workspace/shared/_metadata.json
        2. agent/下的文件 -> data/workspace/{agent}/_metadata.json
        """
        rel_path = os.path.relpath(resolved_path, self.data_root).replace("\\", "/")
        parts = rel_path.split("/")
        
        # Edge case: path is data root itself
        if not parts or parts == ['.']:
            return ""

        workspace = parts[0]
        if len(parts) < 2:
            return ""
            
        # Structure is data/{workspace}/...
        # So we look at parts[1] which is likely 'shared' or '{agent_id}'
        
        second_level = parts[1]
        
        # 1. Shared Area
        if second_level == self.SHARED_DIR:
             metadata_dir = os.path.join(self.data_root, workspace, self.SHARED_DIR)
             return os.path.join(metadata_dir, self.METADATA_FILE)
        
        # 2. Agent Private Area
        # Exclude system files if any (currently none at this level)
        if second_level not in [".git", "__pycache__"]:
             metadata_dir = os.path.join(self.data_root, workspace, second_level)
             return os.path.join(metadata_dir, self.METADATA_FILE)

        return ""

    def _load_metadata(self, metadata_path: str) -> dict:
        """读取元数据文件"""
        if not metadata_path or not os.path.exists(metadata_path):
            return {}
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                return json.load(f).get("files", {})
        except Exception:
            return {}

    def _save_metadata(self, metadata_path: str, data: dict) -> None:
        """保存元数据文件 (Merge Update)"""
        if not metadata_path:
            return
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        try:
            # Load existing to merge (optimistic concurrency)
            current = {}
            if os.path.exists(metadata_path):
                with open(metadata_path, "r", encoding="utf-8") as f:
                    full_data = json.load(f)
                    current = full_data.get("files", {})
            
            # Update
            current.update(data)
            
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump({"files": current}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving metadata: {e}")

    def get_file_info(self, path: str) -> FileMetadata:
        """获取文件元数据 (Lock Status)"""
        resolved = self._resolve_and_validate(path)
        metadata_path = self._get_metadata_path(resolved)
        
        files_map = self._load_metadata(metadata_path)
        
        # Key is relative path from the metadata file's directory
        if not metadata_path:
            return FileMetadata()

        meta_dir = os.path.dirname(metadata_path)
        try:
            rel_key = os.path.relpath(resolved, meta_dir).replace("\\", "/")
        except ValueError:
            return FileMetadata()

        info = files_map.get(rel_key, {})
        return FileMetadata(
            locked=info.get("locked", False),
            type=info.get("type", "doc")
        )

    def set_file_lock(self, path: str, locked: bool) -> None:
        """设置文件锁状态"""
        resolved = self._resolve_and_validate(path)
        metadata_path = self._get_metadata_path(resolved)
        
        if not metadata_path:
            # Cannot lock files outside of managed areas
            return

        meta_dir = os.path.dirname(metadata_path)
        rel_key = os.path.relpath(resolved, meta_dir).replace("\\", "/")
        
        self._save_metadata(metadata_path, {
            rel_key: {"locked": locked, "type": "resource" if locked else "doc"}
        })

    def _check_write_permission(self, resolved_path: str, force: bool = False) -> None:
        """检查写权限: 是否被锁定"""
        # 1. Archives 始终允许追加/写入 (日志用途)
        if f"/{self.ARCHIVES_DIR}/" in resolved_path.replace("\\", "/"):
             return

        # 2. Force Rewrite (例如审批通过后) 跳过检查
        if force:
            return

        # 3. Check Metadata Lock
        metadata_path = self._get_metadata_path(resolved_path)
        if not metadata_path:
            return

        files_map = self._load_metadata(metadata_path)
        meta_dir = os.path.dirname(metadata_path)
        try:
            rel_key = os.path.relpath(resolved_path, meta_dir).replace("\\", "/")
            info = files_map.get(rel_key, {})
            if info.get("locked", False):
                raise PermissionError(f"权限拒绝：文件已锁定 (只读资源): {os.path.basename(resolved_path)}")
        except ValueError:
            pass

    def read_file(self, path: str) -> str:
        """读取文件"""
        resolved = self._resolve_and_validate(path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"文件不存在: {path}")

        ext = os.path.splitext(resolved)[1].lower()
        if ext == ".json":
            with open(resolved, "r", encoding="utf-8") as f:
                data = json.load(f)
                return json.dumps(data, ensure_ascii=False, indent=2)
        else:
            with open(resolved, "r", encoding="utf-8") as f:
                return f.read()

    def create_directory(self, path: str) -> None:
        """创建文件夹 (支持递归)"""
        resolved = self._resolve_and_validate(path)
        os.makedirs(resolved, exist_ok=True)

    def write_file(self, path: str, content: str, force: bool = False) -> Optional[ChangeRequest]:
        """
        写入文件
        - 检查 Lock 状态
        - 如果是 Shared 区域且未 Lock -> 生成 ChangeRequest (除非 force=True)
        - 其他区域 -> 直接写入
        """
        resolved = self._resolve_and_validate(path)
        
        # 1. 权限检查 (Lock Check)
        self._check_write_permission(resolved, force)

        # 2. Shared 区域需审批 (Legacy Logic Refined)
        # 只有在 shared/ 下且不是 metadata 文件时才需要审批
        normalized = resolved.replace("\\", "/")
        is_shared = f"/{self.SHARED_DIR}/" in normalized
        is_metadata = os.path.basename(resolved) == self.METADATA_FILE
        
        if is_shared and not is_metadata and not force:
            original = ""
            if os.path.exists(resolved):
                with open(resolved, "r", encoding="utf-8") as f:
                    original = f.read()
            
            # Simple content check to avoid empty diffs
            if original == content:
                return None

            diff = list(difflib.unified_diff(
                original.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"原始: {path}",
                tofile=f"修改: {path}",
                lineterm=""
            ))

            return ChangeRequest(
                file_path=path,
                original_content=original,
                new_content=content,
                diff_lines=diff,
            )

        # 3. 直接写入
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
        return None

    def append_file(self, path: str, content: str) -> None:
        """追加内容到文件"""
        resolved = self._resolve_and_validate(path)
        # Append typically used for logs, bypassing strict lock check usually desireable,
        # but let's conform to standard permission check if file is locked explicitly.
        self._check_write_permission(resolved) 
        
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with open(resolved, "a", encoding="utf-8") as f:
            f.write(content)

    def apply_change(self, change_request: ChangeRequest) -> None:
        """应用已审批的变更 (Force Write)"""
        if change_request.status != "approved":
            raise ValueError("变更请求尚未审批，无法应用。")
        self.write_file(change_request.file_path, change_request.new_content, force=True)

    def list_directory(self, path: str = "") -> list[dict]:
        """列出目录 (包含 Lock Status)"""
        try:
            resolved = self._resolve_and_validate(path)
        except Exception:
            # If path validation fails (e.g. empty path on windows sometimes issues), try root
            resolved = self.data_root

        if not os.path.isdir(resolved):
            return []

        # Load metadata once for the directory context
        metadata_path = self._get_metadata_path(resolved) 
        files_map = self._load_metadata(metadata_path)
        meta_dir = os.path.dirname(metadata_path) if metadata_path else ""

        items = []
        for name in sorted(os.listdir(resolved)):
            # Hide system files
            if name == self.METADATA_FILE or name.startswith("."): 
                continue 
            
            full = os.path.join(resolved, name)
            rel = os.path.relpath(full, self.data_root).replace("\\", "/")
            
            # Check Lock Status
            is_locked = False
            if meta_dir:
                try:
                    rel_key = os.path.relpath(full, meta_dir).replace("\\", "/")
                    is_locked = files_map.get(rel_key, {}).get("locked", False)
                except:
                    pass

            items.append({
                "name": name,
                "path": rel,
                "is_dir": os.path.isdir(full),
                "size": os.path.getsize(full) if os.path.isfile(full) else None,
                "modified": datetime.fromtimestamp(os.path.getmtime(full)).isoformat() if os.path.exists(full) else None,
                "locked": is_locked
            })
        return items

    def move_file(self, src: str, dst: str) -> None:
        """移动/重命名文件"""
        resolved_src = self._resolve_and_validate(src)
        resolved_dst = self._resolve_and_validate(dst)
        
        # Check source lock
        self._check_write_permission(resolved_src) 
        
        if not os.path.exists(resolved_src):
             raise FileNotFoundError(f"源文件不存在: {src}")

        os.makedirs(os.path.dirname(resolved_dst), exist_ok=True)
        shutil.move(resolved_src, resolved_dst)

    def get_file_diff(self, old_content: str, new_content: str, old_label: str = "原始", new_label: str = "修改") -> list[str]:
        return list(difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=old_label,
            tofile=new_label,
            lineterm=""
        ))
    
    # --- Compatibility Helpers (V2) ---
    # These create the new structure automatically if accessed

    def ensure_workspace_shared_dirs(self, workspace: str) -> str:
        """确保工作区共享目录存在 (V2: 只有 shared 根目录)"""
        ws_path = self._resolve_and_validate(workspace)
        os.makedirs(os.path.join(ws_path, self.SHARED_DIR), exist_ok=True)
        return ws_path

    def ensure_agent_dirs(self, workspace: str, agent_id: str) -> str:
        """确保 Agent 目录结构存在"""
        # Ensure shared exists
        self.ensure_workspace_shared_dirs(workspace)
        
        # Ensure private dirs
        agent_path = os.path.join(workspace, agent_id)
        for sub in [self.ARCHIVES_DIR, self.KNOWLEDGE_DIR, self.VECTOR_DIR]:
            os.makedirs(self._resolve_and_validate(os.path.join(agent_path, sub)), exist_ok=True)
        return agent_path

    def get_agent_context(self, workspace: str, agent_id: str) -> dict[str, str]:
        """
        读取 Agent 的上下文 (V2: 兼容旧逻辑，但主要读取根目录)
        
        在 V2 中，Context 的概念弱化，Agent 应该直接访问文件系统的 'shared' 和 'private' 区域。
        为了保持 ModelAgent 调用兼容，我们简单扫描 Agent 私有目录下的所有一级文件。
        """
        context = {}
        
        def _read_dir_to_context(rel_dir_path: str):
            try:
                full_path = self._resolve_and_validate(os.path.join(workspace, rel_dir_path))
                if os.path.isdir(full_path):
                    for name in os.listdir(full_path):
                        if name.startswith(".") or name == self.METADATA_FILE: continue
                        f_path = os.path.join(full_path, name)
                        if os.path.isfile(f_path):
                            try:
                                with open(f_path, "r", encoding="utf-8") as f:
                                    context[name] = f.read()
                            except:
                                pass
            except:
                pass

        # Read Agent Private Root
        _read_dir_to_context(agent_id)
        
        # Also maybe read Shared Root? (Optional, might be too big)
        # _read_dir_to_context(self.SHARED_DIR)
        
        return context
