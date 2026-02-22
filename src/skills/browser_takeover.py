"""
Browser Takeover Skill（Layer 2 标准技能）
通过 CDP 连接本地浏览器 (9222)，执行自动化操作。
支持动作：goto, click, type, press, screenshot, get_content
"""

import os
import time
from typing import Optional, List, Dict, Any

SKILL_NAME = "browser_takeover"
SKILL_DESCRIPTION = "浏览器接管：连接本地 Chrome (9222) 并执行自动化动作序列 (goto, click, type, screenshot 等)。"

# 全局 Playwright 实例（保持连接）
_playwright = None
_browser = None
_page = None

def _get_page(cdp_url: str = "http://localhost:9222"):
    """获取或初始化 Playwright 页面连接"""
    global _playwright, _browser, _page
    
    # 如果连接已断开，重置
    if _page and _page.is_closed():
        _page = None
        _browser = None
        
    if _page:
        return _page

    from playwright.sync_api import sync_playwright
    
    if not _playwright:
        _playwright = sync_playwright().start()
        
    try:
        # 连接到已存在的浏览器
        _browser = _playwright.chromium.connect_over_cdp(cdp_url)
        context = _browser.contexts[0]
        # 获取第一个页面或新建
        _page = context.pages[0] if context.pages else context.new_page()
        return _page
    except Exception as e:
        raise ConnectionError(f"无法连接到 Chrome ({cdp_url})。请确保 Chrome 以 '--remote-debugging-port=9222' 启动.\n错误: {e}")

def run(actions: List[Dict[str, Any]], cdp_url: str = "http://localhost:9222", **kwargs) -> str:
    """
    执行浏览器动作序列
    
    Args:
        actions: 动作列表，例如：
            [
                {"action": "goto", "url": "https://example.com"},
                {"action": "click", "selector": "#btn"},
                {"action": "type", "selector": "#input", "text": "hello"},
                {"action": "screenshot", "path": "output/shot.png"}
            ]
        cdp_url: 调试端口地址
    """
    try:
        page = _get_page(cdp_url)
        results = []
        
        for i, act in enumerate(actions):
            action_type = act.get("action")
            
            if action_type == "goto":
                url = act.get("url")
                page.goto(url)
                results.append(f"[{i+1}] 导航到: {url}")
                
            elif action_type == "click":
                selector = act.get("selector")
                page.click(selector)
                results.append(f"[{i+1}] 点击: {selector}")
                
            elif action_type == "type":
                selector = act.get("selector")
                text = act.get("text")
                page.fill(selector, text)
                results.append(f"[{i+1}] 输入: {text} -> {selector}")
                
            elif action_type == "press":
                key = act.get("key")
                page.keyboard.press(key)
                results.append(f"[{i+1}] 按键: {key}")
                
            elif action_type == "wait":
                ms = act.get("ms", 1000)
                page.wait_for_timeout(ms)
                results.append(f"[{i+1}] 等待: {ms}ms")
                
            elif action_type == "screenshot":
                path = act.get("path", "output/screenshot.png")
                # 确保目录存在
                os.makedirs(os.path.dirname(path), exist_ok=True)
                page.screenshot(path=path)
                results.append(f"[{i+1}] 截图已保存: {path}")
                
            elif action_type == "get_content":
                content = page.content()
                results.append(f"[{i+1}] 获取页面内容 ({len(content)} chars)")
                
            else:
                results.append(f"[{i+1}] 未知动作: {action_type}")
                
        return "\n".join(results)
        
    except Exception as e:
        return f"浏览器操作失败: {str(e)}"

# 供测试用
def _close():
    global _playwright, _browser, _page
    if _browser:
        _browser.close()
    if _playwright:
        _playwright.stop()
    _playwright = None
    _browser = None
    _page = None
