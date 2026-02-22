"""
FileSystemTools - 文件系统工具（Layer 1 核心工具）
将 FileManager 的方法包装为 LangChain Tool，供 Agent 调用。
"""

import json
from langchain_core.tools import tool

# FileManager 实例将在运行时注入
_file_manager = None


def init_file_tools(file_manager):
    """初始化文件工具，注入 FileManager 实例"""
    global _file_manager
    _file_manager = file_manager


@tool
def read_file(path: str) -> str:
    """读取文件内容。支持 .md, .txt, .json, .csv 等格式。
    
    Args:
        path: 文件的相对路径（相对于 data/ 目录）
    """
    try:
        return _file_manager.read_file(path)
    except (FileNotFoundError, PermissionError) as e:
        return f"错误: {str(e)}"


@tool
def write_file(path: str, content: str) -> str:
    """写入文件。如果文件在 active/ 目录，会生成变更审批请求。
    
    Args:
        path: 文件的相对路径（相对于 data/ 目录）
        content: 要写入的内容
    """
    try:
        result = _file_manager.write_file(path, content)
        if result is not None:
            # 返回 ChangeRequest 的 JSON，UI 层会渲染 Diff
            return json.dumps({
                "type": "change_request",
                "file_path": result.file_path,
                "original_content": result.original_content,
                "new_content": result.new_content,
                "diff": result.diff_lines,
                "status": result.status,
            }, ensure_ascii=False)
        return f"文件已写入: {path}"
    except PermissionError as e:
        return f"权限拒绝: {str(e)}"


@tool
def list_directory(path: str = "") -> str:
    """列出目录中的文件和子目录。
    
    Args:
        path: 目录的相对路径（相对于 data/ 目录），空字符串表示根目录
    """
    try:
        items = _file_manager.list_directory(path)
        if not items:
            return "目录为空。"
        lines = []
        for item in items:
            icon = "📁" if item["is_dir"] else "📄"
            size = f" ({item['size']} bytes)" if item.get("size") else ""
            lines.append(f"{icon} {item['name']}{size}")
        return "\n".join(lines)
    except (NotADirectoryError, FileNotFoundError, PermissionError) as e:
        return f"错误: {str(e)}"


@tool
def move_file(src: str, dst: str) -> str:
    """移动或重命名文件。常用于归档操作。
    
    Args:
        src: 源文件的相对路径
        dst: 目标路径
    """
    try:
        _file_manager.move_file(src, dst)
        return f"文件已移动: {src} -> {dst}"
    except (FileNotFoundError, PermissionError) as e:
        return f"错误: {str(e)}"


def create_agent_file_tools(base_path: str, file_manager) -> list:
    """创建特定于 Agent 的文件工具（上下文感知）
    
    Args:
        base_path: Agent 的根目录 (e.g. "workspace_1/agent_coder")
        file_manager: FileManager 实例
    """
    import os
    from langchain_core.tools import StructuredTool

    # 提取 workspace路径（用于 shared 目录访问）
    workspace_path = os.path.dirname(base_path)  # workspace_1

    def _resolve(path: str) -> str:
        """
        路径解析逻辑：
        - static/ -> workspace/shared/static/  (工作区共享)
        - active/ -> workspace/shared/active/  (工作区共享)
        - archives/ -> workspace/agent/archives/ (Agent 私有)
        - 其他 -> workspace/agent/{path}
        """
        if os.path.isabs(path):
            return path  # 绝对路径保持不变
        
        # 🆕 重定向shared目录
        if path.startswith("static/"):
            return os.path.join(workspace_path, "shared", path)
        elif path.startswith("active/"):
            return os.path.join(workspace_path, "shared", path)
        # archives保持Agent私有
        elif path.startswith("archives/"):
            return os.path.join(base_path, path)
        # 默认: Agent私有路径
        else:
            return os.path.join(base_path, path)

    def read_file_wrapper(path: str) -> str:
        """读取文件内容。支持 .md, .txt, .json, .csv 等格式。"""
        full_path = _resolve(path)
        try:
            return file_manager.read_file(full_path)
        except (FileNotFoundError, PermissionError) as e:
            return f"错误: {str(e)}"

    def write_file_wrapper(path: str, content: str) -> str:
        """写入文件。如果文件在 active/ 目录，会生成变更审批请求。"""
        full_path = _resolve(path)
        try:
            result = file_manager.write_file(full_path, content)
            if result is not None:
                return json.dumps({
                    "type": "change_request",
                    "file_path": result.file_path,
                    "original_content": result.original_content,
                    "new_content": result.new_content,
                    "diff": result.diff_lines,
                    "status": result.status,
                }, ensure_ascii=False)
            return f"文件已写入: {path}"
        except PermissionError as e:
            return f"权限拒绝: {str(e)}"

    def list_directory_wrapper(path: str = "") -> str:
        """列出目录内容。"""
        full_path = _resolve(path)
        try:
            items = file_manager.list_directory(full_path)
            if not items:
                return "目录为空。"
            lines = []
            for item in items:
                icon = "📁" if item["is_dir"] else "📄"
                size = f" ({item['size']} bytes)" if item.get("size") else ""
                lines.append(f"{icon} {item['name']}{size}")
            return "\n".join(lines)
        except (NotADirectoryError, FileNotFoundError, PermissionError) as e:
            return f"错误: {str(e)}"
            
    # Move File Wrapper? (Optionally)
    
    tools = [
        StructuredTool.from_function(
            func=read_file_wrapper,
            name="read_file",
            description="读取文件内容。路径说明: static/ 和 active/ 为工作区共享，archives/ 为Agent私有。"
        ),
        StructuredTool.from_function(
            func=write_file_wrapper,
            name="write_file",
            description="写入文件。路径说明: static/ 只读，active/ 可写(需审批)，archives/ 为Agent私有追加。"
        ),
        StructuredTool.from_function(
            func=list_directory_wrapper,
            name="list_directory",
            description="列出目录文件。路径说明: static/, active/ 为工作区共享目录。"
        ),
    ]
    return tools


@tool
def get_file_diff(old_text: str, new_text: str) -> str:
    """对比两段文本的差异，生成 unified diff 格式。
    
    Args:
        old_text: 原始文本
        new_text: 修改后的文本
    """
    diff = _file_manager.get_file_diff(old_text, new_text)
    if not diff:
        return "两段文本完全相同，无差异。"
    return "\n".join(diff)


# 导出所有工具
FILE_TOOLS = [read_file, write_file, list_directory, move_file, get_file_diff]
