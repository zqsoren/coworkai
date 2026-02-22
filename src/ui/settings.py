"""
settings - LLM Provider 管理与配置
"""

import streamlit as st
import toml
import os
from src.core.llm_manager import LLMManager, LLMProvider

def render_settings():
    """渲染设置面板"""
    # Navigation: Back to Chat
    if st.button("⬅️ 返回聊天 (Back to Chat)", key="btn_back_from_settings", type="secondary"):
        st.session_state["current_page"] = "Orchestrate"
        st.rerun()
        
    st.markdown("### 设置")

    # API Key 配置 (Global)
    with st.expander("全局 API Key (可选)", expanded=False):
        st.info("某些 Provider (如 Gemini Default) 会使用这里的全局 Key。自定义 Provider 可以单独配置 Key。")
        _render_api_keys()

    st.divider()

    # Provider 管理
    st.markdown("### 模型提供商 (LLM Providers)")
    
    mgr = LLMManager()
    
    # 1. 添加新 Provider
    with st.expander("添加新提供商", expanded=False):
        _render_add_provider(mgr)

    # 2. 现有 Provider 列表
    for p_id, provider in mgr.providers.items():
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{provider.name}** ({provider.type})")
                st.caption(f"ID: `{provider.id}` | Models: {', '.join(provider.models)}")
                if provider.base_url:
                    st.caption(f"Base URL: `{provider.base_url}`")
                st.caption(f"API Key Env: `{provider.api_key_env}`")
            
            with col2:
                if st.button("🔌 测试", key=f"test_{p_id}"):
                    success, msg = mgr.test_connection(p_id)
                    if success:
                        st.toast(f"✅ {provider.name}: {msg}", icon="✅")
                    else:
                        st.error(f"❌ 连接失败: {msg}")
            
            with col3:
                # 默认 Provider 不允许删除 (简单起见，或者根据 ID 判断)
                # 其实用户可能有强烈的删除需求，哪怕是默认的。这里允许删除。
                if st.button("🗑️ 删除", key=f"del_{p_id}"):
                    mgr.remove_provider(p_id)
                    st.rerun()

def _render_add_provider(mgr: LLMManager):
    """添加 Provider 表单"""
    with st.form("add_provider_form"):
        p_type = st.selectbox("类型", ["gemini", "openai_compatible", "openai", "anthropic"])
        name = st.text_input("名称 (Display Name)", value="My Custom Provider")
        p_id = st.text_input("ID (Unique)", value="custom_provider").strip()
        base_url = st.text_input("Base URL (Optional)", help="Gemini 中转站URL 或 Ollama URL (e.g. http://localhost:11434/v1)")
        
        # Base URL Validation Hint
        if base_url and p_type == "gemini":
            if "generateContent" in base_url or "/models/" in base_url:
                st.warning("⚠️ Base URL 似乎包含了具体模型路径。请只保留服务器地址 (例如 `https://api.relay.com`)，不要包含 `/models/xxx`。")
            if "https://" in base_url and base_url.count("/") > 3:
                 st.info("💡 提示：Gemini Base URL 通常只需填域名，不需要很长的路径后缀。")
        api_key_env = st.text_input("API Key Env Var Name", value="CUSTOM_GEMINI_KEY", help="secrets.toml 中存储 Key 的变量名。")
        api_key_value = st.text_input("API Key Value (Direct Input)", type="password", help="在此直接输入 Key，会自动保存到 secrets.toml 中对应的变量名下。")
        models_str = st.text_input("Models (逗号分隔)", value="gemini-1.5-pro,gemini-2.0-flash")
        
        submitted = st.form_submit_button("保存")
        if submitted:
            if not p_id:
                st.error("ID 不能为空")
                return
            if p_id in mgr.providers:
                st.error("ID 已存在")
                return
            
            # 自动保存 Key 到 secrets
            if api_key_value:
                secrets = _load_secrets()
                secrets.setdefault("llm", {})
                secrets["llm"][api_key_env] = api_key_value
                _save_secrets(secrets)
                st.toast(f"✅ Key 已保存到 secrets.toml ([llm] {api_key_env})")
            
            models = [m.strip() for m in models_str.split(",") if m.strip()]
            new_p = LLMProvider(
                id=p_id,
                type=p_type,
                name=name,
                base_url=base_url if base_url else None,
                api_key_env=api_key_env,
                models=models
            )
            mgr.add_provider(new_p)
            st.success(f"已添加 {name}")
            st.rerun()

def _render_api_keys():
    """API Key 配置表单 (Legacy/Global)"""
    secrets = _load_secrets()
    llm_secrets = secrets.get("llm", {})

    gemini_key = st.text_input(
        "Gemini API Key",
        value=llm_secrets.get("gemini_api_key", ""),
        type="password",
        key="settings_gemini_key",
    )
    openai_key = st.text_input(
        "OpenAI API Key",
        value=llm_secrets.get("openai_api_key", ""),
        type="password",
        key="settings_openai_key",
    )
    anthropic_key = st.text_input(
        "Anthropic API Key",
        value=llm_secrets.get("anthropic_api_key", ""),
        type="password",
        key="settings_anthropic_key",
    )
    tavily_key = st.text_input(
        "Tavily Search API Key",
        value=secrets.get("search", {}).get("tavily_api_key", ""),
        type="password",
        key="settings_tavily_key",
    )

    if st.button("💾 保存 Global Keys", type="primary", key="save_keys"):
        secrets.setdefault("llm", {})
        secrets["llm"]["gemini_api_key"] = gemini_key
        secrets["llm"]["openai_api_key"] = openai_key
        secrets["llm"]["anthropic_api_key"] = anthropic_key
        secrets.setdefault("search", {})
        secrets["search"]["tavily_api_key"] = tavily_key
        _save_secrets(secrets)
        st.toast("✅ API Keys 已保存！", icon="✅")

def _load_secrets():
    """加载 secrets.toml"""
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        return toml.load(secrets_path)
    return {}

def _save_secrets(secrets):
    """保存 secrets.toml"""
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".streamlit", "secrets.toml")
    os.makedirs(os.path.dirname(secrets_path), exist_ok=True)
    with open(secrets_path, "w", encoding="utf-8") as f:
        toml.dump(secrets, f)
