# AGENTS.md - AI 协作协议

> **"如果你正在阅读此文档，你就是那个智能体 (The Intelligence)。"**
> 
> 这个文件是你的**锚点 (Anchor)**。它定义了项目的法则、领地的地图，以及记忆协议。
> 当你唤醒（开始新会话）时，**请首先阅读此文件**。

---

## 🧠 30秒恢复协议 (Quick Recovery)

**当你开始新会话或感到"迷失"时，立即执行**:

1. **读取 .agent/rules/agents.md** → 获取项目地图
2. **查看下方"当前状态"** → 找到最新架构版本
3. **读取 `genesis/v{N}/05_TASKS.md`** → 了解当前待办
4. **开始工作**

---

## 🗺️ 地图 (领地感知)

以下是这个项目的组织方式：

| 路径 | 描述 | 访问协议 |
|------|------|----------|
| `src/` | **实现层**。实际的代码库。 | 通过 Task 读/写。 |
| `genesis/` | **设计演进史**。版本化架构状态 (v1, v2...)。 | **只读**(旧版) / **写一次**(新版)。 |
| `genesis/v{N}/` | **当前真理**。最新的架构定义。 | 永远寻找最大的 `v{N}`。 |
| `.agent/workflows/` | **工作流**。`/genesis`, `/blueprint` 等。 | 通过 `view_file` 阅读。 |
| `.agent/skills/` | **技能库**。原子能力。 | 通过 `view_file` 调用。 |

---

## 📍 当前状态 (由 Workflow 自动更新)

> **注意**: 此部分由 `/genesis` 和 `/blueprint` 自动维护。

- **最新架构版本**: `genesis/v1`
- **活动任务清单**: `genesis/v1/05_TASKS.md`
- **待办任务数**: `12`
- **最近一次更新**: `2026-02-10`

---

## 🌳 项目结构 (Project Tree)

> **注意**: 此部分由 `/genesis` 维护。

```text
agentOS/
├── genesis/v1/          # 架构文档 (PRD, Arch, ADR)
├── src/
│   ├── app.py           # Streamlit 入口
│   ├── core/            # 核心逻辑 (Workspace, AgentRegistry, FileManager)
│   ├── graph/           # 执行引擎 (LangGraph)
│   ├── skills/          # 技能加载器
│   ├── tools/           # 工具集
│   └── ui/              # 界面组件
├── data/                # 运行时数据 (Workspaces)
├── config/              # 静态配置
└── custom_skills/       # 用户扩展技能
```

---

## 🧭 导航指南 (Navigation Guide)

> **注意**: 此部分由 `/genesis` 维护。

- **架构总览**: `genesis/v1/02_ARCHITECTURE_OVERVIEW.md`
- **PRD**: `genesis/v1/01_PRD.md`
- **ADR**: 架构决策见 `genesis/v1/03_ADR/`
- **详细设计**: 待 `/design-system` 执行后更新
- **任务清单**: 待 `/blueprint` 执行后更新

---

## 🛠️ 工作流注册表

| 工作流 | 触发时机 | 产出 |
|--------|---------|------|
| `/genesis` | 新项目 / 重大重构 | PRD, Architecture, ADRs |
| `/scout` | 变更前 / 接手项目 | `scout/reports/{Date}_SCOUT_RISK_REPORT.md` |
| `/design-system` | genesis 后 | 04_SYSTEM_DESIGN/*.md |
| `/blueprint` | genesis 后 | 05_TASKS.md |
| `/change` | 轻量变更 | 更新 TASKS + CHANGELOG |
| `/explore` | 调研时 | 探索报告 |
| `/challenge` | 决策前质疑 | 07_CHALLENGE_REPORT.md |

---

## 📜 宪法 (The Constitution)

1. **版本即法律**: 不"修补"架构文档，只"演进"。变更必须创建新版本。
2. **显式上下文**: 决策写入 ADR，不留在"聊天记忆"里。
3. **交叉验证**: 编码前对照 `05_TASKS.md`。我在做计划好的事吗？
4. **美学**: 文档应该是美的。善用 Markdown 和 Emoji。

---

> **状态自检**: 准备好了？读取上方"当前状态"指引的架构文档并开始吧。
