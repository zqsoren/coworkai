"""
MCP (Model Context Protocol) 模块
提供 MCP Server 连接、工具发现和调用能力。
"""

from .adapter import (
    MCPManager,
    MCPServerConfig,
    MCPServerStdio,
    MCPServerSSE,
    MCPServerHTTP,
    MCPTransportType,
    MCPTool,
    get_mcp_manager,
    init_mcp_servers,
)

__all__ = [
    "MCPManager",
    "MCPServerConfig",
    "MCPServerStdio",
    "MCPServerSSE",
    "MCPServerHTTP",
    "MCPTransportType",
    "MCPTool",
    "get_mcp_manager",
    "init_mcp_servers",
]
