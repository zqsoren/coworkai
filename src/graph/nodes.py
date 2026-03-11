"""
Graph Nodes - LangGraph 各节点实现
Router → Agent → Tool → Approval → End
"""

import json
import re
from typing import Optional

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .state import AgentState


def _get_llm(agent_config: dict, user_id: str = None):
    """根据 Agent 配置获取对应的 LLM 实例"""
    from src.core.llm_manager import LLMManager
    
    mgr = LLMManager(user_id) if user_id else LLMManager("__global__")
    
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


# 系统默认工具 - 所有 Agent 自动拥有，无需手动配置
SYSTEM_DEFAULT_TOOLS = [
    "read_file", "write_file", "list_directory", "move_file", "get_file_diff",
    "fetch_url_content", "python_repl", "get_current_time",
    "take_screenshot", "open_browser", "get_page_text", "page_screenshot",
    "scroll_page", "check_login_status", "wait_for_login", "close_browser",
    "search_files_by_keyword", "shell_command",
    "create_scheduled_task", "list_scheduled_tasks", "delete_scheduled_task",
]

# Meta-Agent 专属默认工具 - 仅超级助手自动拥有
META_AGENT_DEFAULT_TOOLS = [
    "list_all_files_recursive", "read_any_file", "list_available_agents",
]

def _get_tools(agent_config: dict, base_path: str = None) -> list:
    """根据 Agent 配置获取工具和技能列表
    
    Args:
        agent_config: Agent 配置字典
        base_path: Agent 根目录 (用于上下文感知工具)，如果为 None 则使用全局工具
    """
    from langchain_core.tools import StructuredTool
    from src.tools.file_tools import FILE_TOOLS, create_agent_file_tools
    from src.tools.web_tools import WEB_TOOLS
    from src.tools.code_tools import CODE_TOOLS
    from src.tools.browser_tools import BROWSER_TOOLS
    from src.tools.playwright_tools import PLAYWRIGHT_TOOLS
    from src.tools.meta_tools import META_TOOLS, init_meta_tools, set_meta_context
    from src.tools.stock_tools import STOCK_TOOLS
    from src.tools.schedule_tools import SCHEDULE_TOOLS, init_schedule_context
    from src.skills.skill_loader import SkillLoader
    from src.core.file_manager import FileManager
    import os

    # 初始化定时任务工具上下文
    user_id = agent_config.get("_user_id", "")
    workspace_id = agent_config.get("_workspace_id", "")

    init_schedule_context(
        user_id=user_id,
        workspace_id=workspace_id,
        agent_id=agent_config.get("id", ""),
    )

    # 初始化 XHS Cookie 上下文
    try:
        from src.skills.xhs_scraper import init_xhs_context
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cookie_path = os.path.join(project_root, "data", user_id, ".xhs_cookie")
        xhs_cookie = ""
        if os.path.exists(cookie_path):
            with open(cookie_path, "r", encoding="utf-8") as f:
                xhs_cookie = f.read().strip()
        event_queue = agent_config.get("_event_queue")
        init_xhs_context(cookie=xhs_cookie, event_queue=event_queue, user_id=user_id)
    except Exception:
        pass

    # 动态创建用户级 FileManager（替代已废弃的全局 _file_manager）
    user_fm = None
    if user_id:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        user_data_root = os.path.join(project_root, "data", user_id)
        if os.path.isdir(user_data_root):
            user_fm = FileManager(user_data_root)

    if base_path and user_fm:
        file_tools = create_agent_file_tools(base_path, user_fm)
    else:
        file_tools = FILE_TOOLS

    # 动态初始化 MetaAgent（替代已废弃的全局 init_meta_tools 调用）
    if user_fm and user_id:
        try:
            from src.core.agent_registry import AgentRegistry
            from src.core.meta_agent import MetaAgent
            registry = AgentRegistry(user_id)
            meta = MetaAgent(user_fm, registry)
            init_meta_tools(meta)
            set_meta_context(workspace_id=workspace_id)
        except Exception as e:
            print(f"[nodes.py] MetaAgent init failed: {e}")

    all_tools = {t.name: t for t in file_tools + WEB_TOOLS + CODE_TOOLS + BROWSER_TOOLS + PLAYWRIGHT_TOOLS + META_TOOLS + STOCK_TOOLS + SCHEDULE_TOOLS}

    # 2. 收集 L2/L3 Skills
    # 这里假设 custom_skills 在项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sl = SkillLoader(os.path.join(project_root, "custom_skills"))
    sl.scan_and_load()

    workspace_id = agent_config.get("workspace_id", "") or ""
    _skill_agent_id = agent_config.get("id", "")
    _skill_agent_name = agent_config.get("name", "")
    _skill_user_id = user_id

    for name, skill_data in sl.skills.items():
        # 将技能函数包装为 LangChain Tool
        # 使用 functools.wraps 保留原始函数签名，否则 StructuredTool 无法生成正确的参数 schema
        import functools
        def create_wrapper(run_func, ws_id, ag_id, ag_name, uid):
            @functools.wraps(run_func)
            def wrapper(*args, **kwargs):
                kwargs["workspace_id"] = ws_id
                kwargs["agent_id"] = ag_id
                kwargs["agent_name"] = ag_name
                kwargs["user_id"] = uid
                return run_func(*args, **kwargs)
            return wrapper
        
        wrapper_func = create_wrapper(skill_data["run"], workspace_id, _skill_agent_id, _skill_agent_name, _skill_user_id)
        
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
    # 始终加载系统默认工具
    for name in SYSTEM_DEFAULT_TOOLS:
        if name in all_tools and all_tools[name] not in final_tools:
            final_tools.append(all_tools[name])
    # 如果是 Meta-Agent，加载 Meta 专属默认工具
    agent_id = agent_config.get("id", "")
    if agent_id == "meta_agent":
        for name in META_AGENT_DEFAULT_TOOLS:
            if name in all_tools and all_tools[name] not in final_tools:
                final_tools.append(all_tools[name])
    # 合并用户额外配置的 tools 和 skills
    for name in requested_tools + requested_skills:
        if name in all_tools and all_tools[name] not in final_tools:
            final_tools.append(all_tools[name])

    # 4. 加载 MCP 工具
    mcp_servers = agent_config.get("mcp_servers", [])
    # Debug: write to file since stdout may be buffered in thread
    try:
        with open("mcp_debug.log", "a", encoding="utf-8") as f:
            import datetime
            f.write(f"[{datetime.datetime.now()}] _get_tools called. mcp_servers={mcp_servers}, agent_config keys={list(agent_config.keys())}\n")
    except: pass
    if mcp_servers:
        try:
            import requests as _requests
            import threading
            import queue as _queue
            from src.mcp.adapter import MCPTool, MCPServerConfig, get_mcp_manager

            manager = get_mcp_manager()
            # Use function-level cache so tools are loaded once per server restart
            if not hasattr(_get_tools, '_mcp_tool_cache'):
                _get_tools._mcp_tool_cache = {}

            for server_config in mcp_servers:
                if not server_config.get("enabled", True):
                    continue
                config = MCPServerConfig.from_dict(server_config)

                # Return cached tools
                if config.name in _get_tools._mcp_tool_cache:
                    final_tools.extend(_get_tools._mcp_tool_cache[config.name])
                    continue

                try:
                    loaded_tools = []
                    if config.transport.value == "stdio" and config.command:
                        # stdio 模式：通过子进程加载工具
                        loaded_tools = _load_mcp_stdio_tools_sync(config, manager)
                    elif config.url:
                        # SSE/HTTP 模式：通过 URL 加载工具
                        headers = {}
                        if config.api_key:
                            headers["Authorization"] = f"Bearer {config.api_key}"
                        headers.update(config.headers)
                        loaded_tools = _load_mcp_tools_sync(config.url, headers, config, manager)

                    if loaded_tools:
                        _get_tools._mcp_tool_cache[config.name] = loaded_tools
                        final_tools.extend(loaded_tools)
                except Exception as e:
                    try:
                        with open("mcp_debug.log", "a", encoding="utf-8") as f:
                            f.write(f"  [FAIL] MCP '{config.name}': {type(e).__name__}: {e}\n")
                    except: pass

        except Exception as e:
            try:
                with open("mcp_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"  [ERROR] MCP loading: {type(e).__name__}: {e}\n")
            except: pass

    return final_tools


def _load_mcp_stdio_tools_sync(config, manager) -> list:
    """
    Sync stdio MCP tool loader.
    Starts the MCP server as a subprocess, loads tools, then keeps process alive.
    """
    import asyncio
    import threading
    from src.mcp.adapter import MCPTool, MCPServerStdio

    tools = []

    def _run():
        nonlocal tools
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            server = MCPServerStdio(config)
            success = loop.run_until_complete(server.start())
            if success and server.tools:
                for t in server.tools:
                    tool = MCPTool(
                        name=t["name"],
                        description=t.get("description", ""),
                        mcp_server_name=config.name,
                        input_schema=t.get("inputSchema", {}),
                        mcp_manager=manager,
                    )
                    tools.append(tool)
                # Register server in manager for later tool calls
                manager.servers[config.name] = server
        except Exception as e:
            try:
                with open("mcp_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"  [STDIO-FAIL] MCP '{config.name}': {type(e).__name__}: {e}\n")
            except: pass
        finally:
            loop.close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=30)  # 最多等 30 秒

    return tools


def _load_mcp_tools_sync(url: str, headers: dict, config, manager) -> list:
    """
    Sync MCP SSE tool loader using threading.
    MCP SSE protocol:
      1. GET /sse → SSE stream, server sends 'endpoint' event with message URL
      2. POST to message URL → server sends response via SSE stream
    We keep the SSE stream open in a bg thread while POSTing requests.
    """
    import requests as _requests
    import threading
    import queue as _queue
    import json

    response_queue = _queue.Queue()
    endpoint_queue = _queue.Queue()
    stop_event = threading.Event()

    def sse_reader():
        """Background thread: maintains SSE connection, reads responses."""
        try:
            sse_headers = {**headers, "Accept": "text/event-stream"}
            resp = _requests.get(url, headers=sse_headers, stream=True, timeout=30)
            current_event = None
            for raw_line in resp.iter_lines(decode_unicode=True):
                if stop_event.is_set():
                    break
                if not raw_line:
                    current_event = None
                    continue
                line = raw_line.strip()
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    data = line.split(":", 1)[1].strip()
                    if current_event == "endpoint":
                        endpoint_queue.put(data)
                    elif current_event == "message" or current_event is None:
                        try:
                            parsed = json.loads(data)
                            response_queue.put(parsed)
                        except:
                            pass
            resp.close()
        except Exception as e:
            endpoint_queue.put(f"ERROR:{e}")

    # Start SSE reader thread
    reader_thread = threading.Thread(target=sse_reader, daemon=True)
    reader_thread.start()

    try:
        # Wait for the endpoint URL
        endpoint_path = endpoint_queue.get(timeout=10)
        if isinstance(endpoint_path, str) and endpoint_path.startswith("ERROR:"):
            raise Exception(f"SSE connection failed: {endpoint_path}")

        # Build absolute message URL
        base_origin = "/".join(url.split("?")[0].split("/")[:3])
        if endpoint_path.startswith("http"):
            message_url = endpoint_path
        else:
            message_url = base_origin + endpoint_path

        try:
            with open("mcp_debug.log", "a", encoding="utf-8") as f:
                f.write(f"  [INFO] '{config.name}' endpoint: {message_url}\n")
        except: pass

        post_headers = {**headers, "Content-Type": "application/json"}

        # Step 2: Send initialize
        init_req = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "AgentOS", "version": "1.0.0"}
            }
        }
        _requests.post(message_url, json=init_req, headers=post_headers, timeout=10)
        try:
            init_resp = response_queue.get(timeout=10)
        except _queue.Empty:
            raise Exception("No init response from SSE stream")

        # Step 3: Send initialized notification
        notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        _requests.post(message_url, json=notif, headers=post_headers, timeout=10)

        # Step 4: Send tools/list
        tools_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        _requests.post(message_url, json=tools_req, headers=post_headers, timeout=10)
        try:
            tools_resp = response_queue.get(timeout=10)
        except _queue.Empty:
            raise Exception("No tools/list response from SSE stream")

        # Parse tools — create SyncMCPTool instances
        loaded_tools = []
        if "result" in tools_resp:
            tool_list = tools_resp["result"].get("tools", [])
            for tool_info in tool_list:
                sync_tool = SyncMCPTool(
                    name=tool_info.get("name", ""),
                    description=tool_info.get("description", ""),
                    mcp_server_name=config.name,
                    input_schema=tool_info.get("inputSchema", {}),
                    mcp_sse_url=url,
                    mcp_headers=headers,
                )
                loaded_tools.append(sync_tool._structured_tool)
            try:
                with open("mcp_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"  [OK] '{config.name}': {len(tool_list)} tools: {[t.get('name') for t in tool_list]}\n")
            except: pass
        else:
            try:
                with open("mcp_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"  [WARN] '{config.name}' no result: {tools_resp}\n")
            except: pass

        return loaded_tools

    finally:
        stop_event.set()
        reader_thread.join(timeout=2)


class SyncMCPTool:
    """
    Synchronous MCP tool that implements the LangChain BaseTool interface.
    Uses sync HTTP + threading to call MCP tools via the SSE protocol.
    """
    def __init__(self, name: str, description: str, mcp_server_name: str,
                 input_schema: dict, mcp_sse_url: str, mcp_headers: dict):
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel, Field as PydanticField, create_model
        from typing import Optional

        self._tool_name = name
        self._mcp_sse_url = mcp_sse_url
        self._mcp_headers = mcp_headers

        # Build dynamic Pydantic model from input_schema
        properties = input_schema.get("properties", {})
        required_fields = input_schema.get("required", [])

        type_map = {
            "string": str, "number": float, "integer": int,
            "boolean": bool, "object": dict, "array": list
        }

        field_definitions = {}
        for field_name, field_info in properties.items():
            field_type = type_map.get(field_info.get("type", "string"), str)
            field_desc = field_info.get("description", "")
            if field_name in required_fields:
                field_definitions[field_name] = (field_type, PydanticField(description=field_desc))
            else:
                field_definitions[field_name] = (Optional[field_type], PydanticField(default=None, description=field_desc))

        # Create dynamic model; fallback to basic model if no properties
        if field_definitions:
            ArgsModel = create_model(f"{name}_args", **field_definitions)
        else:
            ArgsModel = create_model(f"{name}_args", input=(str, PydanticField(default="", description="Input")))

        # Capture self reference for the closure
        _self = self

        def mcp_call_func(**kwargs):
            return _self._execute_tool(name, kwargs)

        self._structured_tool = StructuredTool.from_function(
            func=mcp_call_func,
            name=name,
            description=description or name,
            args_schema=ArgsModel,
        )

    @property
    def name(self):
        return self._structured_tool.name

    @property
    def description(self):
        return self._structured_tool.description

    @property
    def args_schema(self):
        return self._structured_tool.args_schema

    def invoke(self, *args, **kwargs):
        return self._structured_tool.invoke(*args, **kwargs)

    def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Execute MCP tool via sync SSE protocol."""
        import requests as _requests
        import threading
        import queue as _queue
        import json

        response_queue = _queue.Queue()
        endpoint_queue = _queue.Queue()
        stop_event = threading.Event()
        url = self._mcp_sse_url
        headers = self._mcp_headers

        def sse_reader():
            try:
                sse_headers = {**headers, "Accept": "text/event-stream"}
                resp = _requests.get(url, headers=sse_headers, stream=True, timeout=60)
                current_event = None
                for raw_line in resp.iter_lines(decode_unicode=True):
                    if stop_event.is_set():
                        break
                    if not raw_line:
                        current_event = None
                        continue
                    line = raw_line.strip()
                    if line.startswith("event:"):
                        current_event = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        data = line.split(":", 1)[1].strip()
                        if current_event == "endpoint":
                            endpoint_queue.put(data)
                        elif current_event == "message" or current_event is None:
                            try:
                                parsed = json.loads(data)
                                response_queue.put(parsed)
                            except: pass
                resp.close()
            except Exception as e:
                endpoint_queue.put(f"ERROR:{e}")

        reader_thread = threading.Thread(target=sse_reader, daemon=True)
        reader_thread.start()

        try:
            endpoint_path = endpoint_queue.get(timeout=10)
            if isinstance(endpoint_path, str) and endpoint_path.startswith("ERROR:"):
                return f"MCP 连接失败: {endpoint_path}"

            base_origin = "/".join(url.split("?")[0].split("/")[:3])
            message_url = base_origin + endpoint_path if not endpoint_path.startswith("http") else endpoint_path

            post_headers = {**headers, "Content-Type": "application/json"}

            # Initialize
            init_req = {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "AgentOS", "version": "1.0.0"}
                }
            }
            _requests.post(message_url, json=init_req, headers=post_headers, timeout=10)
            try: response_queue.get(timeout=10)
            except: return "MCP 初始化超时"

            # Initialized notification
            _requests.post(message_url, json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                          headers=post_headers, timeout=10)

            # Call tool
            call_req = {
                "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments}
            }
            _requests.post(message_url, json=call_req, headers=post_headers, timeout=30)

            try:
                result = response_queue.get(timeout=30)
            except _queue.Empty:
                return "MCP 工具调用超时"

            # Parse result
            if "result" in result:
                content = result["result"].get("content", [])
                texts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        texts.append(item.get("text", ""))
                    elif isinstance(item, str):
                        texts.append(item)
                return "\n".join(texts) if texts else json.dumps(result["result"], ensure_ascii=False)
            elif "error" in result:
                return f"MCP 错误: {result['error']}"
            else:
                return json.dumps(result, ensure_ascii=False)

        except Exception as e:
            return f"MCP 工具执行错误: {e}"
        finally:
            stop_event.set()
            reader_thread.join(timeout=2)


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
        llm = _get_llm(agent_config, user_id=state.get("user_id"))
    except ValueError as e:
        return {
            "messages": [AIMessage(content=f"⚠️ 配置错误: {str(e)}")],
            "needs_approval": False,
        }

    # 构建 system prompt
    system_prompt = agent_config.get("system_prompt", "你是一个 AI 助手。")

    # 追加系统级行为规范
    system_prompt += """

---
## 系统行为规范
### 文件操作流程
当收到需要保存文件的指令时，严格按以下步骤执行：
1. **定位文件夹**: 用 list_directory 检查目标文件夹是否已存在
2. **文件夹处理**: 已存在 → 直接使用；不存在 → 新建文件夹
3. **文件处理**: 
   - 如果是更新/修改/追加已有文件 → 先 read_file 读取原内容，修改后 write_file 覆盖
   - 如果是新建文件 → 直接 write_file 到目标路径
4. **默认存储区域**: 用户没有明确说明时，一律保存到私有文件区域（直接用路径如 "文件夹名/文件名.md"）
5. **共享区域**: 只有用户明确说"共享文件"或"共享目录"时，才使用 shared/ 前缀（如 "shared/文件夹名/文件名.md"）。查看共享文件夹时用 list_directory("shared/")
6. **绝对禁止**: 不要提及"审批面板"、"右侧面板"或任何不存在的 UI 元素
### 回复规范
- 完成任务后，务必给用户一个简短的文字总结（做了什么、文件保存在哪个路径）
- 不要只执行工具就结束，必须有一段总结性文字回复
"""

    if context:
        system_prompt += f"\n\n---\n{context}"

    # 自动加载 Agent 的行为标准和未竟事项（如果存在）
    curr_ws = state.get("current_workspace", "")
    curr_ag = state.get("current_agent", "")
    _uid = state.get("user_id", "")
    if curr_ws and curr_ag and _uid:
        _agent_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", _uid, curr_ws, curr_ag, "archives"
        )
        for _fname, _label in [("行为标准.md", "行为准则"), ("未竟事项.md", "未竟事项")]:
            _fpath = os.path.join(_agent_dir, _fname)
            if os.path.exists(_fpath):
                try:
                    with open(_fpath, "r", encoding="utf-8") as _f:
                        _content = _f.read().strip()
                    if _content and len(_content) > 20:
                        system_prompt += f"\n\n---\n## {_label}\n{_content[:2000]}"
                except Exception:
                    pass



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
        # 仅当 RAG 工具可用时才添加知识库提示
        system_prompt += "\n\n你可以使用 `search_knowledge_base` 工具来检索知识库。如果用户询问特定文档或领域知识，请先调用该工具收集信息，不要猜测。"

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

    # 直接获取带 context 的工具
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
