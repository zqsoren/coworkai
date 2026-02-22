# AgentOS - 本地多智能体编排平台

> 🧠 基于 Streamlit + LangGraph 的本地多智能体编排平台

## 快速开始

### 1. 环境搭建
```bash
# 方式一：运行一键安装脚本 (Windows)
scripts\setup_env.bat

# 方式二：手动安装
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置 API Key
启动后在 **⚙️ 设置** 页面填入你的 API Key，或直接编辑 `.streamlit/secrets.toml`：
```toml
[llm]
gemini_api_key = "your-key-here"
```

### 3. 启动
```bash
streamlit run src/app.py
```
浏览器访问 `http://localhost:8501`

## 目录结构
```
agentOS/
├── .streamlit/          # Streamlit 配置
├── config/              # Agent 注册表
├── data/                # 数据根目录 (Root Lock)
│   └── workspace_xxx/   # 工作区
│       └── agent_yyy/   # Agent
│           ├── static/  # 🔒 静态资产 (只读)
│           ├── active/  # 📝 动态文档 (读写+审批)
│           └── output/  # 🗂 归档输出 (仅写入)
├── custom_skills/       # 用户自定义技能
└── src/                 # 源代码
```

## 三层权限模型
| 目录 | 权限 | 用途 |
|------|------|------|
| `static/` | 🔒 READ-ONLY | 不可变资产（模板、品牌素材） |
| `active/` | 📝 READ-WRITE (Diff 审批) | 项目真实数据源 |
| `output/` | 🗂 WRITE/APPEND | 临时输出、草稿、历史版本 |

## 高级用法

### 1. Meta-Agent (智能体孵化器)
系统内置了 `meta_agent`，它可以帮你创建新的 Agent。
- 在侧栏选择 `workspace_default` -> `meta_agent`。
- 对话示例：“帮我创建一个 Python 专家 Agent，擅长写爬虫。”
- Meta-Agent 会自动生成配置文件并初始化目录。

### 2. 文件变更审批
当 Agent 尝试修改 `active/` 目录下的文件时，会自动触发审批流程。
- 聊天框会显示 "已生成文件变更请求"。
- 在右侧 **上下文面板** -> **📋 待审批变更** 中查看 Diff。
- 点击 ✅ 批准 或 ❌ 拒绝。

### 3. 上下文切片 (@Mention)
在对话中，你可以通过 `@AgentName` 引用意图（系统会解析 @ 提及并优化路由上下文）。
