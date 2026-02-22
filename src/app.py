"""
AgentOS - 本地多智能体编排平台
Streamlit 主入口文件

启动命令: streamlit run src/app.py
"""

import os
import sys

# 确保项目根目录在 Python 路径中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import streamlit.components.v1 as components

# 页面配置（必须在第一个 st 调用之前）
# Dynamic Sidebar State: Controlled by Mini Sidebar expand button
# sidebar_state 默认为 expanded，但在 Mini Sidebar 模式下会被设为 collapsed（由用户手动收起触发）
# 当用户点击 Mini Sidebar 展开按钮时，我们将其设为 expanded 并 rerun
if "sidebar_state" not in st.session_state:
    st.session_state["sidebar_state"] = "expanded"

sidebar_state = st.session_state["sidebar_state"]

st.set_page_config(
    page_title="AgentOS - 多智能体编排平台",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state=sidebar_state,
)

# 注意：我们不再自动重置 sidebar_state 为 auto
# 这样保证 rerun 后状态持续生效。
# Streamlit 的 initial_sidebar_state 只在页面加载或 rerun 时生效一次。
# 如果用户手动收起侧边栏，Streamlit 内部状态会变，但 session_state 不会自动变（除非我们监听）。
# 但在这里，只要我们强制 set_page_config(expanded)，Streamlit 就会尝试展开它。

from src.core.file_manager import FileManager
from src.core.workspace import WorkspaceManager
from src.core.agent_registry import AgentRegistry
from src.tools.file_tools import init_file_tools
from src.skills.skill_loader import SkillLoader
from src.ui.sidebar import render_sidebar
from src.ui.mini_sidebar import render_mini_sidebar
from src.ui.chat import render_chat
from src.ui.context_panel import render_context_panel
from src.ui.settings import render_settings


# ============================================================
# 全局初始化（仅在首次加载时执行）
# ============================================================
@st.cache_resource
def init_platform():
    """初始化平台核心组件（缓存，仅执行一次）"""
    data_root = os.path.join(PROJECT_ROOT, "data")
    config_dir = os.path.join(PROJECT_ROOT, "config")
    custom_skills_dir = os.path.join(PROJECT_ROOT, "custom_skills")

    # 核心组件
    fm = FileManager(data_root)
    wm = WorkspaceManager(fm)
    ar = AgentRegistry(os.path.join(config_dir, "agents_registry.json"))

    # 确保默认工作区存在
    wm.ensure_default_workspace()

    # 初始化文件工具
    init_file_tools(fm)

    # Initialize Meta-Agent and Tools
    from src.core.meta_agent import MetaAgent
    from src.tools.meta_tools import init_meta_tools
    meta_agent = MetaAgent(fm, ar)
    init_meta_tools(meta_agent)

    # 加载自定义技能
    sl = SkillLoader(custom_skills_dir)
    skill_count = sl.scan_and_load()
    print(f"[AgentOS] 已加载 {skill_count} 个自定义技能")

    return fm, wm, ar, sl, meta_agent


# ============================================================
# 自定义 CSS
# ============================================================
def inject_custom_css():
    css_file = os.path.join(PROJECT_ROOT, "src", "assets", "style.css")
    with open(css_file, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ============================================================
# 主应用
# ============================================================
def main():
    # 初始化 session state
    if "show_right_panel" not in st.session_state:
        st.session_state["show_right_panel"] = False # Default closed
    
    inject_custom_css()

    # 初始化平台
    fm, wm, ar, sl, meta_agent = init_platform()
    
    # 初始化 I18n
    from src.utils.i18n import I18nManager
    if "language" not in st.session_state:
        st.session_state["language"] = "zh"

    # 初始化其他 session state
    if "current_workspace" not in st.session_state:
        workspaces = wm.list_workspaces()
        st.session_state["current_workspace"] = (
            workspaces[0]["id"] if workspaces else ""
        )
    
    if st.session_state["current_workspace"]:
        pass # Shared dirs reverted
    if "current_agent" not in st.session_state:
        st.session_state["current_agent"] = ""
    if "agent_config" not in st.session_state:
        st.session_state["agent_config"] = {}
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []
    if "pending_changes" not in st.session_state:
        st.session_state["pending_changes"] = []
    if "_file_manager" not in st.session_state:
        st.session_state["_file_manager"] = fm
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Orchestrate"

    # === 左侧栏 (Control Tower) ===
    # 互斥渲染逻辑：
    # 如果状态是 expanded，只渲染原生 Sidebar（Mini Sidebar 代码不执行）
    # 如果状态是 collapsed，只渲染 Mini Sidebar（原生 Sidebar 内容不渲染，避免后台资源占用）
    current_sidebar_state = st.session_state.get("sidebar_state", "expanded")
    
    if current_sidebar_state == "expanded":
        render_sidebar(wm, ar, fm, meta_agent)
        
        # 强制展开脚本 (Force Expand Script)
        # 当处于 "expanded" 模式时，强制保持原生 Sidebar 展开。
        # 如果用户之前手动收起过，Streamlit 会记住 collapsed 状态，这里通过 JS 纠正它。
        # 同时，这也能防止用户通过原生方式收起（一收起就会自动弹开），引导用户使用我们的 "<<" 按钮。
        components.html("""
        <script>
            function forceExpand() {
                try {
                    const doc = window.parent.document;
                    const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                    
                    if (sidebar && sidebar.getAttribute('aria-expanded') === "false") {
                        // 尝试点击所有可能的展开按钮
                        const selectors = [
                            '[data-testid="stSidebarCollapsedControl"]',
                            'button[aria-label="Expand sidebar"]',
                            'header[data-testid="stHeader"] button'
                        ];
                        
                        for (const sel of selectors) {
                            const btn = doc.querySelector(sel);
                            if (btn) {
                                btn.click();
                                break;
                            }
                        }
                    }
                } catch (e) {
                    console.error("Force expand error:", e);
                }
            }
            
            // 启动轮询：每 500ms 检查一次，确保持续展开
            setInterval(forceExpand, 500);
        </script>
        """, height=0, width=0)
    else:
        render_mini_sidebar(wm)


    # === 顶部语言切换 (Language Toggle) ===
    # 使用 columns 将按钮放置在右上角
    # [Main Content] [Spacer] [Toggle]
    # 注意: Streamlit 的布局限制，我们需要在 sidebar 渲染后立即处理主区域
    # 为了不影响下方布局，我们放置一个容器

    top_col1, top_col2 = st.columns([0.92, 0.08])
    with top_col2:
        current_lang = I18nManager.get_current_locale()
        # Toggle Logic
        btn_label = "EN" if current_lang == "zh" else "中"
        if st.button(btn_label, key="lang_toggle", help="Switch Language"):
            new_lang = "en" if current_lang == "zh" else "zh"
            I18nManager.set_locale(new_lang)
            st.rerun()

    # === 主内容区 (Main Stage & Live Projection) ===
    # Pages: "Orchestrate" (default), "Files", "Logs"
    current_page = st.session_state.get("current_page", "Orchestrate")
    
    # Mapping for backward compatibility if needed, though we should be using English keys now.
    if current_page == "Settings":
        render_settings()
        
    elif current_page == "Files":
        st.header("Files & Context")
        # In Files view, we show the File Manager / Context Panel full width or as main interaction
        render_context_panel(fm)
        
    elif current_page == "Logs":
        st.header("System Logs")
        st.info("Log viewer module is under construction.")
        
    else:
        # Default: Orchestrate (Chat + Persistent Right Panel)
        # "Orchestrate" is the main chat interface
        
        # Always Visible layout: [Chat Area] | [Spacer] | [Right Context Panel]
        # Ratio: 3.5 : 0.2 : 1 
        chat_col, spacer_col, panel_col = st.columns([3.5, 0.2, 1])
        
        with chat_col:
            render_chat(fm)
        
        # Spacer col is empty
        
        with panel_col:
            # Persistent Context Panel
            render_context_panel(fm)


if __name__ == "__main__":
    main()
