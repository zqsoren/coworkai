"""
Graph Nodes - LangGraph 各节点实现
Router → Agent → Tool → Approval → End
"""

import json
import re
from typing import Optional

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .state import AgentState


def _get_llm(agent_config: dict):
    """根据 Agent 配置获取对应的 LLM 实例"""
    from src.core.llm_manager import LLMManager
    
    mgr = LLMManager()
    
    # 1. 优先使用 provider_id + model_name
    provider_id = agent_config.get("provider_id")
    model_name = agent_config.get("model_name")
    
    # 获取对应的 Provider
    if provider_id:
        provider = mgr.get_provider(provider_id)
        if provider and (not model_name or str(model_name).strip() == ""):
            # 如果 Agent 没有显式指定模型，使用 Provider 中配置的第一个模型
            if provider.models and len(provider.models) > 0:
                model_name = provider.models[0]
    
    # 2. 兼容旧版 model_tier
    if not provider_id or not model_name:
        tier = agent_config.get("model_tier", "tier1")
        # 简单映射 fallback
        # 理想情况下应该读取旧的 secrets["models"]，但为了架构整洁，我们直接 default 到 gemini/openai
        if tier == "tier1":
            provider_id = "gemini_default" 
            model_name = "gemini-1.5-pro"
        else:
            provider_id = "gemini_default"
            model_name = "gemini-2.0-flash"
            
    try:
        return mgr.get_model(provider_id, model_name)
    except Exception as e:
        # Fallback if specific provider/model fails or doesn't exist
        print(f"Error initializing LLM ({provider_id}/{model_name}): {e}")
        # Try a safe default
        try:
            return mgr.get_model("gemini_default", "gemini-2.0-flash")
        except:
            raise ValueError(f"无法初始化 LLM，请检查设置: {e}")


def _get_tools(agent_config: dict, base_path: str = None) -> list:
    """根据 Agent 配置获取工具和技能列表
    
    Args:
        agent_config: Agent 配置字典
        base_path: Agent 根目录 (用于上下文感知工具)，如果为 None 则使用全局工具
    """
    from langchain_core.tools import StructuredTool
    from src.tools.file_tools import FILE_TOOLS, create_agent_file_tools, _file_manager
    from src.tools.web_tools import WEB_TOOLS
    from src.tools.code_tools import CODE_TOOLS
    from src.tools.browser_tools import BROWSER_TOOLS
    from src.tools.meta_tools import META_TOOLS
    from src.skills.skill_loader import SkillLoader
    import os

    # 1. 收集 L1 Tools
    # 如果提供了 base_path 且 _file_manager 已初始化，则使用上下文感知的 File Tools
    if base_path and _file_manager:
        file_tools = create_agent_file_tools(base_path, _file_manager)
    else:
        file_tools = FILE_TOOLS

    all_tools = {t.name: t for t in file_tools + WEB_TOOLS + CODE_TOOLS + BROWSER_TOOLS + META_TOOLS}

    # 2. 收集 L2/L3 Skills
    # 这里假设 custom_skills 在项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sl = SkillLoader(os.path.join(project_root, "custom_skills"))
    sl.scan_and_load()

    for name, skill_data in sl.skills.items():
        # 将技能函数包装为 LangChain Tool
        # 注意: 需要捕获 closure 变量
        def create_wrapper(run_func):
            def wrapper(**kwargs):
                return run_func(**kwargs)
            return wrapper
        
        wrapper_func = create_wrapper(skill_data["run"])
        
        tool = StructuredTool.from_function(
            func=wrapper_func,
            name=skill_data["name"],
            description=skill_data["description"]
        )
        all_tools[skill_data["name"]] = tool

    # 3. 过滤
    requested_tools = agent_config.get("tools", [])
    requested_skills = agent_config.get("skills", [])
    
    final_tools = []
    # 合并 tools 和 skills 列表
    for name in requested_tools + requested_skills:
        if name in all_tools:
            final_tools.append(all_tools[name])
            
    return final_tools


def router_node(state: AgentState) -> dict:
    """
    路由节点：解析用户输入，检测 @mention，决定路由目标。
    """
    messages = state.get("messages", [])
    if not messages:
        return state

    last_msg = messages[-1]
    content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    # 检测 @mention
    mention_match = re.search(r"@(\w+)", content)
    if mention_match:
        target = mention_match.group(1)
        # 上下文切片：提取最近 3 条消息作为摘要
        recent = messages[-4:-1] if len(messages) > 3 else messages[:-1]
        summary_parts = []
        for msg in recent:
            role = "用户" if isinstance(msg, HumanMessage) else "助手"
            msg_content = msg.content if hasattr(msg, "content") else str(msg)
            summary_parts.append(f"{role}: {msg_content[:200]}")
        mention_summary = "\n".join(summary_parts) if summary_parts else "无前文上下文"

        return {
            "mention_target": target,
            "mention_summary": mention_summary,
        }

    return {
        "mention_target": None,
        "mention_summary": None,
    }


def agent_node(state: AgentState) -> dict:
    """
    Agent 节点：调用 LLM，绑定工具。
    """
    agent_config = state.get("agent_config", {})
    context = state.get("context", "")
    messages = state.get("messages", [])

    try:
        llm = _get_llm(agent_config)
    except ValueError as e:
        return {
            "messages": [AIMessage(content=f"⚠️ 配置错误: {str(e)}")],
            "needs_approval": False,
        }

    # 构建 system prompt
    system_prompt = agent_config.get("system_prompt", "你是一个 AI 助手。")
    if context:
        system_prompt += f"\n\n---\n{context}"


    # Agentic RAG: 提示词增强
    system_prompt += """

你是一个高级 AI 助手。你可以使用 `search_knowledge_base` 工具。
**重要提示**：你默认不知道用户数据库中的内容。如果用户询问特定的 ID、某份文档或领域特定的知识，你必须首先调用 `search_knowledge_base` 工具来收集信息。
绝对不要瞎猜。请仔细分析用户的请求，生成精准的搜索查询词，调用该工具，然后使用返回的真实信息来回答用户。
"""

    # 添加 @mention 上下文
    mention_summary = state.get("mention_summary")
    if mention_summary:
        system_prompt += f"\n\n---\n## 前文上下文（由主对话传递）\n{mention_summary}"

    # 获取工具
    import os
    base_path = None
    rag_tool = None
    
    curr_ws = state.get("current_workspace")
    curr_agent = state.get("current_agent")
    
    if curr_ws and curr_agent:
        base_path = os.path.join(curr_ws, curr_agent)
        
        # 🆕 Agentic RAG: Bind Search Tool
        try:
            from src.utils.rag_ingestion import RAGIngestion
            from src.tools.rag_tools import get_rag_tool
            
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_root = os.path.join(project_root, "data")
            
            # Check if agent dir exists to avoid errors
            if os.path.exists(os.path.join(data_root, curr_ws, curr_agent)):
                 rag = RAGIngestion(data_root, curr_ws, curr_agent)
                 rag_tool = get_rag_tool(rag)
        except Exception as e:
            print(f"[nodes.py] RAG Tool Init Failed: {e}")

    tools = _get_tools(agent_config, base_path)
    
    if rag_tool:
        tools.append(rag_tool)

    # 绑定工具到 LLM
    if tools:
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm

    # 构建消息列表
    chat_messages = [SystemMessage(content=system_prompt)] + list(messages)

    # 调用 LLM
    try:
        response = llm_with_tools.invoke(chat_messages)
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"⚠️ LLM 调用失败: {str(e)}")],
            "needs_approval": False,
        }

    # 检查是否有工具调用
    has_tool_calls = hasattr(response, "tool_calls") and response.tool_calls
    
    return {
        "messages": [response],
        "needs_approval": False,
    }


def tool_node(state: AgentState) -> dict:
    """
    工具执行节点：执行 LLM 返回的工具调用。
    """
    from langchain_core.messages import ToolMessage

    messages = state.get("messages", [])
    agent_config = state.get("agent_config", {})
    last_msg = messages[-1] if messages else None

    if not last_msg or not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
        return {"messages": [], "pending_changes": [], "needs_approval": False}

    tools = _get_tools(agent_config) # 这里的 tools 可能没有 context?
    # Tool Node 也要重新获取 context aware tools 吗？
    # 是的，因为 StructuredTool 闭包了 context。
    base_path = None
    curr_ws = state.get("current_workspace")
    curr_agent = state.get("current_agent")
    if curr_ws and curr_agent:
        import os
        base_path = os.path.join(curr_ws, curr_agent)

    tools = _get_tools(agent_config, base_path)
    tool_map = {t.name: t for t in tools}

    new_messages = []
    pending_changes = list(state.get("pending_changes", []))
    needs_approval = False

    for call in last_msg.tool_calls:
        tool_name = call["name"]
        tool_args = call["args"]

        if tool_name in tool_map:
            try:
                result = tool_map[tool_name].invoke(tool_args)

                # 检查结果是否包含 ChangeRequest
                if isinstance(result, str) and '"type": "change_request"' in result:
                    try:
                        cr_data = json.loads(result)
                        if cr_data.get("type") == "change_request":
                            pending_changes.append(cr_data)
                            needs_approval = True
                            result = f"📋 已生成文件变更请求: {cr_data.get('file_path', '未知')}\n请在右侧审批面板中查看差异并决定是否应用。"
                    except json.JSONDecodeError:
                        pass

                new_messages.append(
                    ToolMessage(content=str(result), tool_call_id=call["id"])
                )

                # Flight Recorder: 记录工具调用
                _log_tool_call(state, tool_name, tool_args, "Success")

            except Exception as e:
                new_messages.append(
                    ToolMessage(content=f"工具执行错误: {str(e)}", tool_call_id=call["id"])
                )
                _log_tool_call(state, tool_name, tool_args, f"Error: {e}")
        else:
            new_messages.append(
                ToolMessage(content=f"工具 '{tool_name}' 不可用。", tool_call_id=call["id"])
            )

    return {
        "messages": new_messages,
        "pending_changes": pending_changes,
        "needs_approval": needs_approval,
    }


def approval_node(state: AgentState) -> dict:
    """
    审批节点：等待用户对文件变更的审批。
    实际审批通过 Streamlit UI 的回调处理。
    此节点的作用是标记流程进入审批等待状态。
    """
    return {
        "approval_status": "waiting",
    }


# ----- 条件边 (Conditional Edges) -----

def should_use_tools(state: AgentState) -> str:
    """判断是否需要执行工具调用"""
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            return "tools"
    return "respond"


def should_approve(state: AgentState) -> str:
    """判断是否需要审批"""
    if state.get("needs_approval", False):
        return "approval"
    
    # 工具执行后，还需要让 LLM 生成最终回复
    messages = state.get("messages", [])
    if messages:
        from langchain_core.messages import ToolMessage
        if isinstance(messages[-1], ToolMessage):
            return "continue"
    
    return "respond"


def after_approval(state: AgentState) -> str:
    """审批后的分支"""
    status = state.get("approval_status", "")
    if status == "approved":
        return "continue"
    elif status == "rejected":
        return "respond"
    return "wait"


# ----- Flight Recorder Helper -----

def _log_tool_call(state: dict, tool_name: str, args: dict, status: str):
    """记录工具调用到 ProjectLogger (fail-safe)"""
    try:
        from src.core.project_logger import ProjectLogger
        import os
        ws = state.get("current_workspace")
        agent = state.get("current_agent")
        if ws and agent:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            logger = ProjectLogger(os.path.join(project_root, "data"), ws, agent)
            logger.log_tool_call(tool_name, args, status)
    except Exception:
        pass  # 日志失败不中断主流程
