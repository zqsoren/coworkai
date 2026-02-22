"""
AgentGraph - LangGraph StateGraph 构建
定义 Agent 的工作流程：Router → Agent → Tool → Approval → End
"""

from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    router_node,
    agent_node,
    tool_node,
    approval_node,
    should_use_tools,
    should_approve,
)


def build_agent_graph() -> StateGraph:
    """
    构建 Agent 工作流图
    
    流程:
    START → router → agent → [tools? → agent] → [approval?] → END
    """
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("router", router_node)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_node("approval", approval_node)

    # 设置入口
    graph.set_entry_point("router")

    # 路由 → Agent
    graph.add_edge("router", "agent")

    # Agent → 条件分支（是否需要工具调用）
    graph.add_conditional_edges(
        "agent",
        should_use_tools,
        {
            "tools": "tools",
            "respond": END,
        },
    )

    # 工具执行后 → 条件分支（是否需要审批，或继续对话）
    graph.add_conditional_edges(
        "tools",
        should_approve,
        {
            "approval": "approval",
            "continue": "agent",   # 工具结果返回给 Agent 继续生成
            "respond": END,
        },
    )

    # 审批 → 结束（审批在 UI 层处理）
    graph.add_edge("approval", END)

    return graph


def create_compiled_graph():
    """创建并编译图，返回可直接 invoke 的 Runnable"""
    graph = build_agent_graph()
    return graph.compile()
