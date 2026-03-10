"""
XHS Session 保存脚本
在服务器上运行此脚本，手动登录小红书后保存 cookies。
所有用户的 XHS 抓取请求将共享此登录 session。

用法：
  python3 scripts/save_xhs_session.py

注意：需要在有图形界面的环境下运行（VNC / 远程桌面 / X11 转发）。
如果服务器没有图形界面，可以用 --headless 模式 + 手动粘贴 cookie 的方式。
"""

import os
import sys
import json
import argparse

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COOKIE_FILE = os.path.join(PROJECT_ROOT, "data", ".xhs_shared_cookies.json")


def save_via_browser():
    """有图形界面时：打开浏览器让用户手动登录"""
    from playwright.sync_api import sync_playwright

    print("🚀 正在启动浏览器...")
    print("   请在弹出的浏览器窗口中登录小红书")
    print("   登录成功后，回到终端按回车保存 cookies\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")

        input("\n✅ 登录完成后按回车保存 cookies...")

        # 提取 cookies
        cookies = context.cookies()
        xhs_cookies = [c for c in cookies if "xiaohongshu" in c.get("domain", "")]

        os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(xhs_cookies, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 已保存 {len(xhs_cookies)} 条 cookies 到: {COOKIE_FILE}")
        browser.close()


def save_via_paste():
    """无图形界面时：手动粘贴 cookie 字符串"""
    print("📋 请从浏览器中复制小红书的 Cookie 字符串")
    print("   （开发者工具 → Network → 任意请求 → Headers → Cookie）\n")

    cookie_str = input("粘贴 Cookie 字符串: ").strip()
    if not cookie_str:
        print("❌ Cookie 为空，退出")
        return

    cookies = []
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            name, value = item.split("=", 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".xiaohongshu.com",
                "path": "/",
            })

    os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已保存 {len(cookies)} 条 cookies 到: {COOKIE_FILE}")


def check_status():
    """检查当前共享 cookies 状态"""
    if not os.path.exists(COOKIE_FILE):
        print("❌ 尚未保存共享 cookies")
        return

    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        cookies = json.load(f)

    mtime = os.path.getmtime(COOKIE_FILE)
    from datetime import datetime
    saved_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

    print(f"📄 Cookie 文件: {COOKIE_FILE}")
    print(f"🕐 保存时间: {saved_time}")
    print(f"🍪 Cookie 数量: {len(cookies)}")
    print(f"📝 Cookie 名称: {', '.join(c['name'] for c in cookies)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="XHS 共享登录 Session 管理")
    parser.add_argument("--paste", action="store_true", help="手动粘贴 cookie 模式（无图形界面时使用）")
    parser.add_argument("--status", action="store_true", help="查看当前 cookies 状态")
    args = parser.parse_args()

    if args.status:
        check_status()
    elif args.paste:
        save_via_paste()
    else:
        save_via_browser()
