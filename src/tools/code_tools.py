"""
CodeTools - 代码执行工具（Layer 1 核心工具）
提供 Python REPL 和受限 Shell 命令执行能力。
"""

import io
import sys
import subprocess
from contextlib import redirect_stdout, redirect_stderr
from langchain_core.tools import tool


@tool
def python_repl(code: str) -> str:
    """在本地沙箱中执行 Python 代码。适用于数据分析、计算、画图等任务。
    
    Args:
        code: 要执行的 Python 代码
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec_globals = {"__builtins__": __builtins__}
            exec(code, exec_globals)

        stdout = stdout_capture.getvalue()
        stderr = stderr_capture.getvalue()

        result_parts = []
        if stdout:
            result_parts.append(f"输出:\n{stdout}")
        if stderr:
            result_parts.append(f"警告:\n{stderr}")
        if not result_parts:
            result_parts.append("代码执行成功，无输出。")

        return "\n".join(result_parts)
    except Exception as e:
        return f"执行错误: {type(e).__name__}: {str(e)}"


# 允许的 Shell 命令白名单
ALLOWED_COMMANDS = {
    "tree", "dir", "ls", "echo", "type", "cat", "find",
    "where", "whoami", "hostname", "date", "time", "ping",
}


@tool
def shell_command(cmd: str) -> str:
    """执行系统 Shell 命令。仅允许安全的只读命令（如 tree, dir, type）。
    
    Args:
        cmd: 要执行的命令
    """
    # 安全检查：提取命令名
    parts = cmd.strip().split()
    if not parts:
        return "错误: 命令为空。"

    cmd_name = parts[0].lower()
    if cmd_name not in ALLOWED_COMMANDS:
        return (
            f"安全拒绝: 命令 '{cmd_name}' 不在白名单中。\n"
            f"允许的命令: {', '.join(sorted(ALLOWED_COMMANDS))}"
        )

    # 防止管道和重定向注入
    dangerous_chars = ["|", "&", ";", ">", "<", "`", "$", "(", ")"]
    if any(c in cmd for c in dangerous_chars):
        return "安全拒绝: 命令包含危险字符（管道、重定向等）。"

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=".",
        )
        output = result.stdout
        if result.stderr:
            output += f"\n错误输出:\n{result.stderr}"
        if not output.strip():
            output = "命令执行成功，无输出。"
        # 限制输出长度
        if len(output) > 5000:
            output = output[:5000] + "\n...[输出已截断]"
        return output
    except subprocess.TimeoutExpired:
        return "错误: 命令执行超时（30 秒限制）。"
    except Exception as e:
        return f"执行错误: {str(e)}"


CODE_TOOLS = [python_repl, shell_command]
