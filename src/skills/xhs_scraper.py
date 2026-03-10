"""
XHS Scraper Skill（Layer 2 标准技能）
小红书帖子数据采集：打开小红书链接，提取帖子标题、正文、评论、互动数据等，
保存为结构化 Markdown 文件。

依赖 Layer 1 工具：playwright_tools（open_browser, get_page_text 等）
"""

import os
import json
import time
import re
import threading
from collections import deque
from datetime import datetime
from typing import Optional

SKILL_NAME = "xhs_scraper"
SKILL_DESCRIPTION = "小红书帖子数据采集：自动打开小红书链接，提取帖子标题、正文、评论、互动数据等，自动保存为标准 Markdown 报告文件到工作区 shared 目录。返回的结果已包含格式化内容，无需再用 write_file 重新保存。参数：url(必填), collect_account(可选,默认False), max_comments(可选,默认50)"

# 项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 共享 cookies 文件路径
_SHARED_COOKIE_FILE = os.path.join(_PROJECT_ROOT, "data", ".xhs_shared_cookies.json")

# ============================================================
# 全局频率限制器（每分钟最多 2 次请求）
# ============================================================
_rate_lock = threading.Lock()
_request_times: deque = deque(maxlen=2)  # 最近 2 次请求时间戳
_RATE_LIMIT = 2       # 每分钟最大请求数
_RATE_WINDOW = 60     # 窗口大小（秒）


def _wait_for_rate_limit() -> float:
    """等待频率限制通过，返回实际等待秒数"""
    with _rate_lock:
        now = time.time()
        # 清除窗口外的旧记录
        while _request_times and now - _request_times[0] > _RATE_WINDOW:
            _request_times.popleft()
        # 如果窗口内已达上限，需要等待
        if len(_request_times) >= _RATE_LIMIT:
            wait_seconds = _RATE_WINDOW - (now - _request_times[0]) + 0.5
            if wait_seconds > 0:
                return wait_seconds
        return 0


def _record_request():
    """记录一次请求时间"""
    with _rate_lock:
        _request_times.append(time.time())


def _load_shared_cookies() -> str:
    """加载服务器预存的共享 cookies，返回 cookie 字符串"""
    if not os.path.exists(_SHARED_COOKIE_FILE):
        return ""
    try:
        with open(_SHARED_COOKIE_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        if cookies:
            parts = [f"{c['name']}={c['value']}" for c in cookies]
            return "; ".join(parts)
    except Exception:
        pass
    return ""


# ============================================================
# Cookie 上下文（由 nodes.py 在运行前注入）
# ============================================================
_xhs_context = {"cookie": "", "event_queue": None, "user_id": ""}


def init_xhs_context(cookie: str = "", event_queue=None, user_id: str = ""):
    """初始化 XHS 上下文（由 nodes.py 调用）"""
    global _xhs_context
    _xhs_context = {"cookie": cookie, "event_queue": event_queue, "user_id": user_id}


def _parse_cookie_string(cookie_str: str, domain: str = ".xiaohongshu.com") -> list:
    """将 'a1=xxx; web_session=yyy' 格式的 cookie 字符串解析为 Playwright add_cookies 格式"""
    cookies = []
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            name, value = item.split("=", 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": domain,
                "path": "/",
            })
    return cookies

# LLM 解析 Prompt
_EXTRACT_PROMPT = """你是一个数据提取专家。以下是小红书帖子页面的原始文本。
请从中提取以下结构化信息并返回**纯 JSON**（不要用 markdown 代码块包裹）：

{
  "title": "帖子标题",
  "author": "作者昵称",
  "publish_time": "发布时间（如果有）",
  "post_type": "图文 / 视频 / 纯文字",
  "content": "帖子正文内容（完整提取）",
  "tags": ["标签1", "标签2"],
  "likes": 0,
  "favorites": 0,
  "comment_count": 0,
  "comments": [
    {"user": "用户名", "content": "评论内容", "likes": 0}
  ]
}

注意：
1. 数字字段（likes, favorites, comment_count）请转为整数，如 "1.2万" 转为 12000
2. 如果某个字段无法提取，设为 null
3. comments 数组中只包含能识别出的评论
4. 只返回 JSON，不要添加任何解释

以下是页面原始文本：
"""

_ACCOUNT_PROMPT = """你是一个数据提取专家。以下是小红书用户主页的原始文本。
请提取以下信息并返回**纯 JSON**（不要用 markdown 代码块包裹）：

{
  "nickname": "昵称",
  "xiaohongshu_id": "小红书号",
  "followers": 0,
  "following": 0,
  "total_likes_and_favorites": 0,
  "bio": "个人简介"
}

注意：数字请转为整数。只返回 JSON。

以下是页面原始文本：
"""


def _parse_number(text: str) -> int:
    """将中文数字表达（如 '1.2万'）转为整数"""
    if not text:
        return 0
    text = text.strip()
    try:
        if '万' in text:
            return int(float(text.replace('万', '')) * 10000)
        elif '亿' in text:
            return int(float(text.replace('亿', '')) * 100000000)
        else:
            return int(re.sub(r'[^\d]', '', text) or 0)
    except:
        return 0


def _call_llm(prompt: str, text: str) -> dict:
    """调用 LLM 解析文本为结构化 JSON"""
    from src.core.llm_manager import LLMManager

    # 从上下文获取 user_id
    user_id = _xhs_context.get("user_id", "") or "__global__"

    mgr = LLMManager(user_id)
    print(f"[XHS] LLMManager for user={user_id}, providers={list(mgr.providers.keys())}")

    # 尝试获取一个可用的模型
    model = None
    errors = []
    for pid, provider in mgr.providers.items():
        try:
            model_name = provider.models[0] if provider.models else None
            if model_name:
                print(f"[XHS] Trying provider={pid}, model={model_name}")
                model = mgr.get_model(provider.id, model_name, temperature=0.1)
                break
        except Exception as e:
            errors.append(f"{pid}: {e}")
            continue

    if not model:
        err_detail = "; ".join(errors) if errors else "no providers found"
        raise RuntimeError(f"无法找到可用的 LLM 模型（user={user_id}, errors=[{err_detail}]）。请检查 LLM Provider 配置。")

    # 截断输入防止 token 超限
    max_text_len = 12000
    if len(text) > max_text_len:
        text = text[:max_text_len] + "\n...[文本已截断]"

    response = model.invoke(prompt + text)
    content = response.content if hasattr(response, 'content') else str(response)

    # 尝试从响应中提取 JSON
    # 处理可能被 markdown 代码块包裹的情况
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
    if json_match:
        content = json_match.group(1)

    # 清理并解析
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 尝试找到第一个 { 和最后一个 }
        start = content.find('{')
        end = content.rfind('}')
        if start >= 0 and end > start:
            try:
                return json.loads(content[start:end + 1])
            except:
                pass
        return {"error": "LLM 返回内容无法解析为 JSON", "raw": content[:500]}


def _format_markdown(data: dict, url: str, account_data: dict = None) -> str:
    """将结构化数据格式化为统一 Markdown 模板"""
    lines = []

    lines.append("# 小红书帖子内容抓取报告")
    lines.append("")

    # 帖子基本信息
    lines.append("## 帖子基本信息")
    lines.append(f"- **链接**: {url}")
    lines.append(f"- **标题**: {data.get('title', '未知标题')}")
    lines.append(f"- **作者**: {data.get('author', '未知')}")
    lines.append(f"- **发布日期**: {data.get('publish_time', '未知')}")
    location = data.get('location', '')
    if location and location != 'null':
        lines.append(f"- **发布地点**: {location}")
    lines.append("")

    # 帖子正文内容
    lines.append("## 帖子正文内容")
    content = data.get("content", "")
    if not content or content == "null":
        content = "[未能提取正文内容]"
    lines.append(content)
    lines.append("")

    # 标签
    tags = data.get("tags", [])
    if tags:
        lines.append("## 标签 (Hashtags)")
        lines.append(" ".join([f"#{t}" for t in tags]))
        lines.append("")

    # 互动数据
    lines.append("## 互动数据 (Engagement Data)")
    lines.append(f"- **点赞**：{data.get('likes', 0)}")
    lines.append(f"- **收藏**：{data.get('favorites', 0)}")
    lines.append(f"- **评论**：{data.get('comment_count', 0)}")
    lines.append("")

    # 评论
    comments = data.get("comments", [])
    if comments:
        lines.append(f"## 评论详情 (已采集 {len(comments)} 条)")
        for i, c in enumerate(comments, 1):
            user = c.get("user", "匿名")
            text = c.get("content", "")
            c_likes = c.get("likes", 0)
            lines.append(f"{i}. **{user}**: {text} (👍 {c_likes})")
        lines.append("")

    # 账号数据（如果有）
    if account_data and not account_data.get("error"):
        lines.append("## 作者账号信息")
        lines.append(f"- **昵称**: {account_data.get('nickname', '未知')}")
        lines.append(f"- **小红书号**: {account_data.get('xiaohongshu_id', '未知')}")
        lines.append(f"- **粉丝数**: {account_data.get('followers', 0)}")
        lines.append(f"- **关注数**: {account_data.get('following', 0)}")
        lines.append(f"- **获赞与收藏**: {account_data.get('total_likes_and_favorites', 0)}")
        bio = account_data.get('bio', '')
        if bio:
            lines.append(f"- **简介**: {bio}")
        lines.append("")

    # 采集信息
    lines.append("---")
    lines.append(f"*采集时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    return "\n".join(lines)


def _sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符"""
    # 移除 Windows 不允许的字符
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # 移除前后空白和点
    name = name.strip().strip('.')
    # 限制长度
    if len(name) > 80:
        name = name[:80]
    return name or "untitled"


def run(url: str, collect_account: bool = False, max_comments: int = 50, **kwargs) -> str:
    """
    采集小红书帖子数据

    Args:
        url: 小红书帖子链接
        collect_account: 是否同时采集作者账号数据（粉丝数等）
        max_comments: 最多采集评论数量，默认 50 条
    """
    from src.tools.playwright_tools import (
        _ensure_page, _has_display, _close_browser_internal,
        close_browser,
    )

    results_log = []
    use_fetch_fallback = False
    page_text = None
    page = None

    try:
        # ============================================
        # Step 0: 频率限制排队
        # ============================================
        wait_time = _wait_for_rate_limit()
        if wait_time > 0:
            results_log.append(f"[0/7] ⏳ 频率限制：排队等待 {wait_time:.0f} 秒（每分钟最多 {_RATE_LIMIT} 次）...")
            time.sleep(wait_time)
        _record_request()

        # ============================================
        # Step 1: 尝试无头浏览器
        # ============================================
        results_log.append("[1/7] 正在启动浏览器（无头模式）...")
        # 优先使用用户自己的 cookie，其次用服务器共享 cookie
        cookie_str = _xhs_context.get("cookie", "") or _load_shared_cookies()
        if cookie_str and cookie_str == _load_shared_cookies():
            results_log.append("  ℹ 使用服务器预存的共享登录 session")
        try:
            page = _ensure_page(url, browser="chromium", headless=True)
            results_log.append(f"  ✓ 无头浏览器已打开: {url}")

            # 注入用户 Cookie（如果有）
            if cookie_str:
                cookies = _parse_cookie_string(cookie_str)
                if cookies:
                    page.context.add_cookies(cookies)
                    results_log.append(f"  ✓ 已注入 {len(cookies)} 条 Cookie")
                    # 重新导航以使 Cookie 生效
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)

            page.wait_for_timeout(3000)
        except Exception as headless_err:
            results_log.append(f"  ✗ 无头浏览器启动失败: {headless_err}")
            page = None

        # ============================================
        # Step 2: 登录检测 + 有头/fetch 降级
        # ============================================
        if page:
            results_log.append("[2/7] 检测登录状态...")
            login_detected = False
            login_selectors = [".login-container", ".qrcode-img", "[class*='login-btn']"]
            for sel in login_selectors:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        login_detected = True
                        break
                except:
                    continue

            if login_detected:
                results_log.append("  ⚠ 检测到登录弹窗")
                event_queue = _xhs_context.get("event_queue")

                if event_queue:
                    # --- SSE 推送二维码到前端 ---
                    results_log.append("  → 正在截图二维码推送到前端...")
                    try:
                        import base64
                        # 截图整个页面（包含 QR 码）
                        qr_screenshot = page.screenshot()
                        qr_b64 = base64.b64encode(qr_screenshot).decode("utf-8")
                        event_queue.put({
                            "type": "qr_login",
                            "image": qr_b64,
                            "message": "请用小红书 App 扫码登录"
                        })
                        results_log.append("  ✓ 二维码已推送，等待用户扫码（最多 120 秒）...")

                        # 轮询等待登录成功
                        start_time = time.time()
                        logged_in = False
                        last_qr_push = start_time
                        while time.time() - start_time < 120:
                            time.sleep(3)
                            # 检查登录弹窗是否消失
                            still_login = False
                            for sel in login_selectors:
                                try:
                                    el = page.query_selector(sel)
                                    if el and el.is_visible():
                                        still_login = True
                                        break
                                except:
                                    continue
                            if not still_login:
                                logged_in = True
                                break
                            # 每 15 秒重新截图推送（二维码可能刷新）
                            if time.time() - last_qr_push > 15:
                                try:
                                    qr_screenshot = page.screenshot()
                                    qr_b64 = base64.b64encode(qr_screenshot).decode("utf-8")
                                    event_queue.put({
                                        "type": "qr_login",
                                        "image": qr_b64,
                                        "message": "请用小红书 App 扫码登录"
                                    })
                                    last_qr_push = time.time()
                                except:
                                    pass

                        if logged_in:
                            results_log.append("  ✓ 扫码登录成功！")
                            event_queue.put({"type": "qr_login_success", "message": "登录成功"})
                            # 保存 Cookie 到用户数据目录
                            try:
                                ctx_cookies = page.context.cookies()
                                xhs_cookies = [c for c in ctx_cookies if "xiaohongshu" in c.get("domain", "")]
                                if xhs_cookies:
                                    cookie_str_parts = [f"{c['name']}={c['value']}" for c in xhs_cookies]
                                    saved_cookie = "; ".join(cookie_str_parts)
                                    uid = _xhs_context.get("user_id", "")
                                    if uid:
                                        cookie_path = os.path.join(_PROJECT_ROOT, "data", uid, ".xhs_cookie")
                                        os.makedirs(os.path.dirname(cookie_path), exist_ok=True)
                                        with open(cookie_path, "w", encoding="utf-8") as f:
                                            f.write(saved_cookie)
                                        results_log.append(f"  ✓ Cookie 已保存（{len(xhs_cookies)} 条）")
                            except Exception as save_err:
                                results_log.append(f"  ⚠ Cookie 保存失败: {save_err}")
                            # 重新导航到目标页面
                            page.goto(url, wait_until="domcontentloaded", timeout=30000)
                            page.wait_for_timeout(3000)
                        else:
                            results_log.append("  ✗ 扫码超时，降级为 HTTP 抓取模式")
                            event_queue.put({"type": "qr_login_timeout", "message": "扫码超时"})
                            _close_browser_internal()
                            page = None
                            use_fetch_fallback = True
                    except Exception as qr_err:
                        results_log.append(f"  ✗ 扫码流程失败: {qr_err}")
                        try:
                            event_queue.put({"type": "qr_login_timeout", "message": str(qr_err)})
                        except:
                            pass
                        _close_browser_internal()
                        page = None
                        use_fetch_fallback = True

                elif _has_display():
                    # --- 有桌面但无 event_queue：切换有头模式 ---
                    results_log.append("  → 检测到桌面环境，切换有头模式等待扫码登录...")
                    _close_browser_internal()
                    try:
                        page = _ensure_page(url, browser="chromium", headless=False)
                        results_log.append("  ✓ 有头浏览器已打开，请在弹出窗口中扫码登录")
                        page.wait_for_timeout(3000)
                        start_time = time.time()
                        logged_in = False
                        while time.time() - start_time < 120:
                            time.sleep(3)
                            still_login = False
                            for sel in login_selectors:
                                try:
                                    el = page.query_selector(sel)
                                    if el and el.is_visible():
                                        still_login = True
                                        break
                                except:
                                    continue
                            if not still_login:
                                logged_in = True
                                break
                        if logged_in:
                            results_log.append("  ✓ 登录成功！")
                            page.goto(url, wait_until="domcontentloaded", timeout=30000)
                            page.wait_for_timeout(3000)
                        else:
                            results_log.append("  ✗ 登录超时，降级为 HTTP 抓取模式")
                            _close_browser_internal()
                            page = None
                            use_fetch_fallback = True
                    except Exception as headed_err:
                        results_log.append(f"  ✗ 有头浏览器也失败: {headed_err}")
                        _close_browser_internal()
                        page = None
                        use_fetch_fallback = True
                else:
                    # --- 无桌面且无 event_queue：直接降级 fetch ---
                    results_log.append("  → 无桌面环境且无事件队列，降级为 HTTP 抓取模式")
                    _close_browser_internal()
                    page = None
                    use_fetch_fallback = True
            else:
                results_log.append("  ✓ 已处于登录状态（或无需登录）")
        else:
            # 无头浏览器启动就失败了
            results_log.append("  → 降级为 HTTP 抓取模式...")
            use_fetch_fallback = True

        # ============================================
        # Fetch 降级模式
        # ============================================
        if use_fetch_fallback:
            try:
                from src.tools.web_tools import fetch_url_content
                fetch_result = fetch_url_content.invoke({"url": url})
                if fetch_result and not fetch_result.startswith("网页抓取失败") and not fetch_result.startswith("解析出错"):
                    page_text = fetch_result
                    results_log.append(f"  ✓ HTTP 抓取成功，获取到 {len(page_text)} 字符")
                    results_log.append("  ⚠ 注意：HTTP 模式可能无法获取点赞、评论等动态数据")
                else:
                    return f"❌ 采集失败: 浏览器和 HTTP 抓取均失败。\nHTTP 结果: {fetch_result}\n\n执行日志:\n" + "\n".join(results_log)
            except Exception as fetch_err:
                return f"❌ 采集失败: 所有抓取方式均失败。\n错误: {fetch_err}\n\n执行日志:\n" + "\n".join(results_log)

        # ============================================
        # Step 3-5: 浏览器模式独有步骤
        # ============================================
        if page and not use_fetch_fallback:
            # Step 3: 等待帖子内容加载
            results_log.append("[3/7] 等待帖子内容加载...")
            page.wait_for_timeout(2000)
            results_log.append("  ✓ 页面已加载")

            # Step 4: 滚动加载评论
            results_log.append(f"[4/7] 滚动加载评论 (最多 {max_comments} 条)...")
            scroll_attempts = min(max_comments // 5, 15)
            for i in range(scroll_attempts):
                page.evaluate("window.scrollBy(0, 800)")
                page.wait_for_timeout(1500)
            results_log.append(f"  ✓ 完成 {scroll_attempts} 次滚动")

            # Step 5: 提取页面文本
            results_log.append("[5/7] 提取页面文本...")
            page_text = page.inner_text("body")

            if not page_text or len(page_text) < 50:
                return "❌ 页面内容提取失败，可能页面未正确加载。\n\n" + "\n".join(results_log)

            results_log.append(f"  ✓ 获取到 {len(page_text)} 字符")

        # ============================================
        # Step 6: LLM 结构化解析
        # ============================================
        results_log.append("[6/7] 调用 LLM 解析数据...")
        post_data = _call_llm(_EXTRACT_PROMPT, page_text)

        if post_data.get("error"):
            results_log.append(f"  ⚠ LLM 解析异常: {post_data['error']}")
        else:
            results_log.append(f"  ✓ 解析成功: {post_data.get('title', '未知标题')}")

        # 可选：采集账号数据（仅浏览器模式）
        account_data = None
        if collect_account and page and not use_fetch_fallback:
            results_log.append("[6.5/7] 采集作者账号数据...")
            try:
                author_selectors = [
                    "a.author-wrapper",
                    ".author-container a",
                    "a[href*='/user/profile']",
                    ".note-user a",
                ]
                clicked = False
                for sel in author_selectors:
                    try:
                        el = page.query_selector(sel)
                        if el:
                            href = el.get_attribute("href")
                            if href:
                                if href.startswith("/"):
                                    href = "https://www.xiaohongshu.com" + href
                                page.goto(href, wait_until="domcontentloaded", timeout=15000)
                                page.wait_for_timeout(3000)
                                clicked = True
                                break
                    except:
                        continue

                if clicked:
                    account_text = page.inner_text("body")
                    account_data = _call_llm(_ACCOUNT_PROMPT, account_text)
                    results_log.append("  ✓ 账号数据采集成功")
                else:
                    results_log.append("  ⚠ 未找到作者主页链接")
            except Exception as e:
                results_log.append(f"  ⚠ 账号数据采集失败: {e}")

        # ============================================
        # Step 7: 保存文件
        # ============================================
        results_log.append("[7/7] 保存数据文件...")

        title = post_data.get("title", "未知标题")
        filename = _sanitize_filename(title) + ".md"

        markdown_content = _format_markdown(post_data, url, account_data)

        # 保存到工作区 shared 目录（如果能获取到），否则保存到 data/.xhs_data/
        save_dir = None
        workspace_id = kwargs.get("workspace_id", "")
        if workspace_id:
            save_dir = os.path.join(_PROJECT_ROOT, "data", workspace_id, "shared")
        if not save_dir or not os.path.isdir(os.path.dirname(save_dir)):
            save_dir = os.path.join(_PROJECT_ROOT, "data", ".xhs_data")
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        results_log.append(f"  ✓ 文件已保存: {filepath}")

        # 关闭浏览器
        if not use_fetch_fallback:
            _close_browser_internal()

        # 返回结果摘要（告知 Agent 文件已保存，不要重复 write_file）
        mode_note = "（HTTP 降级模式，部分动态数据可能缺失）" if use_fetch_fallback else ""
        summary = f"""✅ 小红书帖子数据采集完成！{mode_note}

**帖子标题**: {title}
**互动数据**: 👍 {post_data.get('likes', 0)} | ⭐ {post_data.get('favorites', 0)} | 💬 {post_data.get('comment_count', 0)}
**采集评论**: {len(post_data.get('comments', []))} 条
**文件已自动保存**: {filepath}

⚠️ 文件已按标准模板自动保存，无需再用 write_file 重新保存。

---
执行日志:
""" + "\n".join(results_log)

        return summary

    except Exception as e:
        _close_browser_internal()
        return f"❌ 采集失败: {str(e)}\n\n执行日志:\n" + "\n".join(results_log)

