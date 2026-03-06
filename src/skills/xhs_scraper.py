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
from datetime import datetime
from typing import Optional

SKILL_NAME = "xhs_scraper"
SKILL_DESCRIPTION = "小红书帖子数据采集：自动打开小红书链接，提取帖子标题、正文、评论、互动数据等，保存为结构化文件。参数：url(必填), collect_account(可选,默认False), max_comments(可选,默认50)"

# 项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# Cookie 上下文（由 nodes.py 在运行前注入）
# ============================================================
_xhs_context = {"cookie": ""}


def init_xhs_context(cookie: str = ""):
    """初始化 XHS 上下文（由 nodes.py 调用）"""
    global _xhs_context
    _xhs_context = {"cookie": cookie}


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

    # 扫描 data 目录找到第一个用户 ID
    user_id = "__global__"
    data_dir = os.path.join(_PROJECT_ROOT, "data")
    try:
        for item in os.listdir(data_dir):
            if item.startswith("user_") and os.path.isdir(os.path.join(data_dir, item)):
                user_id = item
                break
    except:
        pass

    mgr = LLMManager(user_id)

    # 尝试获取一个可用的模型
    model = None
    for provider in mgr.providers.values():
        try:
            model_name = provider.models[0] if provider.models else None
            if model_name:
                model = mgr.get_model(provider.id, model_name, temperature=0.1)
                break
        except:
            continue

    if not model:
        raise RuntimeError("无法找到可用的 LLM 模型。请检查 LLM Provider 配置。")

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
    """将结构化数据格式化为 Markdown"""
    lines = []

    title = data.get("title", "未知标题")
    lines.append(f"# {title}")
    lines.append("")

    # 基本信息
    lines.append("## 基本信息")
    lines.append(f"- **作者**: {data.get('author', '未知')}")
    lines.append(f"- **发布时间**: {data.get('publish_time', '未知')}")
    lines.append(f"- **帖子类型**: {data.get('post_type', '未知')}")
    likes = data.get('likes', 0)
    favs = data.get('favorites', 0)
    comments_count = data.get('comment_count', 0)
    lines.append(f"- **互动数据**: 👍 {likes} | ⭐ {favs} | 💬 {comments_count}")
    lines.append(f"- **原始链接**: {url}")
    lines.append(f"- **采集时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 帖子正文
    lines.append("## 帖子正文")
    content = data.get("content", "")
    if not content or content == "null":
        content = "[未能提取正文内容]"
    lines.append(content)
    lines.append("")

    # 标签
    tags = data.get("tags", [])
    if tags:
        lines.append("## 标签")
        lines.append(" ".join([f"#{t}" for t in tags]))
        lines.append("")

    # 评论
    comments = data.get("comments", [])
    lines.append(f"## 评论 (已采集 {len(comments)} 条)")
    if comments:
        for i, c in enumerate(comments, 1):
            user = c.get("user", "匿名")
            text = c.get("content", "")
            c_likes = c.get("likes", 0)
            lines.append(f"{i}. **{user}**: {text} (👍 {c_likes})")
    else:
        lines.append("暂无评论数据。")
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
        # Step 1: 尝试无头浏览器
        # ============================================
        results_log.append("[1/7] 正在启动浏览器（无头模式）...")
        cookie_str = _xhs_context.get("cookie", "")
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

                if _has_display():
                    # --- 有桌面：切换有头模式，等待用户扫码 ---
                    results_log.append("  → 检测到桌面环境，切换有头模式等待扫码登录...")
                    _close_browser_internal()
                    try:
                        page = _ensure_page(url, browser="chromium", headless=False)
                        results_log.append("  ✓ 有头浏览器已打开，请在弹出窗口中扫码登录")
                        results_log.append("  ⏳ 等待登录中（最多 120 秒）...")

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
                        results_log.append("  → 降级为 HTTP 抓取模式")
                        _close_browser_internal()
                        page = None
                        use_fetch_fallback = True
                else:
                    # --- 无桌面：直接降级 fetch ---
                    results_log.append("  → 无桌面环境，无法扫码，降级为 HTTP 抓取模式")
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

        # 保存到 data/.xhs_data/ 目录
        save_dir = os.path.join(_PROJECT_ROOT, "data", ".xhs_data")
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        results_log.append(f"  ✓ 文件已保存: {filepath}")

        # 关闭浏览器
        if not use_fetch_fallback:
            _close_browser_internal()

        # 返回结果摘要
        mode_note = "（HTTP 降级模式，部分动态数据可能缺失）" if use_fetch_fallback else ""
        summary = f"""✅ 小红书帖子数据采集完成！{mode_note}

**帖子标题**: {title}
**帖子类型**: {post_data.get('post_type', '未知')}
**互动数据**: 👍 {post_data.get('likes', 0)} | ⭐ {post_data.get('favorites', 0)} | 💬 {post_data.get('comment_count', 0)}
**采集评论**: {len(post_data.get('comments', []))} 条
**保存位置**: {filepath}

---
执行日志:
""" + "\n".join(results_log)

        return summary

    except Exception as e:
        _close_browser_internal()
        return f"❌ 采集失败: {str(e)}\n\n执行日志:\n" + "\n".join(results_log)

