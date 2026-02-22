"""
chat - Gemini 风格聊天界面
固定底部输入框 + 流式输出 + Markdown 渲染
包含动态等待动画 (Thinking... Building... Outputting...)
"""

import time
import json
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from src.graph.agent_graph import create_compiled_graph
from src.core.file_manager import FileManager


def _extract_text_content(content) -> str:
    """提取纯文本内容 (Gemini list format parser)"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)
        return "\n".join(text_parts) if text_parts else str(content)
    return str(content)





def render_chat(file_manager: FileManager):
    """渲染主聊天区域"""
    current_agent = st.session_state.get("current_agent", "")
    agent_config = st.session_state.get("agent_config", {})

    if not current_agent:
        st.info("请先选择一个 Agent")
        return

    # 初始化 session state
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []
    if "pending_changes" not in st.session_state:
        st.session_state["pending_changes"] = []

    # =========================================================
    # 0. Mode Detection & Dynamic CSS Injection
    # =========================================================
    # Welcome Mode only if NO messages
    is_welcome_mode = len(st.session_state["chat_messages"]) == 0
    agent_name = agent_config.get("name", "Agent")

    if is_welcome_mode:
        # === STATE A: INITIAL CENTERED VIEW ===
        from src.utils.i18n import i18n
        
        # 1. Show Greeting
        st.markdown(
            f"""
            <div style="text-align: center; margin-top: 10vh; margin-right:px;font-family: 'Inter', sans-serif;">
                <h1 style="color: #2c3e50; font-size: 3rem; font-weight: 700;">Hello, {agent_name}.</h1>
                <p style="color: #95a5a6; font-size: 1.2rem;">{i18n.t("chat.welcome_subtitle")}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 2. Inject CSS to Move Input to Center (Targeting stBottom)
        st.markdown("""
        <style>
        /* === 智能定位控制 (Smart Layout) === */
        
        /* [1] 外层容器：避开左侧边栏，只在“主内容区+右侧区”里活动 */
        div[data-testid="stChatInput"] {
            position: fixed !important;
            bottom: 20% !important; /* 垂直高度 */
            z-index: 99999 !important;
            
            /* === 关键布局逻辑 === */
            /* Streamlit 左侧边栏宽度通常是 21rem (336px) */
            left: 21rem !important; 
            /* 宽度 = 屏幕总宽 - 左侧边栏宽度 */
            width: calc(100% - 21rem) !important;
            
            display: flex !important;
            justify-content: center !important; /* 让里面的输入框在剩余空间里居中 */
            align-items: center !important;
            pointer-events: none !important; /* 让点击穿透空白区域 */
        }
        
        /* [2] 里面的输入框本体 */
        div[data-testid="stChatInput"] > div {
            pointer-events: auto !important; /* 恢复点击 */
            
            /* 宽度控制：在中间区域占 70% */
            width: 70% !important; 
            max-width: 800px !important;
            
            /* 自动居中 (不需要再手动算 margin-left 了) */
            margin-right: 36% !important; 
            
            /* 样式 */
            border-radius: 30px !important;
            box-shadow: 0 12px 40px rgba(0,0,0,0.15) !important;
            border: 1px solid #e0e0e0 !important;
            background: white !important;
            padding: 24px 28px !important;
        }

        /* [3] 响应式适配：如果屏幕变窄（侧边栏收起），自动铺满 */
        @media (max-width: 992px) {
            div[data-testid="stChatInput"] {
                left: 0 !important;
                width: 100% !important;
            }
        }
        
        /* 隐藏底部默认背景 */
        [data-testid="stBottom"] {
            display: none !important;
        }
        </style>
        """, unsafe_allow_html=True)

    else:
        # === STATE B: STANDARD CHAT VIEW ===
        
        # Inject CSS to smooth the transition back to bottom
        # Position: Fixed at bottom with margin (Floating Capsule)
        st.markdown("""
        <style>
        div[data-testid="stChatInput"] {
            bottom: 40px !important; /* Floating above bottom */
            background-color: transparent !important;
            
            /* Alignment Logic: Same as Welcome Mode */
            left: 21rem !important; 
            width: calc(100% - 35rem) !important;
            
            display: flex !important;
            justify-content: center !important; 
            align-items: center !important;
            pointer-events: none !important; /* Allow clicks through empty space */
        }
        
        /* Inner Input Box: Same ratio as Welcome Mode */
        div[data-testid="stChatInput"] > div {
            pointer-events: auto !important;
            width: 70% !important; 
            max-width: 800px !important;
            margin-right: 25% !important; /* Center offset logic */
        }

        /* Responsive: Full width on smaller screens */
        @media (max-width: 992px) {
            div[data-testid="stChatInput"] {
                left: 0 !important;
                width: 100% !important;
            }
            div[data-testid="stChatInput"] > div {
                margin-right: 0 !important;
                width: 90% !important;
            }
        }
        
        [data-testid="stBottom"] {
            display: none !important; /* Hide the default bottom bar container */
        }
        </style>
        """, unsafe_allow_html=True)
        
        # 3. Render Header Badge & History
        # Active Mode Header & History
        provider = agent_config.get("provider_id", "")
        model = agent_config.get("model_name", "")
        st.markdown(
            f"""
            <div style="position:fixed; top:60px; right:20px; z-index:999; opacity:0.8;">
                 <span style="font-size:10px; padding:4px 8px; border-radius:12px; background:rgba(255,255,255,0.8); border:1px solid #e2e8f0; color:#64748b; font-family:sans-serif;">
                    {agent_name} • {provider}/{model}
                 </span>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    # =========================================================
    # 4. Input Handler (Bottom) - MOVED UP due to blocking generation
    # =========================================================
    from src.utils.i18n import i18n
    placeholder = i18n.t("chat.input_placeholder", name=agent_name)
    
    # Standard Input - When user hits Enter:
    if prompt := st.chat_input(placeholder, key="chat_input"):
        # 1. Append User Message
        st.session_state["chat_messages"].append({"role": "user", "content": prompt})
        # 2. FORCE RERUN IMMEDIATELY
        st.rerun()

    # =========================================================
    # 5. Active Mode: Auto-Trigger Generation Logic
    # =========================================================
    if not is_welcome_mode:
        chat_container = st.container()
        with chat_container:
            for message in st.session_state["chat_messages"]:
                if isinstance(message, HumanMessage) or (isinstance(message, dict) and message.get("role") == "user"):
                    content = message.content if hasattr(message, "content") else message["content"]
                    with st.chat_message("user", avatar="👤"):
                        st.markdown(_extract_text_content(content))
                elif isinstance(message, AIMessage) or (isinstance(message, dict) and message.get("role") == "assistant"):
                    content = message.content if hasattr(message, "content") else message["content"]
                    with st.chat_message("assistant", avatar="✨"):
                        st.markdown(_extract_text_content(content))
                elif isinstance(message, dict) and message.get("role") == "change_request":
                    from src.utils.i18n import i18n
                    with st.chat_message("assistant", avatar="📋"):
                        st.info(i18n.t("chat.change_request"))

            # === TRIGGER GENERATION HERE (Inside Container) ===
            if st.session_state["chat_messages"]:
                last_msg = st.session_state["chat_messages"][-1]
                role = last_msg.get("role") if isinstance(last_msg, dict) else (last_msg.type if hasattr(last_msg, "type") else "")
                
                if role == "user" or (isinstance(last_msg, HumanMessage)):
                     prompt = last_msg["content"] if isinstance(last_msg, dict) else last_msg.content
                     _generate_response_with_animation(prompt, agent_config, file_manager)
                     st.rerun()




def _generate_response_with_animation(user_input, agent_config, file_manager):
    """
    Generate response with thread-safe animation.
    Fixes 'Blank Screen' by ensuring we don't return early or clear global state.
    """
    from src.utils.i18n import i18n
    
    # Create a placehoder for the AI response block
    with st.chat_message("assistant", avatar="✨"):
        status_placeholder = st.empty()
        response_placeholder = st.empty()
        
        # 1. Prepare State
        current_ws = st.session_state.get("current_workspace", "")
        current_agent_id = st.session_state.get("current_agent", "")
        context = ""
        if current_ws and current_agent_id:
             cfiles = file_manager.get_agent_context(current_ws, current_agent_id)
             if cfiles:
                  parts = ["## Context"]
                  for k, v in cfiles.items(): parts.append(f"### {k}\n```\n{v[:1000]}\n```")
                  context = "\n".join(parts)
        
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "current_agent": current_agent_id,
            "current_workspace": current_ws,
            "agent_config": agent_config,
            "pending_changes": [],
            "approval_status": None,
            "context": context,
            "needs_approval": False,
        }

        # 2. Run Graph in background
        def run_graph():
            graph = create_compiled_graph()
            # Use 'invoke' directly. For streaming tokens in the future, use 'stream'.
            return graph.invoke(initial_state)

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(run_graph)
        
        # 3. Animation Loop
        start_time = time.time()
        while not future.done():
            elapsed = time.time() - start_time
            dots = "." * (int(elapsed * 2) % 4)
            
            if elapsed < 5:
                text = f"{i18n.t('chat.thinking')}{dots}"
                color = "#9333ea"
            elif elapsed < 12:
                text = f"{i18n.t('chat.building')}{dots}"
                color = "#2563eb"
            else:
                text = f"{i18n.t('chat.outputting')}{dots}"
                color = "#16a34a"
                
            status_placeholder.markdown(
                f'<span style="color:{color}; font-family:monospace; font-size:14px;">● {text}</span>',
                unsafe_allow_html=True
            )
            time.sleep(0.1)

        # 4. Result Handling
        try:
            result = future.result()
            
            # Extract messages
            messages = result.get("messages", [])
            pending = result.get("pending_changes", [])

            # Update session state for pending changes
            if pending:
                st.session_state["pending_changes"] = pending
                st.session_state["chat_messages"].append({
                    "role": "change_request",
                    "content": i18n.t("chat.change_request")
                })
            
            # Extract final response text
            response_text = ""
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    response_text = _extract_text_content(msg.content)
                    break
            
            if not response_text:
                response_text = "..."

            # Clear animation
            status_placeholder.empty()
            
            # Stream output
            _stream_text(response_text, response_placeholder)
            
            # Save to session state
            st.session_state["chat_messages"].append({
                "role": "assistant",
                "content": response_text
            })
            
            # Logger
            try:
                import os
                from src.core.project_logger import ProjectLogger
                if current_ws and current_agent_id:
                     project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                     logger = ProjectLogger(os.path.join(project_root, "data"), current_ws, current_agent_id)
                     logger.log_interaction(user_input, response_text)
            except: pass

        except Exception as e:
            status_placeholder.empty()
            st.error(f"Agent Error: {str(e)}")
            
        finally:
            executor.shutdown(wait=False)


def _stream_text(text: str, placeholder):
    """Simple typewriter effect"""
    displayed = ""
    chunk_size = 5
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i+chunk_size]
        displayed += chunk
        placeholder.markdown(displayed + "▌")
        time.sleep(0.01)
    placeholder.markdown(displayed)

