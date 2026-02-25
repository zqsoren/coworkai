"""
AgentState - LangGraph 图状态定义
定义整个 Agent 工作流的共享状态。
"""

from typing import Annotated, Optional, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph StateGraph 的状态定义"""

    # 对话消息列表（LangGraph 内置的消息合并策略）
    messages: Annotated[list, add_messages]

    # 当前活跃的 Agent ID
    current_agent: str

    # 当前工作区 ID
    current_workspace: str

    # Agent 的配置信息
    agent_config: dict

    # 待审批的文件变更请求列表
    pending_changes: list[dict]

    # 最近一次审批状态: None / "approved" / "rejected"
    approval_status: Optional[str]

    # Agent 的项目上下文（从 active/ 读取）
    context: str

    # @mention 路由信息
    mention_target: Optional[str]
    mention_summary: Optional[str]

    # 是否需要用户审批
    needs_approval: bool

    # 最终响应（用于输出）
    final_response: Optional[str]

    # LLM 配置文件路径（用户级别）
    llm_config_path: Optional[str]
