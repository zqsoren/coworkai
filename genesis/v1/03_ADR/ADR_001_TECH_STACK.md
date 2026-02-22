# ADR 001: Technology Stack Selection

**Status**: Accepted
**Date**: 2026-02-10
**Context**: AgentOS v1

## Context
构建一个本地运行的多智能体平台，需支持浏览器自动化、代码执行和文件系统操作。

## Decision

### 1. Frontend: Streamlit (Latest)
- **用途**: 主应用界面。
- **配置**: `localhost:8501`。
- **关键组件**: `st.chat_message`, `st.columns` (3-column layout), `st.expander` (Agent list).

### 2. Orchestration: LangGraph
- **用途**: 管理多智能体状态机。
- **特性**: 支持循环、条件边缘、持久化状态。

### 3. Browser Automation: Playwright (CDP Mode)
- **用途**: "Browser Takeover" 技能。
- **机制**: 连接到已存在的 Chrome 实例 (Port 9222)。
- **优势**: 无需用户重复登录，共享 Cookie/Session。

### 4. LLM Interface: LangChain
- **用途**: 模型统一接口。
- **支持**: Gemini, OpenAI, Anthropic。

### 5. Local Automation: Python Std Lib
- **os/shutil**: 文件操作。
- **difflib**: 生成审批用的差异对比。
- **json**: 配置存储。

## Consequences
- 必须确保用户 Chrome 以 `--remote-debugging-port=9222` 启动。
- Streamlit 的无状态特性要求我们在 `st.session_state` 中仔细管理 LangGraph 的状态快照。
