"""
i18n - Internationalization Manager
Handles language switching (zh/en) and text translation.
"""

import streamlit as st

# Translation Dictionary
TRANSLATIONS = {
    "zh": {
        # Sidebar
        "sidebar.title": "AgentOS",
        "sidebar.edition": "Prism Edition",
        "sidebar.workspaces": "工作区",
        "sidebar.workspace_new": "new",
        "sidebar.workspace_create_input": "新工作区名称",
        "sidebar.workspace_create_btn": "创建",
        "sidebar.agents": "智能体列表",
        "sidebar.agent_new": "新建 Agent",
        "sidebar.agent_no_agents": "暂无智能体。",
        "sidebar.settings": "设置",
        "sidebar.orchestrate": "编排",
        "sidebar.files": "文件",
        "sidebar.logs": "日志",

        # Chat
        "chat.welcome_title": "Hello, {name}",
        "chat.welcome_subtitle": "需要我为你做些什么？",
        "chat.input_placeholder": "问问 {name}...",
        "chat.thinking": "思考中",
        "chat.building": "构建中",
        "chat.outputting": "输出中",
        "chat.agent_error": "⚠️ 调用失败: {error}\n\n请检查 API Key。",
        "chat.change_request": "已生成文件变更请求，请在右侧面板查看详情。",

        # Context Panel
        "panel.kb_btn": "知识库",
        "panel.settings": "Agent 设定",
        "panel.static": "静态资源库",
        "panel.active": "动态项目文档",
        "panel.archives": "归档与交付",
        "panel.upload_drag": "拖拽文件到此处",
        "panel.upload_limit": "支持每个文件 200MB • txt, md, py, json, pdf...",
        "panel.close": "关闭面板 ◧",
        "panel.open": "打开面板 ◨",
        
        # Agent Settings
        "settings.save": "💾 保存设定",
        "settings.saved": "✅ Agent 设定已保存",
        "settings.name": "名称",
        "settings.prompt": "System Prompt",
        "settings.model": "模型",

        # Dialogs
        "dialog.create_agent": "创建新 Agent",
        "dialog.agent_name": "Agent 名称",
        "dialog.model_select": "接入模型",
        "dialog.system_prompt": "人物设定 (System Prompt)",
        "dialog.cancel": "取消",
        "dialog.create": "创建",
        "dialog.success": "创建成功！",
    },
    "en": {
        # Sidebar
        "sidebar.title": "AgentOS",
        "sidebar.edition": "Prism Edition",
        "sidebar.workspaces": "WORKSPACES",
        "sidebar.workspace_new": "new",
        "sidebar.workspace_create_input": "New Workspace Name",
        "sidebar.workspace_create_btn": "Create",
        "sidebar.agents": "AGENTS",
        "sidebar.agent_new": "New Agent",
        "sidebar.agent_no_agents": "No agents found.",
        "sidebar.settings": "Settings",
        "sidebar.orchestrate": "Orchestrate",
        "sidebar.files": "Files",
        "sidebar.logs": "Logs",

        # Chat
        "chat.welcome_title": "Hello, {name}",
        "chat.welcome_subtitle": "How can I help you today?",
        "chat.input_placeholder": "Message {name}...",
        "chat.thinking": "Thinking",
        "chat.building": "Building",
        "chat.outputting": "Outputting",
        "chat.agent_error": "⚠️ Error: {error}\n\nPlease check API Key.",
        "chat.change_request": "📋 Change request generated. Check the right panel.",

        # Context Panel
        "panel.kb_btn": "Knowledge Base",
        "panel.settings": "Agent Settings",
        "panel.static": "Static Assets",
        "panel.active": "Active Docs",
        "panel.archives": "Archives",
        "panel.upload_drag": "Drag and drop files here",
        "panel.upload_limit": "Limit 200MB per file • txt, md, py, json, pdf...",
        "panel.close": "Close Panel ◧",
        "panel.open": "Open Context ◨",

        # Agent Settings
        "settings.save": "💾 Save Settings",
        "settings.saved": "✅ Settings Saved",
        "settings.name": "Name",
        "settings.prompt": "System Prompt",
        "settings.model": "Model",

        # Dialogs
        "dialog.create_agent": "Create New Agent",
        "dialog.agent_name": "Agent Name",
        "dialog.model_select": "Select Model",
        "dialog.system_prompt": "System Prompt",
        "dialog.cancel": "Cancel",
        "dialog.create": "Create",
        "dialog.success": "Created successfully!",
    }
}


class I18nManager:
    """国际化管理器"""

    @staticmethod
    def get_current_locale():
        """获取当前语言代码 (zh/en)"""
        if "language" not in st.session_state:
            st.session_state["language"] = "zh"
        return st.session_state["language"]

    @staticmethod
    def set_locale(code: str):
        """切换语言"""
        if code in ["zh", "en"]:
            st.session_state["language"] = code

    @staticmethod
    def t(key: str, **kwargs) -> str:
        """
        获取翻译文本
        :param key: 翻译键 (e.g. 'sidebar.workspaces')
        :param kwargs: 格式化参数 (e.g. name='Agent')
        """
        lang = I18nManager.get_current_locale()
        
        # 获取语言字典，默认为中文
        lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["zh"])
        
        # 获取文本，如果 key 不存在则返回 key 本身
        text = lang_dict.get(key, key)
        
        # 格式化字符串 (如果有参数)
        if kwargs and isinstance(text, str):
            try:
                return text.format(**kwargs)
            except Exception:
                return text
                
        return text

# 全局实例
i18n = I18nManager()
