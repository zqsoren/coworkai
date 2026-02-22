"""
diff_viewer - Diff 审批卡片组件
渲染红绿差异对比视图 + Approve/Reject 按钮 (Prism Edition)
"""

import streamlit as st
import html
from src.core.file_manager import FileManager, ChangeRequest


def render_diff_lines(diff_lines: list[str]) -> str:
    """将 diff 行转换为 Prism 风格的 HTML"""
    # Split lines into left (deletions) and right (additions/unchanged)
    # 简单的左右分栏逻辑
    left_html = []
    right_html = []
    
    for line in diff_lines:
        safe_line = html.escape(line)
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            # Meta lines - shown on both sides or handled separately?
            # Let's put gray text on both
            left_html.append(f'<div style="color: #888;">{safe_line}</div>')
            right_html.append(f'<div style="color: #888;">{safe_line}</div>')
        elif line.startswith("-"):
            left_html.append(f'<div style="background: rgba(213,0,0,0.1); color: #D50000; display: inline-block; width: 100%;">{safe_line}</div>')
            right_html.append('<div style="height: 1.5em;"></div>') # Placeholder
        elif line.startswith("+"):
            left_html.append('<div style="height: 1.5em;"></div>') # Placeholder
            right_html.append(f'<div style="background: rgba(0,200,83,0.1); color: #00C853; display: inline-block; width: 100%;">{safe_line}</div>')
        else:
            # Unchanged
            left_html.append(f'<div style="color: #666;">{safe_line}</div>')
            right_html.append(f'<div style="color: #666;">{safe_line}</div>')

    return f"""
    <div class="diff-content">
        <div class="diff-left">
            {"".join(left_html)}
        </div>
        <div class="diff-right">
            {"".join(right_html)}
        </div>
    </div>
    """


def render_change_request(change_data: dict, index: int,
                          file_manager: FileManager) -> None:
    """
    渲染变更审批卡片 (Prism Style)
    """
    file_path = change_data.get("file_path", "Unknown File")
    diff_lines = change_data.get("diff", [])
    status = change_data.get("status", "pending")

    # 卡片容器
    with st.container():
        # Header
        st.markdown(
            f"""
            <div class="prism-card">
                <div class="diff-header">
                    <span>CHANGE REQUEST</span>
                    <span>{file_path}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Diff Content
        if diff_lines:
            diff_html = render_diff_lines(diff_lines)
            st.markdown(diff_html, unsafe_allow_html=True)
        else:
            st.info("New file (No diff).")

        # 按钮 (Only if pending)
        if status == "pending":
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("✅ Approve", key=f"approve_{index}",
                             type="primary", use_container_width=True):
                    _apply_change(change_data, index, file_manager)
                    st.rerun()
            with col2:
                if st.button("❌ Reject", key=f"reject_{index}",
                             type="secondary", use_container_width=True):
                    _reject_change(index)
                    st.rerun()
            with col3:
                comment = st.text_input(
                    "Comment", key=f"comment_{index}",
                    placeholder="Reason for rejection...",
                    label_visibility="collapsed",
                )
        elif status == "approved":
            st.success("✅ Approved & Applied")
        elif status == "rejected":
            st.error("❌ Rejected")


def _apply_change(change_data: dict, index: int,
                  file_manager: FileManager) -> None:
    """批准并应用变更"""
    cr = ChangeRequest(
        file_path=change_data["file_path"],
        original_content=change_data.get("original_content", ""),
        new_content=change_data.get("new_content", ""),
        diff_lines=change_data.get("diff", []),
        status="approved",
    )
    try:
        file_manager.apply_change(cr)
        st.session_state.pending_changes[index]["status"] = "approved"
        st.toast("✅ Change Applied!", icon="✅")
    except Exception as e:
        st.error(f"Failed to apply: {e}")


def _reject_change(index: int) -> None:
    """拒绝变更"""
    if index < len(st.session_state.get("pending_changes", [])):
        st.session_state.pending_changes[index]["status"] = "rejected"
        st.toast("❌ Change Rejected", icon="❌")
