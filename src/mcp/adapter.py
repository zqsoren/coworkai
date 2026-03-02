"""
MCP Adapter - Model Context Protocol 适配器
将 MCP Server 的工具转换为 LangChain 工具，供 Agent 使用。
支持两种传输模式：
1. stdio - 通过子进程标准输入输出通信（本地 MCP Server）
2. SSE - 通过 Server-Sent Events 连接远程 MCP Server
"""

import asyncio
import json
import os
import shutil
import aiohttp
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class MCPTransportType(Enum):
    """MCP 传输类型"""
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


@dataclass
class MCPServerConfig:
    """MCP Server 配置"""
    id: str
    name: str
    transport: MCPTransportType = MCPTransportType.STDIO
    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    url: str = ""
    api_key: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "MCPServerConfig":
        transport_str = data.get("transport", "stdio").lower()
        transport = MCPTransportType(transport_str) if transport_str in [t.value for t in MCPTransportType] else MCPTransportType.STDIO
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            transport=transport,
            command=data.get("command", ""),
            args=data.get("args", []),
            env=data.get("env", {}),
            url=data.get("url", ""),
            api_key=data.get("api_key", ""),
            headers=data.get("headers", {}),
            description=data.get("description", ""),
            enabled=data.get("enabled", True)
        )


class MCPTool(BaseTool):
    """MCP 工具包装器，将 MCP Server 的工具转换为 LangChain 工具"""
    
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    mcp_server_name: str = Field(..., description="所属 MCP Server 名称")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="输入参数 Schema")
    _mcp_manager: Any = None
    
    def __init__(self, name: str, description: str, mcp_server_name: str, 
                 input_schema: Dict[str, Any], mcp_manager: Any, **kwargs):
        super().__init__(
            name=name,
            description=description,
            mcp_server_name=mcp_server_name,
            input_schema=input_schema,
            **kwargs
        )
        self._mcp_manager = mcp_manager
    
    def _run(self, *args, **kwargs) -> str:
        """同步执行（通过 asyncio.run）"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._arun(*args, **kwargs))
                    return future.result()
            else:
                return asyncio.run(self._arun(*args, **kwargs))
        except Exception as e:
            return f"工具执行错误: {str(e)}"
    
    async def _arun(self, *args, **kwargs) -> str:
        """异步执行"""
        if not self._mcp_manager:
            return "错误: MCP Manager 未初始化"
        
        try:
            result = await self._mcp_manager.call_tool(
                self.mcp_server_name,
                self.name,
                kwargs
            )
            return result
        except Exception as e:
            return f"工具执行错误: {str(e)}"


class MCPServerStdio:
    """MCP Server stdio 模式 - 通过子进程通信"""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: Optional[asyncio.subprocess.Process] = None
        self.tools: List[Dict[str, Any]] = []
        self._initialized = False
        self._request_id = 0
    
    async def start(self) -> bool:
        """启动 MCP Server 进程"""
        if self.process:
            return True
        
        try:
            env = os.environ.copy()
            env.update(self.config.env)
            
            if not shutil.which(self.config.command):
                print(f"[MCP-stdio] 命令不存在: {self.config.command}")
                return False
            
            self.process = await asyncio.create_subprocess_exec(
                self.config.command,
                *self.config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            await self._initialize()
            return self._initialized
        except Exception as e:
            print(f"[MCP-stdio] 启动失败: {e}")
            return False
    
    async def stop(self):
        """停止 MCP Server 进程"""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception:
                pass
            finally:
                self.process = None
                self._initialized = False
    
    async def _send_request(self, method: str, params: Dict = None) -> Optional[Dict]:
        """发送 JSON-RPC 请求"""
        if not self.process or not self.process.stdin:
            return None
        
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {}
        }
        
        try:
            message = json.dumps(request) + "\n"
            self.process.stdin.write(message.encode())
            await self.process.stdin.drain()
            
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=30.0
            )
            
            if response_line:
                response = json.loads(response_line.decode())
                return response
        except asyncio.TimeoutError:
            print(f"[MCP-stdio] 请求超时: {method}")
        except Exception as e:
            print(f"[MCP-stdio] 请求错误: {e}")
        
        return None
    
    async def _initialize(self) -> bool:
        """初始化 MCP 连接"""
        response = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "AgentOS",
                "version": "1.0.0"
            }
        })
        
        if response and "result" in response:
            await self._send_request("notifications/initialized")
            self._initialized = True
            await self._load_tools()
            return True
        
        return False
    
    async def _load_tools(self):
        """加载 MCP Server 提供的工具列表"""
        response = await self._send_request("tools/list")
        if response and "result" in response:
            self.tools = response["result"].get("tools", [])
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> str:
        """调用 MCP 工具"""
        response = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        if response:
            if "result" in response:
                content = response["result"].get("content", [])
                if isinstance(content, list):
                    texts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            texts.append(item.get("text", ""))
                    return "\n".join(texts)
                return str(content)
            elif "error" in response:
                return f"错误: {response['error'].get('message', 'Unknown error')}"
        
        return "错误: 无响应"


class MCPServerSSE:
    """MCP Server SSE 模式 - 通过 Server-Sent Events 连接远程服务"""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.tools: List[Dict[str, Any]] = []
        self._initialized = False
        self._request_id = 0
        self._session: Optional[aiohttp.ClientSession] = None
        self._endpoint: str = ""
    
    async def start(self) -> bool:
        """连接 MCP SSE 服务"""
        try:
            if not self.config.url:
                print("[MCP-SSE] 未配置 URL")
                return False
            
            self._session = aiohttp.ClientSession()
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            }
            
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            headers.update(self.config.headers)
            
            await self._initialize(headers)
            return self._initialized
        except Exception as e:
            print(f"[MCP-SSE] 连接失败: {e}")
            return False
    
    async def stop(self):
        """断开连接"""
        if self._session:
            try:
                await self._session.close()
            except Exception:
                pass
            finally:
                self._session = None
                self._initialized = False
    
    async def _send_request(self, method: str, params: Dict = None, headers: Dict = None) -> Optional[Dict]:
        """发送 JSON-RPC 请求"""
        if not self._session:
            return None
        
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {}
        }
        
        try:
            request_headers = {
                "Content-Type": "application/json",
            }
            if self.config.api_key:
                request_headers["Authorization"] = f"Bearer {self.config.api_key}"
            if headers:
                request_headers.update(headers)
            
            url = self._endpoint if self._endpoint else self.config.url
            
            async with self._session.post(
                url,
                json=request,
                headers=request_headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type", "")
                    
                    if "text/event-stream" in content_type:
                        result = await self._parse_sse_response(response)
                        return result
                    else:
                        return await response.json()
                else:
                    text = await response.text()
                    print(f"[MCP-SSE] 请求失败 ({response.status}): {text[:200]}")
                    return {"error": {"message": f"HTTP {response.status}: {text[:100]}"}}
                    
        except asyncio.TimeoutError:
            print(f"[MCP-SSE] 请求超时: {method}")
        except Exception as e:
            print(f"[MCP-SSE] 请求错误: {e}")
        
        return None
    
    async def _parse_sse_response(self, response) -> Optional[Dict]:
        """解析 SSE 响应"""
        buffer = ""
        async for line in response.content:
            line = line.decode("utf-8").strip()
            if not line:
                continue
            
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str:
                    try:
                        return json.loads(data_str)
                    except json.JSONDecodeError:
                        buffer += data_str
        
        if buffer:
            try:
                return json.loads(buffer)
            except json.JSONDecodeError:
                pass
        
        return None
    
    async def _initialize(self, headers: Dict = None) -> bool:
        """初始化 MCP 连接"""
        response = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "AgentOS",
                "version": "1.0.0"
            }
        }, headers)
        
        if response and "result" in response:
            result = response["result"]
            
            if "capabilities" in result:
                self._endpoint = self.config.url
            
            self._initialized = True
            await self._load_tools()
            return True
        
        return False
    
    async def _load_tools(self):
        """加载 MCP Server 提供的工具列表"""
        response = await self._send_request("tools/list")
        if response and "result" in response:
            self.tools = response["result"].get("tools", [])
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> str:
        """调用 MCP 工具"""
        response = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        if response:
            if "result" in response:
                content = response["result"].get("content", [])
                if isinstance(content, list):
                    texts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            texts.append(item.get("text", ""))
                    return "\n".join(texts)
                return str(content)
            elif "error" in response:
                return f"错误: {response['error'].get('message', 'Unknown error')}"
        
        return "错误: 无响应"


class MCPServerHTTP:
    """MCP Server HTTP 模式 - 通过 HTTP 请求连接远程服务"""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.tools: List[Dict[str, Any]] = []
        self._initialized = False
        self._request_id = 0
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def start(self) -> bool:
        """连接 MCP HTTP 服务"""
        try:
            if not self.config.url:
                print("[MCP-HTTP] 未配置 URL")
                return False
            
            self._session = aiohttp.ClientSession()
            await self._initialize()
            return self._initialized
        except Exception as e:
            print(f"[MCP-HTTP] 连接失败: {e}")
            return False
    
    async def stop(self):
        """断开连接"""
        if self._session:
            try:
                await self._session.close()
            except Exception:
                pass
            finally:
                self._session = None
                self._initialized = False
    
    async def _send_request(self, method: str, params: Dict = None) -> Optional[Dict]:
        """发送 JSON-RPC 请求"""
        if not self._session:
            return None
        
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {}
        }
        
        try:
            headers = {
                "Content-Type": "application/json",
            }
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            headers.update(self.config.headers)
            
            async with self._session.post(
                self.config.url,
                json=request,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    print(f"[MCP-HTTP] 请求失败 ({response.status}): {text[:200]}")
                    return {"error": {"message": f"HTTP {response.status}: {text[:100]}"}}
                    
        except asyncio.TimeoutError:
            print(f"[MCP-HTTP] 请求超时: {method}")
        except Exception as e:
            print(f"[MCP-HTTP] 请求错误: {e}")
        
        return None
    
    async def _initialize(self) -> bool:
        """初始化 MCP 连接"""
        response = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "AgentOS",
                "version": "1.0.0"
            }
        })
        
        if response and "result" in response:
            self._initialized = True
            await self._load_tools()
            return True
        
        return False
    
    async def _load_tools(self):
        """加载 MCP Server 提供的工具列表"""
        response = await self._send_request("tools/list")
        if response and "result" in response:
            self.tools = response["result"].get("tools", [])
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> str:
        """调用 MCP 工具"""
        response = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        if response:
            if "result" in response:
                content = response["result"].get("content", [])
                if isinstance(content, list):
                    texts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            texts.append(item.get("text", ""))
                    return "\n".join(texts)
                return str(content)
            elif "error" in response:
                return f"错误: {response['error'].get('message', 'Unknown error')}"
        
        return "错误: 无响应"


class MCPManager:
    """MCP 管理器 - 管理所有 MCP Server 连接和工具"""
    
    def __init__(self):
        self.servers: Dict[str, Any] = {}
        self._tools: List[MCPTool] = []
    
    async def add_server(self, config: MCPServerConfig) -> bool:
        """添加并启动 MCP Server"""
        if config.name in self.servers:
            return True
        
        server = self._create_server(config)
        if not server:
            print(f"[MCP] 不支持的传输类型: {config.transport}")
            return False
        
        success = await server.start()
        
        if success:
            self.servers[config.name] = server
            await self._register_tools(server, config.name)
            return True
        
        return False
    
    def _create_server(self, config: MCPServerConfig):
        """根据传输类型创建对应的 Server 实例"""
        if config.transport == MCPTransportType.STDIO:
            return MCPServerStdio(config)
        elif config.transport == MCPTransportType.SSE:
            return MCPServerSSE(config)
        elif config.transport == MCPTransportType.HTTP:
            return MCPServerHTTP(config)
        return None
    
    async def remove_server(self, name: str):
        """移除 MCP Server"""
        if name in self.servers:
            await self.servers[name].stop()
            del self.servers[name]
            self._tools = [t for t in self._tools if t.mcp_server_name != name]
    
    async def _register_tools(self, server: Any, server_name: str):
        """注册 MCP Server 的工具"""
        for tool_info in server.tools:
            tool = MCPTool(
                name=tool_info.get("name", ""),
                description=tool_info.get("description", ""),
                mcp_server_name=server_name,
                input_schema=tool_info.get("inputSchema", {}),
                mcp_manager=self
            )
            self._tools.append(tool)
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict) -> str:
        """调用 MCP 工具"""
        if server_name not in self.servers:
            return f"错误: MCP Server '{server_name}' 未连接"
        
        server = self.servers[server_name]
        return await server.call_tool(tool_name, arguments)
    
    def get_tools(self) -> List[MCPTool]:
        """获取所有 MCP 工具"""
        return self._tools.copy()
    
    def get_langchain_tools(self) -> List[BaseTool]:
        """获取 LangChain 格式的工具列表"""
        return self._tools.copy()
    
    async def stop_all(self):
        """停止所有 MCP Server"""
        for name in list(self.servers.keys()):
            await self.remove_server(name)
    
    @property
    def status(self) -> Dict[str, Any]:
        """获取 MCP 状态"""
        return {
            "servers": {
                name: {
                    "tools_count": len(server.tools),
                    "initialized": server._initialized,
                    "transport": server.config.transport.value if hasattr(server, 'config') else "unknown"
                }
                for name, server in self.servers.items()
            },
            "total_tools": len(self._tools)
        }


_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """获取全局 MCP Manager 实例"""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager


async def init_mcp_servers(configs: List[Dict[str, Any]]) -> MCPManager:
    """初始化 MCP Servers"""
    manager = get_mcp_manager()
    
    for config_data in configs:
        config = MCPServerConfig.from_dict(config_data)
        if config.enabled:
            await manager.add_server(config)
    
    return manager
