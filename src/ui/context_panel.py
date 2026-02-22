"""
context_panel - 右侧上下文面板 V2
功能：
1. Agent Settings (设置)
2. Knowledge Base (知识库)
3. Workspace Shared Files (工作区共享 - 支持文件锁)
4. Agent Private Files (Agent 私有 - 支持文件锁)
5. Archives (归档)
"""

import os
import streamlit as st
from src.core.file_manager import FileManager
from src.ui.diff_viewer import render_change_request
from src.utils.rag_ingestion import RAGIngestion

def render_context_panel(file_manager: FileManager):
    """渲染右侧上下文面板 V2"""
    from src.utils.i18n import i18n
    
    current_ws = st.session_state.get("current_workspace", "")
    current_agent = st.session_state.get("current_agent", "")

    if not current_ws or not current_agent:
        st.info("请选择一个工作区和 Agent")
        return

    # 0. 待审批变更 (最高优先级)
    _render_pending_changes(file_manager)

    st.markdown("### 🛠️ 控制台")
    
    col1, col2 = st.columns(2)
    with col1:
        # Settings Dialog Button
        if st.button("⚙️ 设置", key="btn_settings_dialog", use_container_width=True):
             _show_settings_dialog(current_ws, current_agent)
    with col2:
        # KB Dialog Button
        if st.button("📚 知识库", key="btn_kb_dialog", use_container_width=True, type="primary"):
            _show_knowledge_base_dialog(file_manager, current_ws, current_agent)

    st.divider()

    # 1. 工作区共享文件 (Shared)
    st.markdown("#### 🌐 工作区共享文件")
    shared_root = file_manager.ensure_workspace_shared_dirs(current_ws)
    # shared_root is data/{ws}/
    # We want to show data/{ws}/shared/
    shared_dir = os.path.join(shared_root, "shared")
    
    _render_file_tree_zone(file_manager, shared_dir, "shared_zone", allow_lock=True)

    st.divider()

    # 2. Agent 私有文件 (Private)
    st.markdown("#### 🔒 Agent 私有文件")
    agent_root = file_manager.ensure_agent_dirs(current_ws, current_agent)
    # agent_root is data/{ws}/{agent}
    # We want to show the root of agent dir, EXCLUDING archives/kb/vector
    
    _render_file_tree_zone(
        file_manager, agent_root, "private_zone", 
        allow_lock=True, 
        exclude_dirs=["archives", "knowledge_base", "vector_store", "context"]
    )

    st.divider()

    # 3. 归档文件 (Archives)
    st.markdown("#### 🗄️ 归档文件")
    archives_dir = os.path.join(agent_root, "archives")
    _render_file_tree_zone(file_manager, archives_dir, "archives_zone", allow_lock=False)


def _render_file_tree_zone(file_manager: FileManager, root_path: str, zone_key: str, allow_lock: bool, exclude_dirs=None):
    """渲染文件树区域"""
    if exclude_dirs is None:
        exclude_dirs = []

    # Upload & New Folder
    c1, c2 = st.columns([0.7, 0.3])
    with c1:
        uploaded = st.file_uploader(
            "Upload",
            key=f"upload_{zone_key}",
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
    with c2:
        start_create = st.button("➕ 文件夹", key=f"new_folder_btn_{zone_key}", use_container_width=True)

    if start_create:
        st.session_state[f"creating_folder_{zone_key}"] = True

    if st.session_state.get(f"creating_folder_{zone_key}", False):
        new_folder_name = st.text_input("文件夹名称", key=f"input_folder_{zone_key}")
        col_ok, col_cancel = st.columns(2)
        with col_ok:
            if st.button("确认创建", key=f"confirm_folder_{zone_key}"):
                if new_folder_name:
                    new_path = os.path.join(root_path, new_folder_name)
                    try:
                        file_manager.create_directory(new_path)
                        st.toast(f"文件夹已创建: {new_folder_name}")
                        st.session_state[f"creating_folder_{zone_key}"] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"创建失败: {e}")
        with col_cancel:
            if st.button("取消", key=f"cancel_folder_{zone_key}"):
                 st.session_state[f"creating_folder_{zone_key}"] = False
                 st.rerun()

    # Handle Uploads
    if uploaded:
        for f in uploaded:
            save_path = os.path.join(root_path, f.name)
            try:
                # Use FM write for safety/locking checks
                # Binary write is special, maybe direct os write is better here? 
                # FM.write_file deals with strings. 
                # For safety in V2, let's verify path first.
                resolved = file_manager._resolve_and_validate(save_path)
                with open(resolved, "wb") as out:
                    out.write(f.getbuffer())
                st.toast(f"✅ Uploaded: {f.name}")
            except Exception as e:
                st.error(f"上传失败: {e}")
        # Clear uploader? Streamlit quirk, requires key reset or rerun logic usually.
        # Minimal viable behavior here.

    # Render Tree
    _render_recursive_tree(file_manager, root_path, zone_key, allow_lock, exclude_dirs)


def _render_recursive_tree(file_manager, current_path, key_prefix, allow_lock, exclude_dirs):
    """递归渲染树"""
    try:
        items = file_manager.list_directory(current_path)
    except Exception:
        return

    if not items:
        st.caption("(Empty)")
        return

    for item in items:
        if item["name"] in exclude_dirs:
            continue
            
        # UI Row
        col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
        
        full_path = os.path.join(file_manager.data_root, item["path"])
        is_locked = item.get("locked", False)
        
        with col1:
            icon = "📁" if item["is_dir"] else ("🔒" if is_locked else "📄")
            label = f"{icon} {item['name']}"
            
            if item["is_dir"]:
                # Directory: Expander
                # Unique key is critical for recursion
                # Use current path hash or something to ensure uniqueness? key_prefix + name is good.
                if st.expander(label, expanded=False):
                    _render_recursive_tree(file_manager, full_path, f"{key_prefix}_{item['name']}", allow_lock, [])
            else:
                # File: Click to view
                if st.button(label, key=f"view_{key_prefix}_{item['name']}", use_container_width=True):
                    _show_file_viewer(file_manager, item["path"], item["name"])

        with col2:
            # Lock Toggle
            if allow_lock and not item["is_dir"]:
                lock_icon = "🔓" if is_locked else "🔒"
                help_text = "点击解锁" if is_locked else "点击上锁 (变为只读资源)"
                if st.button(lock_icon, key=f"lock_{key_prefix}_{item['name']}", help=help_text):
                    try:
                        file_manager.set_file_lock(item["path"], not is_locked)
                        st.rerun()
                    except Exception as e:
                        st.error(f"操作失败: {e}")

        with col3:
            # Delete
            if st.button("🗑️", key=f"del_{key_prefix}_{item['name']}", help="删除"):
                try:
                    # TODO: Add confirm dialog? For now direct delete.
                    tgt = file_manager._resolve_and_validate(item["path"])
                    if os.path.isdir(tgt):
                        import shutil
                        shutil.rmtree(tgt)
                    else:
                        os.remove(tgt)
                    st.rerun()
                except Exception as e:
                    st.error(f"删除失败: {e}")


# --- Popups ---

@st.dialog("⚙️ Agent 设置", width="large")
def _show_settings_dialog(current_ws: str, current_agent: str):
    """Settings Pop-up"""
    from src.core.llm_manager import LLMManager
    from src.core.agent_registry import AgentRegistry
    from src.utils.i18n import i18n

    registry_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config", "agents_registry.json"
    )
    registry = AgentRegistry(registry_path)
    agent_config = registry.get_agent(current_agent) or {}

    new_name = st.text_input(i18n.t("settings.name"), value=agent_config.get("name", current_agent))
    new_prompt = st.text_area(i18n.t("settings.prompt"), value=agent_config.get("system_prompt", ""), height=300)

    # Model Selection
    mgr = LLMManager()
    all_models = mgr.list_all_models()
    model_displays = [m["display"] for m in all_models]
    
    current_idx = 0
    for i, m in enumerate(all_models):
        if (m["provider_id"] == agent_config.get("provider_id") and
                m["model_name"] == agent_config.get("model_name")):
            current_idx = i
            break
            
    if all_models:
        selected_model_idx = st.selectbox(i18n.t("settings.model"), range(len(model_displays)), index=current_idx, format_func=lambda i: model_displays[i])
    else:
        st.write("No models available")
        selected_model_idx = -1

    if st.button(i18n.t("settings.save")):
        updates = {
            "name": new_name,
            "system_prompt": new_prompt
        }
        
        if selected_model_idx >= 0:
            updates["provider_id"] = all_models[selected_model_idx]["provider_id"]
            updates["model_name"] = all_models[selected_model_idx]["model_name"]

        registry.update_agent(current_agent, updates)
        
        # Update session
        current_config = st.session_state.get("agent_config", {})
        current_config.update(updates)
        st.session_state["agent_config"] = current_config
        
        st.toast(i18n.t("settings.saved"))
        st.rerun()


@st.dialog("📄 文件预览", width="large")
def _show_file_viewer(file_manager, rel_path, filename):
    """File Viewer"""
    st.caption(f"Path: `{rel_path}`")
    try:
        content = file_manager.read_file(rel_path)
        ext = os.path.splitext(filename)[1].lower()
        lang = {".py":"python", ".js":"javascript", ".json":"json", ".md":"markdown", ".csv":"csv"}.get(ext, "")
        st.code(content, language=lang) if lang else st.text(content)
    except Exception as e:
        st.error(f"Error: {e}")


@st.dialog("📚 知识库管理", width="large")
def _show_knowledge_base_dialog(file_manager, ws, agent):
    """Knowledge Base Manager"""
    kb_path = os.path.join(file_manager.data_root, ws, agent, "knowledge_base")
    os.makedirs(kb_path, exist_ok=True)
    
    st.info("上传文件到 RAG 知识库，供 Agent 检索使用。")
    
    uploaded = st.file_uploader("Upload Documents", accept_multiple_files=True)
    if uploaded:
        for f in uploaded:
            with open(os.path.join(kb_path, f.name), "wb") as out:
                out.write(f.getbuffer())
        st.toast(f"Uploaded {len(uploaded)} files")
        st.rerun()
        
    st.divider()
    
    files = sorted(os.listdir(kb_path)) if os.path.exists(kb_path) else []
    if files:
        for f in files:
            c1, c2 = st.columns([0.8, 0.2])
            c1.markdown(f"📄 {f}")
            if c2.button("🗑️", key=f"kb_del_{f}"):
                os.remove(os.path.join(kb_path, f))
                st.rerun()
    else:
        st.caption("No files yet.")
        
    st.divider()
    
    if st.button("⚡ 重建索引 (Rebuild Index)", type="primary"):
        with st.spinner("Indexing..."):
            try:
                ingestion = RAGIngestion(file_manager.data_root, ws, agent)
                ingestion.rebuild_all()
                st.success("Indexing Complete!")
            except Exception as e:
                st.error(f"Indexing Failed: {e}")


def _render_pending_changes(file_manager: FileManager):
    """渲染待审批变更列表"""
    pending = st.session_state.get("pending_changes", [])
    if not pending:
        return

    st.warning(f"🔔 有 {len(pending)} 条变更待审批")
    with st.expander("📋 审批变更", expanded=True):
        for i, change in enumerate(pending):
            if change.get("status") == "pending":
                render_change_request(change, i, file_manager)
