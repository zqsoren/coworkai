"""
Meta Tools - Meta-Agent 工具集
暴露 MetaAgent 的 Builder + Observer 能力给 LangGraph。
"""

from langchain_core.tools import tool
from src.core.meta_agent import MetaAgent

_meta_agent: MetaAgent = None

def init_meta_tools(meta_agent: MetaAgent):
    global _meta_agent
    _meta_agent = meta_agent


# ================================================================
# Builder Tools
# ================================================================

@tool
def create_new_agent(agent_id: str, name: str, role_description: str,
                     tools: list[str] = None, skills: list[str] = None) -> str:
    """
    创建一个新的 AI 助手 (Agent)。
    
    Args:
        agent_id: Agent 的唯一标识 ID (英文, e.g. "writer", "coder")
        name: Agent 的显示名称 (e.g. "文案大师")
        role_description: 角色的详细描述，将作为 System Prompt 的一部分
        tools: 需要使用的工具列表 (e.g. ["read_file", "google_search"])
        skills: 需要使用的技能列表 (e.g. ["deep_research"])
    """
    if not _meta_agent:
        return "错误: MetaAgent 未初始化。"

    import streamlit as st
    workspace_id = st.session_state.get("current_workspace", "workspace_default")
    
    try:
        return _meta_agent.create_agent(
            workspace_id=workspace_id,
            agent_id=agent_id,
            name=name,
            role_desc=role_description,
            tools=tools,
            skills=skills
        )
    except Exception as e:
        return f"创建失败: {str(e)}"


@tool
def list_available_agents() -> str:
    """列出系统中所有可用的 Agent"""
    if not _meta_agent:
        return "错误: MetaAgent 未初始化。"
    
    agents = _meta_agent.registry.list_agents()
    lines = ["系统中的 Agent 列表:"]
    for a in agents:
        lines.append(f"- [{a['id']}] {a.get('name')} (Tags: {', '.join(a.get('tags', []))})")
    return "\n".join(lines)


# ================================================================
# Observer Tools
# ================================================================

@tool
def list_all_files_recursive(max_depth: int = 5) -> str:
    """
    递归列出当前工作区内所有 Agent 的所有文件。
    用于全局文件盘点和发现。

    Args:
        max_depth: 最大递归深度，默认5层
    """
    if not _meta_agent:
        return "错误: MetaAgent 未初始化。"

    import streamlit as st
    workspace_id = st.session_state.get("current_workspace", "workspace_default")

    files = _meta_agent.list_all_files(workspace_id, max_depth)
    if not files:
        return "工作区内无文件。"

    # 按 agent 分组
    by_agent = {}
    for f in files:
        agent = f["agent"]
        by_agent.setdefault(agent, []).append(f)

    lines = [f"📂 工作区文件总览 ({len(files)} 个文件):\n"]
    for agent, agent_files in by_agent.items():
        lines.append(f"\n### {agent}")
        for f in agent_files[:20]:  # 每个 agent 最多显示20个
            size_kb = f["size"] / 1024
            lines.append(f"  - {f['path']} ({size_kb:.1f} KB)")
        if len(agent_files) > 20:
            lines.append(f"  ... 还有 {len(agent_files) - 20} 个文件")

    return "\n".join(lines)


@tool
def read_any_file(file_path: str) -> str:
    """
    读取 data/ 目录下任意文件的内容（Meta-Agent 特权）。
    用于跨 Agent 阅读文件，但不能修改。

    Args:
        file_path: 文件的相对路径 (基于 data/)，例如 "workspace_default/agent_writer/context/active/draft.md"
    """
    if not _meta_agent:
        return "错误: MetaAgent 未初始化。"

    try:
        return _meta_agent.read_any_file(file_path)
    except FileNotFoundError as e:
        return f"文件不存在: {e}"
    except IsADirectoryError as e:
        return f"路径是目录: {e}"
    except Exception as e:
        return f"读取失败: {e}"


@tool
def search_files_by_keyword(keyword: str) -> str:
    """
    在当前工作区的所有文件中搜索关键词。
    返回匹配的文件列表和所在行。

    Args:
        keyword: 要搜索的关键词
    """
    if not _meta_agent:
        return "错误: MetaAgent 未初始化。"

    import streamlit as st
    workspace_id = st.session_state.get("current_workspace", "workspace_default")

    results = _meta_agent.search_files(workspace_id, keyword)
    if not results:
        return f"未找到包含 '{keyword}' 的文件。"

    lines = [f"🔍 搜索 '{keyword}' — 找到 {len(results)} 个文件:\n"]
    for r in results[:10]:
        lines.append(f"\n**{r['file']}** (Agent: {r['agent']}, {r['total_matches']} 处匹配)")
        for line_no, line_text in r["matches"]:
            lines.append(f"  L{line_no}: {line_text[:100]}")

    return "\n".join(lines)


@tool
def suggest_delegation_to_agent(target_agent_id: str, task_description: str) -> str:
    """
    建议将任务委派给另一个 Agent。
    会在聊天中生成一个"切换到 @Agent"的建议按钮。

    Args:
        target_agent_id: 目标 Agent 的 ID
        task_description: 建议该 Agent 执行的任务描述
    """
    if not _meta_agent:
        return "错误: MetaAgent 未初始化。"

    import streamlit as st

    suggestion = _meta_agent.suggest_delegation(target_agent_id, task_description)

    # 将委派建议存入 session_state，供 chat UI 渲染按钮
    if "delegation_suggestions" not in st.session_state:
        st.session_state["delegation_suggestions"] = []
    st.session_state["delegation_suggestions"].append(suggestion)

    return suggestion["message"]


# All tools
META_TOOLS = [
    create_new_agent,
    list_available_agents,
    list_all_files_recursive,
    read_any_file,
    search_files_by_keyword,
    suggest_delegation_to_agent,
]
