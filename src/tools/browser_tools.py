"""
BrowserPrimitives - 浏览器原语工具（Layer 1 核心工具）
提供时间获取、截图等基础能力。
Playwright CDP 连接为可选功能。
"""

from datetime import datetime
from langchain_core.tools import tool


@tool
def get_current_time() -> str:
    """获取当前系统时间，用于写日志或判断日程。"""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S (%A)")


@tool
def take_screenshot() -> str:
    """截取当前屏幕，保存到临时目录并返回文件路径。"""
    try:
        from PIL import ImageGrab
        import tempfile
        import os

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(tempfile.gettempdir(), filename)

        img = ImageGrab.grab()
        img.save(filepath)
        return f"截图已保存: {filepath}"
    except ImportError:
        return "错误: Pillow 库未安装。请运行: pip install Pillow"
    except Exception as e:
        return f"截图失败: {str(e)}"


BROWSER_TOOLS = [get_current_time, take_screenshot]
