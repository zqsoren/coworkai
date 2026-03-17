"""
MCP Server — 将 AgentOS 市场 Agent 暴露为 MCP 工具供外部平台调用

Tools:
  - list_market_agents: 列出所有已发布的市场 Agent
  - get_agent_info: 获取指定 Agent 的完整元信息
  - chat_with_agent: 与指定 Agent 对话（全能力：含工具/知识库/MCP）
"""

import os
import sys
import json
import contextvars

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse

# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.supabase_client import supabase

# ---- Context var for the authenticated caller ----
mcp_caller_user_id = contextvars.ContextVar("mcp_caller_user_id", default=None)

# ---- MCP Server Instance ----
mcp_server = Server("基石协作")

# ---- SSE Transport (messages endpoint is relative to the mount point) ----
sse_transport = SseServerTransport("/messages/")

# ===========================================================================
# Tool Definitions
# ===========================================================================

@mcp_server.list_tools()
async def list_tools():
    return [
        Tool(
            name="list_market_agents",
            description="列出基石协作市场上所有已发布的智能体。返回每个 Agent 的 id、名称、描述、工具、技能等摘要信息。",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_agent_info",
            description="获取基石协作市场上指定 Agent 的完整元信息，包括系统提示词、工具列表、技能、MCP 服务和知识库。",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "市场 Agent 的 ID（如 market_a1b2c3d4）",
                    }
                },
                "required": ["agent_id"],
            },
        ),
        Tool(
            name="chat_with_agent",
            description="与基石协作平台上的一个已发布智能体对话。Agent 将使用其配置的工具、知识库和 MCP 服务来回答您的问题。",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "市场 Agent 的 ID",
                    },
                    "message": {
                        "type": "string",
                        "description": "发送给 Agent 的消息",
                    },
                },
                "required": ["agent_id", "message"],
            },
        ),
    ]


# ===========================================================================
# Tool Implementations
# ===========================================================================

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "list_market_agents":
        return await _tool_list_market_agents()
    elif name == "get_agent_info":
        return await _tool_get_agent_info(arguments.get("agent_id", ""))
    elif name == "chat_with_agent":
        return await _tool_chat_with_agent(
            arguments.get("agent_id", ""),
            arguments.get("message", ""),
        )
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _tool_list_market_agents():
    """List all published market agents."""
    result = supabase.table("market_agents").select(
        "id, name, description, tools, skills, downloads, rating"
    ).execute()

    agents = result.data or []
    text = json.dumps(agents, ensure_ascii=False, indent=2)
    return [TextContent(type="text", text=text)]


async def _tool_get_agent_info(agent_id: str):
    """Get full metadata of a market agent."""
    if not agent_id:
        return [TextContent(type="text", text="Error: agent_id is required")]

    result = supabase.table("market_agents") \
        .select("*") \
        .eq("id", agent_id) \
        .execute()

    if not result.data:
        return [TextContent(type="text", text=f"Agent '{agent_id}' not found")]

    agent = result.data[0]
    # Remove internal fields
    safe_fields = {
        "id": agent.get("id"),
        "name": agent.get("name"),
        "description": agent.get("description"),
        "system_prompt": agent.get("system_prompt"),
        "tools": agent.get("tools", []),
        "skills": agent.get("skills", []),
        "mcp_servers": [
            {"name": s.get("name"), "description": s.get("description", "")}
            for s in (agent.get("mcp_servers") or [])
        ],
        "knowledge_base": agent.get("knowledge_base", []),
        "downloads": agent.get("downloads", 0),
        "rating": agent.get("rating", 5.0),
    }
    text = json.dumps(safe_fields, ensure_ascii=False, indent=2)
    return [TextContent(type="text", text=text)]


async def _tool_chat_with_agent(agent_id: str, message: str):
    """Chat with a market agent using the full LangGraph pipeline."""
    if not agent_id or not message:
        return [TextContent(type="text", text="Error: agent_id and message are required")]

    # 1. Fetch market agent data
    result = supabase.table("market_agents") \
        .select("*") \
        .eq("id", agent_id) \
        .execute()

    if not result.data:
        return [TextContent(type="text", text=f"Agent '{agent_id}' not found")]

    agent_data = result.data[0]
    publisher_id = agent_data.get("publisher_id", "")

    # 2. Build agent_config compatible with the LangGraph pipeline
    agent_config = {
        "id": agent_id,
        "name": agent_data.get("name", "Market Agent"),
        "system_prompt": agent_data.get("system_prompt", "你是一个 AI 助手。"),
        "tools": agent_data.get("tools", []),
        "skills": agent_data.get("skills", []),
        "mcp_servers": agent_data.get("mcp_servers", []),
        "provider_id": agent_data.get("provider_id", ""),
        "model_name": agent_data.get("model_name", ""),
        "persona_mode": "efficient",
        "_user_id": publisher_id,
        "_workspace_id": "",
    }

    # 3. Run via LangGraph (same pipeline as /api/chat/invoke)
    try:
        from langchain_core.messages import HumanMessage, AIMessage
        from src.graph.agent_graph import create_compiled_graph

        initial_state = {
            "messages": [HumanMessage(content=message)],
            "current_agent": agent_id,
            "current_workspace": "",
            "agent_config": agent_config,
            "pending_changes": [],
            "context": "",
            "needs_approval": False,
            "user_id": publisher_id,
        }

        graph = create_compiled_graph()
        result = graph.invoke(initial_state)

        # Extract final response
        messages = result.get("messages", [])
        response_text = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                content = msg.content
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            parts.append(item["text"])
                        elif isinstance(item, str):
                            parts.append(item)
                    response_text = "\n".join(parts)
                else:
                    response_text = str(content)
                break

        if not response_text:
            response_text = "Agent 未返回有效回复。"

        return [TextContent(type="text", text=response_text)]

    except Exception as e:
        import traceback
        traceback.print_exc()
        return [TextContent(type="text", text=f"Agent 执行失败: {str(e)}")]


# ===========================================================================
# SSE Endpoint Handler (with API Key auth)
# ===========================================================================

async def _validate_api_key(request) -> str | None:
    """Validate API Key from Authorization header. Returns user_id or None."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer ak_"):
        return None

    api_key = auth_header[7:]  # Strip "Bearer "
    try:
        result = supabase.table("api_keys") \
            .select("user_id") \
            .eq("key", api_key) \
            .execute()

        if result.data:
            # Update last_used_at
            from datetime import datetime
            supabase.table("api_keys") \
                .update({"last_used_at": datetime.now().isoformat()}) \
                .eq("key", api_key) \
                .execute()
            return result.data[0]["user_id"]
    except Exception as e:
        print(f"[MCP] API Key validation error: {e}")

    return None


async def handle_sse(request):
    """SSE endpoint — validates API Key then starts MCP session."""
    user_id = await _validate_api_key(request)
    if not user_id:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid or missing API Key. Use 'Authorization: Bearer ak_xxxxx' header."},
        )

    mcp_caller_user_id.set(user_id)

    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options(),
        )


# ===========================================================================
# Starlette App to mount on FastAPI
# ===========================================================================

mcp_app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ],
)
