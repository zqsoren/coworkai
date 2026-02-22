"""
sidebar - Sidebar Component
Workspace Selector + Agent List + Quick Actions (Prism Edition)
"""

import streamlit as st
import json
import os
from datetime import datetime


def render_sidebar(workspace_manager, agent_registry, file_manager, meta_agent):
    """Render the Sidebar with new Prism Design (3-Section Hierarchy)"""
    from src.utils.i18n import i18n
    
    # Define current_page at function level to ensure availability
    current_page = st.session_state.get("current_page", "Orchestrate")
    
    with st.sidebar:
        # 1. Header: AgentOS (Prism Edition) + Collapse Button
        # Layout: [Title (0.8)] [Collapse (0.2)]
        h_col1, h_col2 = st.columns([0.8, 0.2])
        
        with h_col1:
            st.markdown(
                f"""
                <div style="margin-bottom: 24px; padding-left: 8px;">
                    <h1 style="font-size: 20px; font-weight: 700; margin: 0; color: #1e293b; letter-spacing: -0.5px;">
                        {i18n.t("sidebar.title")}
                    </h1>
                    <p style="font-size: 10px; color: #94a3b8; font-weight: 600; letter-spacing: 1px; margin-top: 4px; text-transform: uppercase;">
                        {i18n.t("sidebar.edition")}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        with h_col2:
            # Custom Collapse Button
            if st.button("«", key="btn_collapse_sidebar", help="Collapse Sidebar"):
                st.session_state["sidebar_state"] = "collapsed"
                st.rerun()

        # ---------------------------------------------------------
        # SECTION 1: GLOBAL NAVIGATION (Views) - REMOVED PER USER REQUEST
        # ---------------------------------------------------------
        # Orchestrate, Files, Logs
        # User requested to remove these buttons. 
        # Default page is "Orchestrate" (Chat).
        # Settings is accessible at bottom, with a new Back button added there.
        
        current_page = st.session_state.get("current_page", "Orchestrate")
        
        # nav_items = [
        #     {"label": "Orchestrate", "i18n_key": "sidebar.orchestrate"},
        #     {"label": "Files", "i18n_key": "sidebar.files"},
        #     {"label": "Logs", "i18n_key": "sidebar.logs"}
        # ]
        # 
        # for item in nav_items:
        #     label = i18n.t(item['i18n_key'])
        #     key = f"nav_{item['label'].lower()}"
        #     is_active = (current_page == item['label'])
        #     
        #     if st.button(label, key=key, use_container_width=True, 
        #                  type="primary" if is_active else "secondary"):
        #         st.session_state["current_page"] = item['label']
        #         st.rerun()
                
        # st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)


        # ---------------------------------------------------------
        # SECTION 2: WORKSPACES
        # ---------------------------------------------------------
        # Header with Add Button
        col_ws_header, col_ws_add = st.columns([0.8, 0.2])
        with col_ws_header:
            st.markdown(f'<div class="sidebar-header">{i18n.t("sidebar.workspaces")}</div>', unsafe_allow_html=True)
        with col_ws_add:
            if st.button(i18n.t("sidebar.workspace_new"), key="btn_add_workspace", help="Create New Workspace"):
                st.session_state["show_create_ws_input"] = not st.session_state.get("show_create_ws_input", False)

        # Create Workspace Input (Toggleable)
        if st.session_state.get("show_create_ws_input"):
            new_ws_name = st.text_input(i18n.t("sidebar.workspace_create_input"), key="input_new_ws_name", placeholder="Project Alpha")
            if st.button(i18n.t("sidebar.workspace_create_btn"), key="btn_confirm_create_ws"):
                if new_ws_name:
                    try:
                        new_id = workspace_manager.create_workspace(new_ws_name)
                        st.session_state["current_workspace"] = new_id
                        st.session_state["show_create_ws_input"] = False
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        # List Workspaces
        # Get current workspace info
        current_ws = st.session_state.get("current_workspace", "")
        workspaces = workspace_manager.list_workspaces()
        
        # If no workspace selected, try to select default
        if not current_ws and workspaces:
            st.session_state["current_workspace"] = workspaces[0]["id"]
            current_ws = workspaces[0]["id"]
            st.rerun()

        for ws in workspaces:
            ws_id = ws["id"]
            ws_name = ws.get("name", ws_id)
            is_active = (current_ws == ws_id)
            
            # Layout: [Button (0.85)] [Menu (0.15)]
            c1, c2 = st.columns([0.85, 0.15])
            
            with c1:
                # Label with indicator for active
                label = f"{ws_name}"
                if st.button(label, key=f"ws_nav_{ws_id}", use_container_width=True,
                             type="primary" if is_active else "secondary"):
                    if not is_active:
                        st.session_state["current_workspace"] = ws_id
                        st.session_state["current_agent"] = None
                        st.rerun()
            
            with c2:
                # Popover Menu
                with st.popover("⋮", help="更多操作"):
                    # Rename
                    new_name = st.text_input("重命名", value=ws_name, key=f"rename_ws_input_{ws_id}")
                    if st.button("确认重命名", key=f"btn_rename_ws_{ws_id}"):
                        workspace_manager.rename_workspace(ws_id, new_name)
                        st.rerun()
                    
                    # Delete (Protect Default)
                    if ws_id != workspace_manager.DEFAULT_WORKSPACE:
                        st.divider()
                        if st.button("🗑️ 删除工作区", key=f"btn_del_ws_{ws_id}", type="primary"):
                            try:
                                workspace_manager.delete_workspace(ws_id)
                                if is_active:
                                    st.session_state["current_workspace"] = None
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

        st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)


        # ---------------------------------------------------------
        # SECTION 3: CONTEXT AGENTS
        # ---------------------------------------------------------
        if current_ws:
            ws_display_name = current_ws.replace("workspace_", "").upper()
            
            # Find current ws name for display if available
            curr_ws_obj = next((w for w in workspaces if w["id"] == current_ws), None)
            if curr_ws_obj:
                ws_display_name = curr_ws_obj.get("name", ws_display_name)
                
            agents_header = f"{i18n.t('sidebar.agents')} ({ws_display_name})"
            st.markdown(f'<div class="sidebar-header">{agents_header}</div>', unsafe_allow_html=True)
            
            agents = workspace_manager.get_workspace_agents(current_ws)
            if agents:
                selected_agent_id = st.session_state.get("current_agent")
                
                for agent in agents:
                    agent_id = agent["id"]
                    agent_name = agent.get("name", agent_id)
                    tags = agent.get("tags", [])
                    role = tags[0] if tags else "General Agent"
                    
                    is_selected = (selected_agent_id == agent_id)
                    
                    # Layout: [Button (0.85)] [Menu (0.15)]
                    ac1, ac2 = st.columns([0.85, 0.15])
                    
                    with ac1:
                        label = f"{agent_name}\n      {role}" 
                        if st.button(label, key=f"agent_nav_{agent_id}", use_container_width=True,
                                     type="secondary"): 
                            st.session_state["current_agent"] = agent_id
                            st.session_state["agent_config"] = agent
                            st.session_state["chat_messages"] = [] 
                            st.rerun()
                            
                    with ac2:
                        # Popover Menu
                        with st.popover("⋮", help="更多操作"):
                            # Rename
                            new_agent_name = st.text_input("重命名", value=agent_name, key=f"rename_agent_input_{agent_id}")
                            if st.button("确认", key=f"btn_rename_agent_{agent_id}"):
                                meta_agent.rename_agent(current_ws, agent_id, new_agent_name)
                                st.rerun()
                                
                            st.divider()
                            # Delete
                            if st.button("🗑️ 删除 Agent", key=f"btn_del_agent_{agent_id}", type="primary"):
                                meta_agent.delete_agent(current_ws, agent_id)
                                if is_selected:
                                    st.session_state["current_agent"] = None
                                st.rerun()

            else:
                st.caption(i18n.t("sidebar.agent_no_agents"))
                
            # Quick Action: Add Agent
            if st.button(i18n.t("sidebar.agent_new"), key="quick_add_agent"):
                _show_create_agent_dialog(workspace_manager, meta_agent)

        else:
             st.info("No workspace selected.")

        # ---------------------------------------------------------
        # FOOTER / SETTINGS
        # ---------------------------------------------------------
        st.markdown("<div style='margin-top: auto;'></div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top: 48px;'></div>", unsafe_allow_html=True)
        
        if st.button(i18n.t("sidebar.settings"), key="nav_settings", use_container_width=True,
                     type="primary" if current_page == "Settings" else "secondary"):
            st.session_state["current_page"] = "Settings"
            st.rerun()


@st.dialog("Create Agent")
def _show_create_agent_dialog(workspace_manager, meta_agent):
    """Agent Creation Dialog — 弹窗式创建"""
    from src.core.llm_manager import LLMManager
    from src.utils.i18n import i18n
    
    # st.dialog decorator string dynamic change is tricky, assumes static string
    # We can rely on content inside being dynamic.
    
    st.markdown(f"### {i18n.t('dialog.create_agent')}")

    current_ws = st.session_state.get("current_workspace", "")
    if not current_ws:
        st.warning("请先选择一个工作区")
        return

    # 1. Agent Name
    agent_name = st.text_input(i18n.t("dialog.agent_name"), placeholder="例如: 财务分析师")

    # 2. Model Selectbox (from LLMManager)
    mgr = LLMManager()
    all_models = mgr.list_all_models()

    if all_models:
        model_options = [m["display"] for m in all_models]
        selected_idx = st.selectbox(
            i18n.t("dialog.model_select"),
            range(len(model_options)),
            format_func=lambda i: model_options[i],
            help="只显示在 Settings 中已配置的供应商和模型"
        )
        selected_model = all_models[selected_idx]
    else:
        st.warning("⚠️ 尚未配置任何模型供应商。请先到 Settings 添加。")
        selected_model = None

    # 3. System Prompt
    system_prompt = st.text_area(
        i18n.t("dialog.system_prompt"),
        placeholder="你是一个专业的财务分析师，擅长数据分析和报表生成...",
        height=200
    )

    # Submit
    col1, col2 = st.columns(2)
    with col1:
        if st.button(i18n.t("dialog.cancel"), use_container_width=True):
            st.rerun()
    with col2:
        if st.button(i18n.t("dialog.create"), type="primary", use_container_width=True):
            if not agent_name:
                st.error("名称不能为空")
                return
            if not selected_model:
                st.error("请先配置模型供应商")
                return

            agent_id = f"agent_{agent_name.lower().replace(' ', '_').replace('-', '_')}"
            prompt = system_prompt if system_prompt else f"你是一个 {agent_name}。"

            try:
                meta_agent.create_agent(
                    workspace_id=current_ws,
                    agent_id=agent_id,
                    name=agent_name,
                    role_desc=prompt,
                    provider_id=selected_model["provider_id"],
                    model_name=selected_model["model_name"]
                )
                st.success(f"{agent_name} {i18n.t('dialog.success')}")
                st.rerun()
            except Exception as e:
                st.error(f"创建失败: {e}")

