# Product Requirements Document (PRD) - AgentOS v1

**Status**: Draft (Refined)
**Version**: v1.1
**Date**: 2026-02-10

## 1. 产品概述
AgentOS 是一个运行于 `localhost:8501` 的本地化 Web 应用。
**核心理念**: 以文件为中心的记忆 (File-Centric Memory)。文件系统即数据库，严格区分数据的静态、动态和归档状态。

### 1.1 核心价值
- **Privacy First**: 数据完全本地化，不依赖云端数据库。
- **Transparency**: 所有的记忆都是可见的文件 (Markdown/JSON)。
- **Control**: 敏感操作（如修改 PRD）必须经过可见的 Diff 审批。

## 2. 数据架构与权限 (Data Architecture)

### 2.1 三级数据权限
系统严格执行以下权限模型：
- **🔒 Static Assets (`/static_assets`)**:
  - **权限**: READ-ONLY
  - **用途**: 存放不可变的事实、模板、品牌素材（如 Logo, 银行流水 PDF）。
- **📝 Living Docs (`/living_docs`)**:
  - **权限**: READ-WRITE (Diff 审批)
  - **用途**: 项目的 **Single Source of Truth**。代表当前状态（如 PRD_Master.md, Todo.txt）。
- **🗂 Archives (`/archives`)**:
  - **权限**: WRITE-ONLY / APPEND
  - **用途**: 存放临时草稿、历史版本、备份。

## 3. 用户故事 (User Stories)

### 3.1 核心交互
- **[REQ-001] 元智能体 (Meta-Agent)**: 作为用户，我希望告诉系统“帮我创建一个懂理财的 Agent”，系统能自动配置 System Prompt、选择可视化技能，并创建对应的目录结构。
- **[REQ-002] 智能上下文 (@Mention)**: 作为用户，我希望在聊天中使用 `@设计师`，系统能自动截取相关上下文传给该 Agent，而不是把整个聊天历史都发过去。
- **[REQ-003] 分屏协作**: 作为用户，我希望界面是左中右三栏结构，右侧面板能实时显示 Agent 正在修改的文件内容。

### 3.2 安全与控制
- **[REQ-010] 变更请求卡片 (Diff View)**: 当 Agent 想要修改 Living Docs 时，我希望看到一个红绿对比的 Diff 卡片，由我决定是 [批准] 还是 [拒绝]。
- **[REQ-011] 根目录锁 (Root Lock)**: 系统必须阻止 Agent 访问 `permission_scope` 以外的任何文件。

## 4. 功能规格 (Functional Specs)

### 4.1 能力分层系统
系统实现三层能力架构：
1.  **Core Tools (L1)**: 原子能力，如 `FileSystemTools` (read/write/diff), `WebTools` (Search/Fetch), `CodeTools` (REPL), `BrowserPrimitives` (Screenshot)。
2.  **Standard Skills (L2)**: 组合工作流 Class。
    - *Deep Research*: 搜索 -> 抓取 -> 总结 -> 报告。
    - *Browser Takeover*: 连接本地 Chrome (CDP) -> 模拟操作 -> 验证。
    - *Data Viz*: 读取数据 -> 编写绘图代码 -> 生成图片。
3.  **Custom Skills (L3)**: 动态加载 `custom_skills/*.py`。

### 4.2 模型分级策略
支持为不同 Agent 分配不同等级的模型：
- **T1 (The Brain)**: GPT-4o / Gemini 1.5 Pro (架构、编程、复杂推理)。
- **T2 (The Fast)**: GPT-4o-mini / Gemini Flash (搜索、总结、简单任务)。

## 5. 界面规范
- **左侧栏**: Workspace 选择、Agent 列表 (标签分组)、API Key 全局设置。
- **主区域**: 聊天流，支持 Markdown 渲染和 Diff 卡片组件。
- **右侧栏**: 实时上下文面板，自动刷新显示 `active/` 下的文件变更。
