"""
Memory Skill — 每日对话记忆总结
定时于 00:00（北京时间）自动总结各 Agent 当日对话，生成 4 类记忆输出：
1. 今日里程碑 → Agent 知识库（向量化）
2. 全局用户偏好 → 系统级偏好文件
3. 未竟事项 → Agent 归档目录
4. 新实体/术语 → Agent 知识库（向量化）
"""

import os
import json
import re
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("memory_skill")

SKILL_NAME = "daily_memory"
SKILL_DESCRIPTION = "每日对话记忆总结：分析当天所有对话，生成里程碑、用户偏好、未竟事项和新术语。系统自动在每天 00:00 执行。"

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA_ROOT = os.path.join(_PROJECT_ROOT, "data")

# ============================================================
# LLM Prompt
# ============================================================

_MEMORY_PROMPT = """你是一个记忆管理助手。请分析以下 Agent「{agent_name}」今日的对话记录，提取 4 类信息并输出严格 JSON。

**输出格式（必须是合法 JSON）：**
```json
{{
  "milestones": "今天完成的关键事项，Markdown 列表格式。如果没有实质内容则为空字符串",
  "preferences": "识别到的用户持久性偏好（审美、回复风格、技术路线等）。只记录持久性的偏好，不要记录临时要求。如果没有新偏好则为空字符串",
  "pending_tasks": "未完成的任务及其上下文，方便下次无缝衔接。Markdown 列表格式。如果没有则为空字符串",
  "new_terms": "今天提到的新名词、新项目名及其定义。Markdown 列表格式。如果没有则为空字符串"
}}
```

**昨日未竟事项（判断哪些已完成、哪些仍在进行、哪些是新增）：**
{yesterday_pending}

**今日对话记录：**
{messages}
"""


# ============================================================
# 数据获取
# ============================================================

def _fetch_today_sessions(user_id: str) -> list[dict]:
    """从 Supabase 查询该用户今日所有 chat_sessions"""
    from backend.supabase_client import supabase

    # 北京时间今日 00:00 ~ 明日 00:00
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)

    result = supabase.table("chat_sessions") \
        .select("id, context_id, title, messages, updated_at") \
        .eq("user_id", user_id) \
        .gte("updated_at", today_start.isoformat()) \
        .lt("updated_at", tomorrow_start.isoformat()) \
        .execute()

    return result.data or []


def _group_by_agent(sessions: list[dict]) -> dict[str, list[dict]]:
    """按 context_id (Agent ID) 分组"""
    groups = {}
    for s in sessions:
        aid = s.get("context_id", "unknown")
        groups.setdefault(aid, []).append(s)
    return groups


def _flatten_messages(sessions: list[dict]) -> str:
    """将多个 session 的 messages 合并为可读文本"""
    lines = []
    for s in sessions:
        messages = s.get("messages", [])
        if not messages:
            continue
        lines.append(f"--- 会话: {s.get('title', '未命名')} ---")
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if not content:
                continue
            # 截断过长的单条消息
            if len(content) > 2000:
                content = content[:2000] + "...[截断]"
            role_label = "用户" if role == "human" else "助手" if role in ("ai", "assistant") else role
            lines.append(f"[{role_label}]: {content}")
        lines.append("")
    return "\n".join(lines)


# ============================================================
# LLM 调用
# ============================================================

def _get_llm(user_id: str):
    """获取可用的 LLM 模型"""
    from src.core.llm_manager import LLMManager

    mgr = LLMManager(user_id)

    # Fallback: 如果当前 user 没有 providers，从 Supabase 找一个
    if not mgr.providers:
        try:
            from backend.supabase_client import supabase
            result = supabase.table("llm_providers").select("user_id").limit(1).execute()
            if result.data:
                mgr = LLMManager(result.data[0]["user_id"])
        except Exception:
            pass

    for provider in mgr.providers.values():
        try:
            model_name = provider.models[0] if provider.models else None
            if model_name:
                return mgr.get_model(provider.id, model_name, temperature=0.3)
        except Exception:
            continue

    raise RuntimeError(f"[MemorySkill] 无法找到可用的 LLM 模型 (user={user_id})")


def _call_llm_for_memory(user_id: str, agent_name: str,
                          messages_text: str, yesterday_pending: str) -> dict:
    """调用 LLM 生成 4 类记忆输出"""
    model = _get_llm(user_id)

    # 控制输入长度
    max_len = 15000
    if len(messages_text) > max_len:
        messages_text = messages_text[:max_len] + "\n...[对话内容已截断]"

    prompt = _MEMORY_PROMPT.format(
        agent_name=agent_name,
        yesterday_pending=yesterday_pending or "（无）",
        messages=messages_text,
    )

    response = model.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)

    # 提取 JSON
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
    if json_match:
        content = json_match.group(1)

    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 尝试修复常见 JSON 问题
        try:
            # 找到第一个 { 和最后一个 }
            start = content.index("{")
            end = content.rindex("}") + 1
            return json.loads(content[start:end])
        except Exception:
            logger.error(f"[MemorySkill] JSON 解析失败, raw={content[:500]}")
            return {}


# ============================================================
# 文件写入
# ============================================================

def _read_file_safe(path: str) -> str:
    """安全读取文件，文件不存在则返回空字符串"""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _write_file(path: str, content: str):
    """写入文件，自动创建目录"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _append_to_file(path: str, content: str):
    """追加内容到文件"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)


def _write_outputs(user_id: str, agent_id: str, agent_name: str,
                    workspace_id: str, result: dict):
    """将 4 类输出写入对应位置"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    agent_dir = os.path.join(_DATA_ROOT, user_id, workspace_id, agent_id) if workspace_id \
        else os.path.join(_DATA_ROOT, user_id, agent_id)

    # --- 1. 今日里程碑 → knowledge_base ---
    milestones = result.get("milestones", "")
    if milestones:
        kb_dir = os.path.join(agent_dir, "knowledge_base")
        milestone_file = os.path.join(kb_dir, f"里程碑_{today_str}.md")
        content = f"# {agent_name} 里程碑 — {today_str}\n\n{milestones}\n"
        _write_file(milestone_file, content)

        # Ingest 到向量库
        try:
            from src.utils.rag_ingestion import RAGIngestion
            rag = RAGIngestion(_DATA_ROOT, workspace_id or user_id, agent_id)
            chunks = rag.ingest_file(milestone_file)
            logger.info(f"[MemorySkill] 里程碑已向量化: {chunks} chunks")
        except Exception as e:
            logger.warning(f"[MemorySkill] 里程碑向量化失败: {e}")

    # --- 2. 全局用户偏好 → 系统级文件 ---
    preferences = result.get("preferences", "")
    if preferences:
        pref_file = os.path.join(_DATA_ROOT, user_id, ".user_preferences.md")
        existing = _read_file_safe(pref_file)
        if existing:
            # 追加新偏好到文件末尾
            new_content = existing.rstrip() + f"\n\n## {today_str} 更新\n\n{preferences}\n"
        else:
            new_content = f"# 用户偏好\n\n> 此文件由记忆系统自动维护，记录用户的持久性偏好。\n\n## {today_str} 初始记录\n\n{preferences}\n"
        _write_file(pref_file, new_content)
        logger.info(f"[MemorySkill] 全局偏好已更新")

    # --- 3. 未竟事项 → archives ---
    pending = result.get("pending_tasks", "")
    archives_dir = os.path.join(agent_dir, "archives")
    pending_file = os.path.join(archives_dir, "未竟事项.md")
    if pending:
        content = f"# 未竟事项\n\n> 最后更新: {today_str}\n\n{pending}\n"
        _write_file(pending_file, content)
        logger.info(f"[MemorySkill] 未竟事项已更新: {agent_id}")
    else:
        # 如果没有未竟事项了，清空文件
        if os.path.exists(pending_file):
            content = f"# 未竟事项\n\n> 最后更新: {today_str}\n\n✅ 当前没有未完成的事项。\n"
            _write_file(pending_file, content)

    # --- 4. 新实体/术语 → knowledge_base ---
    terms = result.get("new_terms", "")
    if terms:
        kb_dir = os.path.join(agent_dir, "knowledge_base")
        terms_file = os.path.join(kb_dir, "术语表.md")
        existing = _read_file_safe(terms_file)
        if existing:
            new_content = existing.rstrip() + f"\n\n## {today_str} 新增\n\n{terms}\n"
        else:
            new_content = f"# 术语表\n\n> 此文件由记忆系统自动维护。\n\n## {today_str} 初始记录\n\n{terms}\n"
        _write_file(terms_file, new_content)

        # Ingest 到向量库
        try:
            from src.utils.rag_ingestion import RAGIngestion
            rag = RAGIngestion(_DATA_ROOT, workspace_id or user_id, agent_id)
            chunks = rag.ingest_file(terms_file)
            logger.info(f"[MemorySkill] 术语表已向量化: {chunks} chunks")
        except Exception as e:
            logger.warning(f"[MemorySkill] 术语表向量化失败: {e}")


# ============================================================
# 主入口
# ============================================================

def run(user_id: str, **kwargs) -> str:
    """
    执行每日记忆总结

    Args:
        user_id: 用户 ID
    """
    logger.info(f"[MemorySkill] 开始执行每日记忆总结, user={user_id}")
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 1. 获取今日所有会话
    sessions = _fetch_today_sessions(user_id)
    if not sessions:
        logger.info("[MemorySkill] 今日无对话记录，跳过")
        return f"✅ 每日记忆总结完成 ({today_str})\n\n今日无对话记录。"

    # 2. 按 Agent 分组
    agent_groups = _group_by_agent(sessions)
    logger.info(f"[MemorySkill] 今日对话涉及 {len(agent_groups)} 个 Agent")

    # 3. 获取 Agent 名称映射
    agent_names = {}
    try:
        from src.core.agent_registry import AgentRegistry
        ar = AgentRegistry(user_id)
        for a in ar.list_agents():
            agent_names[a["id"]] = a.get("name", a["id"])
    except Exception:
        pass

    # 4. 逐 Agent 处理
    results_log = []
    for agent_id, agent_sessions in agent_groups.items():
        agent_name = agent_names.get(agent_id, agent_id)
        logger.info(f"[MemorySkill] 处理 Agent: {agent_name} ({len(agent_sessions)} 个会话)")

        # 获取该 Agent 的 workspace
        workspace_id = ""
        try:
            ar = AgentRegistry(user_id)
            agent_config = ar.get_agent(agent_id)
            if agent_config:
                workspace_id = agent_config.get("workspace", "")
        except Exception:
            pass

        # 合并消息文本
        messages_text = _flatten_messages(agent_sessions)
        if not messages_text.strip():
            results_log.append(f"- **{agent_name}**: 无有效消息，跳过")
            continue

        # 读取昨日未竟事项
        agent_dir = os.path.join(_DATA_ROOT, user_id, workspace_id, agent_id) if workspace_id \
            else os.path.join(_DATA_ROOT, user_id, agent_id)
        pending_file = os.path.join(agent_dir, "archives", "未竟事项.md")
        yesterday_pending = _read_file_safe(pending_file)

        # 调用 LLM
        try:
            result = _call_llm_for_memory(user_id, agent_name, messages_text, yesterday_pending)
        except Exception as e:
            logger.error(f"[MemorySkill] LLM 调用失败 for {agent_name}: {e}")
            results_log.append(f"- **{agent_name}**: ❌ LLM 调用失败 ({e})")
            continue

        if not result:
            results_log.append(f"- **{agent_name}**: ⚠ LLM 返回为空")
            continue

        # 写入各类输出
        try:
            _write_outputs(user_id, agent_id, agent_name, workspace_id, result)
        except Exception as e:
            logger.error(f"[MemorySkill] 写入失败 for {agent_name}: {e}")
            results_log.append(f"- **{agent_name}**: ❌ 写入失败 ({e})")
            continue

        # 汇总结果
        has_milestone = bool(result.get("milestones"))
        has_pref = bool(result.get("preferences"))
        has_pending = bool(result.get("pending_tasks"))
        has_terms = bool(result.get("new_terms"))
        tags = []
        if has_milestone: tags.append("📌里程碑")
        if has_pref: tags.append("🎨偏好")
        if has_pending: tags.append("📋未竟")
        if has_terms: tags.append("📖术语")
        results_log.append(f"- **{agent_name}**: ✅ {' | '.join(tags) or '无新内容'}")

    # 5. 记录执行日志
    log_entry = f"\n## {today_str} 记忆总结\n\n" + "\n".join(results_log) + "\n"
    log_file = os.path.join(_DATA_ROOT, user_id, ".memory_log.md")
    _append_to_file(log_file, log_entry)

    summary = f"✅ 每日记忆总结完成 ({today_str})\n\n" + "\n".join(results_log)
    logger.info(f"[MemorySkill] 完成: {summary}")
    return summary
