"""
PlaywrightTools - 通用浏览器自动化工具（Layer 1 核心工具）
基于 Playwright 持久化上下文，支持 Edge/Chrome/Chromium。
提供：open_browser, get_page_text, page_screenshot, scroll_page,
      check_login_status, wait_for_login, close_browser
"""

import os
import time
from datetime import datetime
from typing import Optional
from langchain_core.tools import tool

# ============================================================
# 全局浏览器实例管理
# ============================================================

_playwright_instance = None
_browser_context = None
_current_page = None

# Cookie / Profile 持久化目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROFILE_DIR = os.path.join(_PROJECT_ROOT, "data", ".browser_profiles", "default")


def _ensure_page(url: Optional[str] = None, browser: str = "msedge") -> "Page":
    """获取或启动浏览器页面（内部使用）"""
    global _playwright_instance, _browser_context, _current_page

    # 如果已有活跃页面且未关闭，直接返回
    if _current_page and not _current_page.is_closed():
        if url:
            _current_page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return _current_page

    # 启动 Playwright
    from playwright.sync_api import sync_playwright

    if not _playwright_instance:
        _playwright_instance = sync_playwright().start()

    # 确保 profile 目录存在
    os.makedirs(_PROFILE_DIR, exist_ok=True)

    # 启动持久化浏览器上下文
    launch_kwargs = {
        "user_data_dir": _PROFILE_DIR,
        "headless": False,
        "viewport": {"width": 1280, "height": 900},
        "args": ["--disable-blink-features=AutomationControlled"],
    }

    # 浏览器 channel 映射
    channel_map = {
        "msedge": "msedge",
        "edge": "msedge",
        "chrome": "chrome",
        "chromium": None,  # 默认 Playwright 内置 Chromium
    }
    channel = channel_map.get(browser.lower(), "msedge")
    if channel:
        launch_kwargs["channel"] = channel

    try:
        _browser_context = _playwright_instance.chromium.launch_persistent_context(**launch_kwargs)
    except Exception as e:
        # 如果指定的浏览器不可用，回退到内置 Chromium
        if channel:
            launch_kwargs.pop("channel", None)
            _browser_context = _playwright_instance.chromium.launch_persistent_context(**launch_kwargs)
        else:
            raise e

    # 获取或新建页面
    if _browser_context.pages:
        _current_page = _browser_context.pages[0]
    else:
        _current_page = _browser_context.new_page()

    # 导航到指定 URL
    if url:
        _current_page.goto(url, wait_until="domcontentloaded", timeout=30000)

    return _current_page


# ============================================================
# LangChain Tool 定义
# ============================================================

@tool
def open_browser(url: str, browser: str = "msedge") -> str:
    """打开浏览器并导航到指定 URL。首次调用会启动一个新的浏览器窗口，后续调用复用同一窗口。
    Cookie 和登录状态会自动持久化保存。
    
    Args:
        url: 要访问的网页地址
        browser: 浏览器类型，支持 "msedge"(默认), "chrome", "chromium"
    """
    try:
        page = _ensure_page(url, browser)
        title = page.title()
        return f"浏览器已打开: {url}\n页面标题: {title}"
    except Exception as e:
        return f"打开浏览器失败: {str(e)}"


@tool
def get_page_text(selector: str = "body") -> str:
    """获取当前浏览器页面的文本内容。可以指定 CSS 选择器只获取页面中某个区域的文本。
    
    Args:
        selector: CSS 选择器，默认 "body" 获取整个页面文本
    """
    global _current_page
    if not _current_page or _current_page.is_closed():
        return "错误: 浏览器未打开。请先调用 open_browser。"

    try:
        # 等待选择器出现
        _current_page.wait_for_selector(selector, timeout=10000)
        text = _current_page.inner_text(selector)
        
        # 限制返回长度，避免 token 爆炸
        if len(text) > 15000:
            text = text[:15000] + "\n\n...[内容已截断，共 {} 字符]".format(len(text))
        
        return text
    except Exception as e:
        return f"获取页面文本失败: {str(e)}"


@tool
def page_screenshot(filename: str = "") -> str:
    """截取当前浏览器页面的截图并保存。
    
    Args:
        filename: 保存的文件名（不含路径），默认自动以时间戳命名。截图保存在项目 data/ 目录下。
    """
    global _current_page
    if not _current_page or _current_page.is_closed():
        return "错误: 浏览器未打开。请先调用 open_browser。"

    try:
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"

        # 保存到 data/.screenshots/ 目录
        save_dir = os.path.join(_PROJECT_ROOT, "data", ".screenshots")
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)

        _current_page.screenshot(path=filepath, full_page=False)
        return f"截图已保存: {filepath}"
    except Exception as e:
        return f"截图失败: {str(e)}"


@tool
def scroll_page(direction: str = "down", pixels: int = 800) -> str:
    """滚动当前浏览器页面。
    
    Args:
        direction: 滚动方向，"down" 向下或 "up" 向上
        pixels: 滚动像素数，默认 800
    """
    global _current_page
    if not _current_page or _current_page.is_closed():
        return "错误: 浏览器未打开。请先调用 open_browser。"

    try:
        scroll_y = pixels if direction.lower() == "down" else -pixels
        _current_page.evaluate(f"window.scrollBy(0, {scroll_y})")
        # 等待一下让动态内容加载
        _current_page.wait_for_timeout(1000)
        
        # 获取当前滚动位置
        scroll_pos = _current_page.evaluate("window.scrollY")
        page_height = _current_page.evaluate("document.body.scrollHeight")
        return f"已向{('下' if direction == 'down' else '上')}滚动 {pixels}px。当前位置: {scroll_pos}/{page_height}"
    except Exception as e:
        return f"滚动失败: {str(e)}"


# ============================================================
# 登录检测 — 平台特定逻辑
# ============================================================

_LOGIN_DETECTORS = {
    "xiaohongshu": {
        # 已登录标志：用户头像/个人信息区域
        "logged_in_selectors": [
            ".user .name",           # 用户名
            ".sidebar .user-info",   # 侧边栏用户信息
            "a[href*='/user/profile']",  # 个人主页链接
        ],
        # 未登录标志：登录弹窗/二维码
        "login_selectors": [
            ".login-container",
            ".qrcode-img",
            "[class*='login']",
            "img[alt*='二维码']",
        ],
    },
}


@tool
def check_login_status(platform: str = "xiaohongshu") -> str:
    """检测当前页面是否已登录指定平台。
    
    Args:
        platform: 平台名称，目前支持 "xiaohongshu"
    """
    global _current_page
    if not _current_page or _current_page.is_closed():
        return "错误: 浏览器未打开。请先调用 open_browser。"

    detector = _LOGIN_DETECTORS.get(platform)
    if not detector:
        return f"不支持的平台: {platform}。目前支持: {', '.join(_LOGIN_DETECTORS.keys())}"

    try:
        # 先检查是否有明确的登录弹窗
        for sel in detector["login_selectors"]:
            try:
                el = _current_page.query_selector(sel)
                if el and el.is_visible():
                    return f"未登录: 检测到登录弹窗/二维码。请在浏览器中完成扫码登录。"
            except:
                continue

        # 检查是否有已登录标志
        for sel in detector["logged_in_selectors"]:
            try:
                el = _current_page.query_selector(sel)
                if el:
                    return f"已登录: 检测到用户信息元素。"
            except:
                continue

        return "登录状态不确定: 未检测到明确的登录/未登录标志。页面可能仍在加载中。"
    except Exception as e:
        return f"检测登录状态失败: {str(e)}"


@tool
def wait_for_login(timeout: int = 120) -> str:
    """等待用户在浏览器中完成扫码登录。会持续轮询页面状态，直到检测到登录成功或超时。
    
    Args:
        timeout: 最长等待时间（秒），默认 120 秒
    """
    global _current_page
    if not _current_page or _current_page.is_closed():
        return "错误: 浏览器未打开。请先调用 open_browser。"

    try:
        start_time = time.time()
        poll_interval = 3  # 每 3 秒检查一次

        while time.time() - start_time < timeout:
            # 检查所有平台的已登录标志
            for platform, detector in _LOGIN_DETECTORS.items():
                for sel in detector["logged_in_selectors"]:
                    try:
                        el = _current_page.query_selector(sel)
                        if el:
                            elapsed = int(time.time() - start_time)
                            return f"登录成功！(等待了 {elapsed} 秒)"
                    except:
                        continue

            # 检查页面是否发生了导航（登录成功后通常会跳转）
            time.sleep(poll_interval)

        return f"等待超时 ({timeout} 秒)。请确认是否已完成登录，或再次调用此工具。"
    except Exception as e:
        return f"等待登录失败: {str(e)}"


@tool
def close_browser() -> str:
    """关闭浏览器并释放所有资源。关闭后需重新调用 open_browser 才能继续操作。"""
    global _playwright_instance, _browser_context, _current_page

    try:
        if _browser_context:
            _browser_context.close()
        if _playwright_instance:
            _playwright_instance.stop()
    except:
        pass
    finally:
        _playwright_instance = None
        _browser_context = None
        _current_page = None

    return "浏览器已关闭。"


# ============================================================
# 导出
# ============================================================

PLAYWRIGHT_TOOLS = [
    open_browser,
    get_page_text,
    page_screenshot,
    scroll_page,
    check_login_status,
    wait_for_login,
    close_browser,
]
