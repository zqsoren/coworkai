"""
Learn Skill — Agent 学习技能
从文章/文件内容中提取经验知识和行为准则，纳入 Agent 知识库。

用法：Agent 收到含"学习"字眼的指令时调用此 Skill。

输出：
1. 经验知识 → Agent 知识库（向量化，可检索）
2. 行为准则 → Agent archives/行为标准.md（累积更新）
"""

import os
import json
import re
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("learn_skill")

SKILL_NAME = "learn"
SKILL_DESCRIPTION = """从文章或 URL 中学习知识，提取行业经验和可执行行为准则，存入知识库。
当用户说"学习这篇文章"、"学习一下"、"帮我分析/提取/总结知识"时，必须调用此工具。
参数 content: 文章的 URL 或文本内容（必填）"""

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA_ROOT = os.path.join(_PROJECT_ROOT, "data")

# ============================================================
# LLM Prompt
# ============================================================

_LEARN_PROMPT = """你是「{agent_name}」，{agent_role}。

请认真阅读以下内容，从你的专业角度提取两类信息，输出严格 JSON：

## 输出格式
```json
{{
  "knowledge_summary": "从文章中提取的行业知识、经验、方法论的结构化总结。用 Markdown 格式，包含要点和细节。",
  "behavior_rules": "从文章中提炼出的可执行行为准则列表。每条准则必须具体、可操作。\\n例如：不要说'写得吸引人'，要说'在标题前 5 个字使用数字'。\\n用 Markdown 列表格式。"
}}
```

## 要求
1. **知识总结**：站在你的职能角度，提取对你工作最有价值的知识点
2. **行为准则**：必须是具体的、可执行的规则，而非模糊的建议
3. 如果文章内容与你的职能无关，仍尽力提取通用的可用知识
4. 如果内容太短或无实质内容，对应字段返回空字符串

## 以下是要学习的内容：

{content}
"""


# ============================================================
# URL 获取
# ============================================================

def _fetch_url(url: str) -> str:
    """获取 URL 内容"""
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # 简单提取文本：去掉 HTML 标签
        text = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', html)
        text = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        logger.warning(f"[LearnSkill] URL 获取失败: {e}")
        return ""


def _is_url(text: str) -> bool:
    """判断是否为 URL"""
    text = text.strip()
    return text.startswith("http://") or text.startswith("https://")


# ============================================================
# LLM 调用
# ============================================================

def _get_llm(user_id: str, provider_id: str = "", model_name: str = ""):
    """获取可用的 LLM 模型，使用与 Agent 相同的 provider/model 配置"""
    from src.core.llm_manager import LLMManager

    print(f"[LearnSkill._get_llm] user_id={user_id}, provider_id={provider_id}, model_name={model_name}")

    mgr = LLMManager(user_id) if user_id else LLMManager("__global__")
    print(f"[LearnSkill._get_llm] loaded providers: {list(mgr.providers.keys())}")

    # 1. 优先使用 Agent 配置的 provider_id + model_name
    if provider_id:
        try:
            provider = mgr.get_provider(provider_id)
            if provider and (not model_name or str(model_name).strip() == ""):
                if provider.models and len(provider.models) > 0:
                    model_name = provider.models[0]
            if model_name:
                print(f"[LearnSkill._get_llm] trying Agent config: {provider_id}/{model_name}")
                return mgr.get_model(provider_id, model_name, temperature=0.3)
        except Exception as e:
            print(f"[LearnSkill._get_llm] Agent config FAILED: {e}")

    # 2. Fallback: 尝试 gemini_default
    try:
        print("[LearnSkill._get_llm] trying gemini_default/gemini-2.0-flash")
        return mgr.get_model("gemini_default", "gemini-2.0-flash", temperature=0.3)
    except Exception as e:
        print(f"[LearnSkill._get_llm] gemini_default FAILED: {e}")

    # 3. Fallback: 遍历所有 provider
    for provider in mgr.providers.values():
        try:
            m = provider.models[0] if provider.models else None
            if m:
                print(f"[LearnSkill._get_llm] trying {provider.id}/{m}")
                return mgr.get_model(provider.id, m, temperature=0.3)
        except Exception as e:
            print(f"[LearnSkill._get_llm] {provider.id} FAILED: {e}")
            continue

    raise RuntimeError(f"[LearnSkill] 无法找到可用的 LLM 模型 (user={user_id})")


def _call_llm(user_id: str, agent_name: str, agent_role: str, content: str,
              provider_id: str = "", model_name: str = "") -> dict:
    """调用 LLM 提取知识和行为准则"""
    model = _get_llm(user_id, provider_id, model_name)

    # 控制输入长度
    max_len = 20000
    if len(content) > max_len:
        content = content[:max_len] + "\n...[内容已截断]"

    prompt = _LEARN_PROMPT.format(
        agent_name=agent_name,
        agent_role=agent_role or "AI 助手",
        content=content,
    )

    response = model.invoke(prompt)
    raw = response.content if hasattr(response, "content") else str(response)

    # 提取 JSON
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
    if json_match:
        raw = json_match.group(1)

    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except Exception:
            logger.error(f"[LearnSkill] JSON 解析失败: {raw[:500]}")
            return {}


# ============================================================
# 文件操作
# ============================================================

def _read_file_safe(path: str) -> str:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _write_file(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ============================================================
# 主入口
# ============================================================

def run(content: str, **kwargs) -> str:
    """
    Agent 学习技能：从文章 URL 或文本内容中提取知识和行为准则

    Args:
        content: 文章的 URL 或文本内容
    """
    # 从 kwargs 获取 Agent 上下文（由 nodes.py wrapper 注入）
    agent_id = kwargs.get("agent_id", "")
    agent_name = kwargs.get("agent_name", "AI 助手")
    user_id = kwargs.get("user_id", "")
    provider_id = kwargs.get("provider_id", "")
    model_name_cfg = kwargs.get("model_name", "")
    workspace_id = kwargs.get("workspace_id", "")

    if not content or not content.strip():
        return "❌ 请提供要学习的内容（URL 或文本）。"

    # 如果是 URL，自动获取内容
    if _is_url(content.strip()):
        url = content.strip()
        logger.info(f"[LearnSkill] 检测到 URL，正在获取: {url}")
        fetched = _fetch_url(url)
        if not fetched:
            return f"❌ 无法获取 URL 内容: {url}"
        content = fetched
        logger.info(f"[LearnSkill] URL 内容获取成功, 长度={len(content)}")

    logger.info(f"[LearnSkill] Agent={agent_name} 开始学习, 内容长度={len(content)}")

    # 获取 Agent 的角色描述（system prompt 的前 200 字）
    agent_role = ""
    try:
        from src.core.agent_registry import AgentRegistry
        ar = AgentRegistry(user_id)
        config = ar.get_agent(agent_id)
        if config:
            agent_role = (config.get("system_prompt", "") or "")[:200]
    except Exception:
        pass

    # 调用 LLM
    try:
        result = _call_llm(user_id, agent_name, agent_role, content, provider_id, model_name_cfg)
    except Exception as e:
        return f"❌ 学习失败: {e}"

    if not result:
        return "⚠ LLM 返回为空，未能提取有效内容。"

    knowledge = result.get("knowledge_summary", "")
    rules = result.get("behavior_rules", "")
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 确定 Agent 目录
    agent_dir = os.path.join(_DATA_ROOT, user_id, workspace_id, agent_id) if workspace_id \
        else os.path.join(_DATA_ROOT, user_id, agent_id)

    outputs = []

    # --- 1. 知识写入 knowledge_base → 向量化 ---
    if knowledge:
        kb_dir = os.path.join(agent_dir, "knowledge_base")
        # 用时间戳生成文件名
        safe_title = content[:30].replace("\n", " ").replace("/", "_").replace("\\", "_").strip()
        filename = f"学习笔记_{datetime.now().strftime('%Y%m%d_%H%M')}_{safe_title}.md"
        knowledge_file = os.path.join(kb_dir, filename)

        file_content = f"# 学习笔记\n\n> 学习时间: {today_str}\n> Agent: {agent_name}\n\n{knowledge}\n"
        _write_file(knowledge_file, file_content)

        # Ingest 到向量库
        chunks = 0
        try:
            from src.utils.rag_ingestion import RAGIngestion
            rag = RAGIngestion(_DATA_ROOT, workspace_id or user_id, agent_id)
            chunks = rag.ingest_file(knowledge_file)
        except Exception as e:
            logger.warning(f"[LearnSkill] 向量化失败: {e}")

        outputs.append(f"📚 **知识已入库** ({chunks} 个向量块)")

    # --- 2. 行为准则写入 archives/行为标准.md ---
    if rules:
        archives_dir = os.path.join(agent_dir, "archives")
        rules_file = os.path.join(archives_dir, "行为标准.md")
        existing = _read_file_safe(rules_file)

        if existing:
            # 追加新规则
            new_content = existing.rstrip() + f"\n\n## {today_str} 新增准则\n\n{rules}\n"
        else:
            # 首次创建
            new_content = f"# {agent_name} 行为标准\n\n> 此文件由学习技能自动维护。Agent 执行任务时应遵循以下准则。\n\n## {today_str} 初始准则\n\n{rules}\n"

        _write_file(rules_file, new_content)
        outputs.append(f"📏 **行为准则已更新** → `archives/行为标准.md`")

    if not outputs:
        return "⚠ 未从内容中提取到有价值的知识或准则。"

    summary = f"✅ **学习完成！**\n\n" + "\n".join(outputs)

    # 简要展示学到的内容
    if knowledge:
        # 取前 300 字预览
        preview = knowledge[:300] + ("..." if len(knowledge) > 300 else "")
        summary += f"\n\n---\n### 📚 知识摘要\n{preview}"

    if rules:
        summary += f"\n\n### 📏 新行为准则\n{rules}"

    return summary
