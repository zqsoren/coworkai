import json
import asyncio
from typing import List, Dict, Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage

from src.core.base_agent import BaseAgent
from src.core.llm_manager import LLMManager
from src.core.agent_registry import AgentRegistry
from src.core.file_manager import FileManager
from src.core.persona_prompts import get_persona_prompt
from src.utils.rag_ingestion import RAGIngestion
from src.tools.rag_tools import get_rag_tool
from src.mcp import get_mcp_manager, MCPServerConfig

class ModelAgent(BaseAgent):
    """
    Adapter bridging the Data-Driven Agent config to an Object-Oriented Agent.
    Exposes `chat()` and `execute()` methods for GroupChat integration.
    """

    def __init__(self, agent_id: str, workspace_id: str, 
                 file_manager: FileManager, registry: AgentRegistry, llm_manager: LLMManager = None):
        super().__init__(agent_id, workspace_id, file_manager)
        self.file_manager = file_manager # Alias for backward compatibility
        self.registry = registry
        
        # Load config from registry (source of truth)
        self.config = self.registry.get_agent(agent_id)
        if not self.config:
            raise ValueError(f"Agent '{agent_id}' not found in registry.")

        # Override BaseAgent properties with registry data
        self.name = self.config.get("name", agent_id)
        # Use system_prompt as description (Supervisor Context), fallback to 'role' for legacy
        self.system_prompt = self.config.get("system_prompt", "You are a helpful AI assistant.")
        self.description = self.system_prompt if self.system_prompt else self.config.get("role", "A helpful AI assistant.")
        
        # Initialize LLM — use provided manager (user-scoped) or default
        self.llm_manager = llm_manager or LLMManager()
        self.llm = self._init_llm()

    def _init_llm(self):
        """Initialize LLM based on config."""
        provider_id = self.config.get("provider_id", "")
        model_name = self.config.get("model_name")
        if not model_name:
            print(f"[ModelAgent] Warning: Agent {self.agent_id} has empty model_name. Fallback to default.")
            model_name = "z-ai/glm-4.5-air:free"
        
        # Validate provider exists in the user's loaded providers
        if provider_id and provider_id not in self.llm_manager.providers:
            print(f"[ModelAgent] Warning: Provider '{provider_id}' not found. Trying first available provider.")
            if self.llm_manager.providers:
                provider_id = next(iter(self.llm_manager.providers))
            else:
                raise ValueError(f"No LLM providers configured. Cannot initialize agent {self.agent_id}.")

        print(f"[ModelAgent] Init LLM for {self.agent_id}: provider={provider_id}, model={model_name}")
        try:
            return self.llm_manager.get_model(provider_id, model_name)
        except Exception as e:
            print(f"Error initializing LLM for {self.agent_id}: {e}")
            # Fallback to first available provider's first model
            if self.llm_manager.providers:
                fallback_pid = next(iter(self.llm_manager.providers))
                fallback_p = self.llm_manager.providers[fallback_pid]
                fallback_model = fallback_p.models[0] if fallback_p.models else model_name
                print(f"[ModelAgent] Falling back to: provider={fallback_pid}, model={fallback_model}")
                return self.llm_manager.get_model(fallback_pid, fallback_model)
            raise

    async def chat(self, history: List[Dict[str, Any]]) -> str:
        """
        Standard chat interaction.
        Args:
            history: List of dicts [{'role': 'user'|'assistant'|'system', 'content': '...'}]
        Returns:
            Review text or conversation response.
        """
        # Build enhanced system prompt with persona
        persona_mode = self.config.get("persona_mode", "normal")
        persona_prompt = get_persona_prompt(persona_mode)
        enhanced_prompt = f"{self.system_prompt}\n\n{persona_prompt}" if persona_prompt else self.system_prompt
        
        messages = [SystemMessage(content=enhanced_prompt)]
        
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                # If there's a specific 'name' in the message (from GroupChat), prepend it?
                # For now, standard LangChain messages don't strictly enforce 'name' field in all drivers.
                messages.append(AIMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))
        
        response = await self.llm.ainvoke(messages)
        return response.content

    async def execute(self, instruction: str) -> str:
        """
        Execute a specific instruction, potentially using tools.
        For simplicity in this V1 adapter, we map it to a chat call with tools if available.
        """
        # TODO: Bind tools here if we want real execution. 
        # For the Supervisor/GroupChat text-based flow, chat is often sufficient 
        # unless we strictly need the tool output as the return value.
        
        # For now, treat execution as a direct formatted prompt
        # framing the instruction as a command.
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"EXECUTE: {instruction}")
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content

    async def execute_with_context(self, instruction: str, history: list, on_event=None) -> str:
        """
        Execute a specific instruction with conversation history context.
        This allows the agent to see what other agents have said before.
        
        NOW supports RAG (knowledge base) and tools (file operations, etc.)
        similar to single-chat mode.
        
        Args:
            instruction: The task instruction from Supervisor
            history: List of conversation history dicts with 'role', 'content', 'name'
        
        Returns:
            Agent's response
        """
        import os
        
        # 1. Build enhanced system prompt with persona
        persona_mode = self.config.get("persona_mode", "normal")
        persona_prompt = get_persona_prompt(persona_mode)
        enhanced_prompt = f"{self.system_prompt}\n\n{persona_prompt}" if persona_prompt else self.system_prompt
        
        
        # 2. 🆕 Agentic RAG: Bind Search Tool and Update Prompt
        # Use data_root (canonical) instead of base_dir (alias) to avoid AttributeError
        try:
            # Defensive check for file_manager
            file_manager = getattr(self, "file_manager", None)
            if file_manager:
                root_dir = getattr(file_manager, "data_root", getattr(file_manager, "base_dir", "."))
                base_path = os.path.join(root_dir, self.workspace_id, self.agent_id)
                
                # Initialize RAG System for this agent
                rag = RAGIngestion(root_dir, self.workspace_id, self.agent_id)
                rag_tool = get_rag_tool(rag)
            else:
                # Fallback
                base_path = os.path.join(".", self.workspace_id, self.agent_id)
                rag_tool = None
        except Exception as e:
            print(f"[ModelAgent] Error resolving base_path or RAG: {e}")
            base_path = "."
            rag_tool = None

        # Update System Prompt with Tool Instructions
        enhanced_prompt += """

你是一个高级 AI 助手。你可以使用 `search_knowledge_base` 工具。
**重要提示**：你默认不知道用户数据库中的内容。如果用户询问特定的 ID、某份文档或领域特定的知识，你必须首先调用 `search_knowledge_base` 工具来收集信息。
绝对不要瞎猜。请仔细分析用户的请求，生成精准的搜索查询词，调用该工具，然后使用返回的真实信息来回答用户。
"""
            
        print(f"[{self.name}] Executing with context. History len: {len(history)}")
        tools = self._get_agent_tools(base_path)
        
        # Add RAG tool if available
        if rag_tool:
            tools.append(rag_tool)
        
        if tools:
            llm_with_tools = self.llm.bind_tools(tools)
        else:
            llm_with_tools = self.llm
        
        # 4. Build messages with history
        messages = [SystemMessage(content=enhanced_prompt)]
        
        # Add recent conversation history (last 10 messages for context)
        recent_history = history[-10:] if len(history) > 10 else history
        
        for msg in recent_history:
            role = msg.get("role")
            content = msg.get("content")
            name = msg.get("name", role)
            
            if role == "user":
                messages.append(HumanMessage(content=f"[User]: {content}"))
            elif role == "assistant":
                messages.append(AIMessage(content=f"[{name}]: {content}"))
        
        # Add current instruction
        messages.append(HumanMessage(content=f"[Supervisor Instruction]: {instruction}"))
        
        # 5. 🆕 Tool execution loop (similar to agent_node in nodes.py)
        import time
        start_time = time.time()
        
        def log_debug(msg):
            try:
                with open("backend_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
            except: pass

        log_debug(f"[{self.name}] 开始执行 execute_with_context... (Instruction length: {len(instruction)})")
        
        async def fire(event_type: str, **kwargs):
            if on_event:
                try:
                    await on_event({"type": event_type, "agent": self.name, **kwargs})
                except Exception:
                    pass

        max_iterations = 5
        for iteration in range(max_iterations):
            try:
                log_debug(f"[{self.name}] LLM Invocation {iteration+1}/{max_iterations}...")
                await fire("thinking")
                response = await llm_with_tools.ainvoke(messages)
                log_debug(f"[{self.name}] LLM Response received ({time.time() - start_time:.2f}s)")
            except Exception as e:
                log_debug(f"[{self.name}] LLM Error: {e}")
                await fire("error", content=str(e))
                return f"⚠️ LLM 调用失败: {str(e)}"
            
            # Check if there are tool calls
            if hasattr(response, "tool_calls") and response.tool_calls:
                print(f"[{self.name}] 工具调用: {len(response.tool_calls)} 个工具")
                
                # Emit tool_call events
                for tc in response.tool_calls:
                    import json as _json
                    await fire("tool_call", tool=tc.get("name", ""), args=_json.dumps(tc.get("args", {}), ensure_ascii=False)[:300])

                # Add AI response with tool calls to messages
                messages.append(response)
                
                # Execute tools
                try:
                    tool_results = await self._execute_tools_with_events(response.tool_calls, tools, fire)
                    messages.extend(tool_results)
                except Exception as e:
                    print(f"[{self.name}] 工具执行严重错误: {e}")
                    messages.append(ToolMessage(content=f"Error executing tools: {e}", tool_call_id="error"))
                
                # Continue loop to get final answer
            else:
                # No tool calls, this is the final answer
                print(f"[{self.name}] 执行完成，返回结果。")
                await fire("agent_message", content=response.content)
                return response.content
        
        # Max iterations reached, return last response
        return response.content if hasattr(response, 'content') else str(response)

    # 🆕 Helper methods for RAG and tools
    
    async def _query_knowledge_base(self, query: str) -> str:
        """查询知识库，返回相关文档片段"""
        import os
        
        try:
            from src.core.rag import RAGSystem
            
            rag = RAGSystem(self.file_manager.base_dir)
            vs_path = os.path.join(
                self.file_manager.base_dir,
                self.workspace_id,
                self.agent_id,
                "vector_store"
            )
            
            if os.path.exists(vs_path) and os.listdir(vs_path):
                docs = rag.query(query, top_k=3)
                if docs:
                    context = ""
                    for d in docs:
                        context += f"### [{d['source']}] (相关度: {d['score']:.2f})\n{d['content'][:500]}\n\n"
                    return context
        except Exception as e:
            print(f"[{self.name}] RAG查询失败: {e}")
        
        return ""
    
    def _get_agent_tools(self, base_path: str):
        """获取 Agent 配置的工具列表（包括 MCP 工具）"""
        from src.graph.nodes import _get_tools
        
        tools = []
        
        try:
            tools = _get_tools(self.config, base_path)
        except Exception as e:
            print(f"[{self.name}] 工具加载失败: {e}")
        
        mcp_tools = self._get_mcp_tools()
        tools.extend(mcp_tools)
        
        return tools
    
    def _get_mcp_tools(self) -> List:
        """获取 Agent 配置的 MCP 工具"""
        mcp_tools = []
        mcp_servers = self.config.get("mcp_servers", [])
        
        if not mcp_servers:
            return mcp_tools
        
        try:
            manager = get_mcp_manager()
            
            for server_config in mcp_servers:
                if not server_config.get("enabled", True):
                    continue
                
                config = MCPServerConfig.from_dict(server_config)
                
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(manager.add_server(config))
                    else:
                        asyncio.run(manager.add_server(config))
                except Exception as e:
                    print(f"[{self.name}] MCP Server '{config.name}' 初始化失败: {e}")
            
            mcp_tools = manager.get_langchain_tools()
            print(f"[{self.name}] 加载了 {len(mcp_tools)} 个 MCP 工具")
            
        except Exception as e:
            print(f"[{self.name}] MCP 工具加载失败: {e}")
        
        return mcp_tools
    
    async def _execute_tools_with_events(self, tool_calls, tools, fire):
        """执行工具调用并发射事件，返回ToolMessage列表"""
        results = []
        tool_map = {t.name: t for t in tools}

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id", "unknown")

            if tool_name in tool_map:
                tool = tool_map[tool_name]
                try:
                    if hasattr(tool, "ainvoke"):
                        result = await tool.ainvoke(tool_args)
                    else:
                        result = tool.invoke(tool_args)
                    result_str = str(result)
                    await fire("tool_result", tool=tool_name, result=result_str[:500])
                    results.append(ToolMessage(content=result_str, tool_call_id=tool_id))
                except Exception as e:
                    error_msg = f"工具 {tool_name} 执行失败: {str(e)}"
                    await fire("tool_result", tool=tool_name, result=error_msg)
                    results.append(ToolMessage(content=error_msg, tool_call_id=tool_id))
            else:
                error_msg = f"工具 {tool_name} 未找到"
                await fire("tool_result", tool=tool_name, result=error_msg)
                results.append(ToolMessage(content=error_msg, tool_call_id=tool_id))
        return results

    async def _execute_tools(self, tool_calls, tools):
        """执行工具调用，返回ToolMessage列表"""
        results = []
        
        # Build tool name -> tool mapping
        tool_map = {t.name: t for t in tools}
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id", "unknown")
            
            if tool_name in tool_map:
                tool = tool_map[tool_name]
                try:
                    # Execute tool (sync or async)
                    if hasattr(tool, "ainvoke"):
                        result = await tool.ainvoke(tool_args)
                    else:
                        result = tool.invoke(tool_args)
                    
                    results.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tool_id
                    ))
                    print(f"[{self.name}] 工具 {tool_name} 执行成功")
                except Exception as e:
                    error_msg = f"工具 {tool_name} 执行失败: {str(e)}"
                    print(f"[{self.name}] {error_msg}")
                    results.append(ToolMessage(
                        content=error_msg,
                        tool_call_id=tool_id
                    ))
            else:
                error_msg = f"工具 {tool_name} 未找到"
                print(f"[{self.name}] {error_msg}")
                results.append(ToolMessage(
                    content=error_msg,
                    tool_call_id=tool_id
                ))
        
        return results
