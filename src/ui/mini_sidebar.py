"""
Mini Sidebar (Rail Mode) - Fixed Layout
修复布局问题：使用 CSS 将侧边栏彻底脱离文档流，防止挤压主内容。
"""

import streamlit as st
import streamlit.components.v1 as components

def render_mini_sidebar(workspace_manager):
    """
    Renders the interactive Mini Sidebar.
    """
    
    # 1. 核心修复：使用 st.columns 创建独立容器 (Safe Wrapper)
    # 之前使用 st.container() 会生成 stVerticalBlock，导致 CSS :has() 意外会选中整个 App 的根容器（也是 VerticalBlock），造成页面空白。
    # 改用 st.columns([1]) 会生成 stHorizontalBlock。由于此时我们并不在其他 Column 内，
    # 这个 HorizontalBlock 是独立的，不会命中根节点，是安全的 CSS 锚点。
    col_wrapper, = st.columns([1])
    
    with col_wrapper:
        # CSS 锚点
        st.markdown('<div class="mini-sidebar-marker"></div>', unsafe_allow_html=True)
        
        # 2. 内联 CSS：针对这个 specific HorizontalBlock 的样式
        st.markdown("""
            <style>
                /* 定位包含 marker 的 HorizontalBlock */
                /* 注意：这里改成了 stHorizontalBlock */
                div[data-testid="stHorizontalBlock"]:has(div.mini-sidebar-marker) {
                    position: fixed !important;
                    left: 0 !important;
                    top: 0 !important;
                    width: 60px !important;
                    height: 100vh !important;
                    z-index: 99999 !important;
                    background-color: #f8f9fa !important;
                    border-right: 1px solid #e5e7eb !important;
                    padding-top: 12px !important;
                    align-items: center !important;
                    gap: 8px !important;
                    /* 覆盖 Streamlit 默认的 flex-direction: row */
                    flex-direction: column !important; 
                    
                    /* 默认显示 (Show by Default) - 这样更稳健，只会因规则隐藏 */
                    visibility: visible !important;
                    display: flex !important;
                    transition: all 0.1s;
                }
                
                /* 防止容器占据空间 */
                div[data-testid="stHorizontalBlock"]:has(div.mini-sidebar-marker) {
                    margin: 0 !important;
                }

                /* 按钮样式需要适配 */
                /* 因为我们现在在 column 里，按钮默认是 full width，需要限制 */
                div[data-testid="stHorizontalBlock"]:has(div.mini-sidebar-marker) button {
                    width: 40px !important;
                    height: 40px !important;
                    padding: 0 !important;
                    border: 1px solid transparent !important;
                    background: transparent !important;
                    border-radius: 8px !important;
                    color: #64748b !important;
                    display: flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                    font-size: 18px !important;
                    box-shadow: none !important;
                    margin: 0 auto !important; /* 居中 */
                }

                div[data-testid="stHorizontalBlock"]:has(div.mini-sidebar-marker) button:hover {
                    background-color: #e2e8f0 !important;
                    color: #0f172a !important;
                }
                
                div[data-testid="stHorizontalBlock"]:has(div.mini-sidebar-marker) button[kind="primary"] {
                    background-color: #eff6ff !important;
                    color: #2563eb !important;
                    border: 1px solid #dbeafe !important;
                }
                
                /* 显隐逻辑 (Visibility Logic) - REINFORCED */
                /* 当且仅当原生 Sidebar 展开时，强制隐藏 */
                /* 使用 body:has 全局检测，不再依赖兄弟选择器结构，极度鲁棒 */
                body:has([data-testid="stSidebar"][aria-expanded="true"]) div[data-testid="stHorizontalBlock"]:has(div.mini-sidebar-marker) {
                    display: none !important;
                    visibility: hidden !important;
                }
                
                /* 这条不再需要，因为默认就是 visible */
                /* [data-testid="stSidebar"][aria-expanded="false"] ... { visibility: visible !important; } */
                
                /* 修复列内部的 gap */
                div[data-testid="stHorizontalBlock"]:has(div.mini-sidebar-marker) > div {
                    width: 100% !important; /* 让内部 column 占满 */
                    display: flex !important;
                    flex-direction: column !important;
                    align-items: center !important;
                }
            </style>
        """, unsafe_allow_html=True)

        # 3. 展开按钮 (Python State + Rerun)
        # 之前的纯 JS 方案在 iframe 中可能因跨域或选择器问题失效。
        # 我们恢复最稳健的 Python 方案：更新状态 -> Rerun -> App.py 读取新状态 -> 强制展开
        
        # 为了让按钮看起来像是在这一行，我们用一个专门的 wrap
        st.markdown('<div class="mini-btn-wrapper">', unsafe_allow_html=True)
        
        if st.button("›", key="mini_expand_btn", help="Expand Sidebar"):
            st.session_state["sidebar_state"] = "expanded"
            st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 这里的 JS 是核心逻辑：使用轮询机制确保找到并点击按钮
        # 针对 Streamlit iframe 环境的鲁棒性增强版
        js_helper = """
        <script>
            function clickExpand() {
                try {
                    const doc = window.parent.document;
                    // 1. 标准 ID
                    let btn = doc.querySelector('[data-testid="stSidebarCollapsedControl"]');
                    
                    // 2. 备用：Header 中的按钮
                    if (!btn) {
                        const header = doc.querySelector('header[data-testid="stHeader"]');
                        if (header) btn = header.querySelector('button');
                    }
                    
                    // 3. 通用备用
                    if (!btn) {
                         btn = doc.querySelector('button[aria-label="Expand sidebar"]');
                    }
                    
                    if (btn) {
                        btn.click();
                        return true;
                    }
                } catch (e) {
                    console.error("MiniSidebar expansion error:", e);
                }
                return false;
            }

            // 启动轮询：每50ms尝试一次，共尝试20次 (1秒超时)
            let attempts = 0;
            const interval = setInterval(() => {
                const success = clickExpand();
                attempts++;
                if (success || attempts > 20) {
                    clearInterval(interval);
                }
            }, 50);
        </script>
        """
        components.html(js_helper, height=0, width=0)

        # 4. Workspaces & Agents
        # 这里的代码逻辑不变，只是现在在 col_wrapper 的上下文中运行
        workspaces = workspace_manager.list_workspaces()
        current_ws_id = st.session_state.get("current_workspace", "")
        
        for ws in workspaces:
            ws_id = ws["id"]
            ws_name = ws.get("name", ws_id)
            icon = ws_name.strip()[0].upper() if ws_name else "?"
            is_active = (ws_id == current_ws_id)
            
            if st.button(icon, key=f"mini_ws_{ws_id}", help=ws_name, type="primary" if is_active else "secondary"):
                st.session_state["current_workspace"] = ws_id
                st.session_state["current_agent"] = None
                st.rerun()

        st.markdown('<div style="width: 32px; height: 1px; background: #e5e7eb; margin: 8px 0;"></div>', unsafe_allow_html=True)

        if current_ws_id:
            agents = workspace_manager.get_workspace_agents(current_ws_id)
            current_agent_id = st.session_state.get("current_agent", "")
            
            for agent in agents:
                agent_id = agent["id"]
                agent_name = agent.get("name", agent_id)
                icon = agent_name.strip()[0].upper() if agent_name else "?"
                is_active = (agent_id == current_agent_id)
                
                if st.button(icon, key=f"mini_ag_{agent_id}", help=agent_name, type="primary" if is_active else "secondary"):
                    st.session_state["current_agent"] = agent_id
                    st.rerun()

        # Settings Button (Positioned at bottom)
        st.markdown("""
            <style>
                /* 定位 Settings 按钮 */
                /* stHorizontalBlock > div(column) > div(vertical block) > ... */
                /* 这里我们直接选最后一个按钮 */
                div[data-testid="stHorizontalBlock"]:has(div.mini-sidebar-marker) .stButton:last-child {
                    margin-top: auto !important;
                    margin-bottom: 20px !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        # 这里的 Spacer Trick: 为了让 margin-top: auto 生效，容器高度必须是 100vh 且 flex
        # 我们在上面 CSS 已经设了 flex-direction: column 和 height: 100vh
        # 还需要确保中间没有元素阻断高度传递
        
        # 插入一个占位符推动之后的元素到底部？
        # 在 Streamlit 中，flex 布局有时会被中间的 div 截断。
        # 我们尝试用 CSS 修改中间容器样式
        st.markdown("""
        <style>
        div[data-testid="stHorizontalBlock"]:has(div.mini-sidebar-marker) > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] {
            height: 100% !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        if st.button("⚙️", key="mini_settings", help="Settings"):
             st.session_state["current_page"] = "Settings"
             st.rerun()