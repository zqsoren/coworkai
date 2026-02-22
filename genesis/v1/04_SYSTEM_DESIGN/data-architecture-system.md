# System Design: 三级数据架构系统 (Data Architecture System)

| Meta | Details |
| :--- | :--- |
| **System ID** | `data-architecture-system` |
| **Status** | **Implemented** |
| **Date** | 2026-02-10 |
| **Version** | v1.1 |
| **关联需求** | [REQ-010] Diff 审批, [REQ-011] Root Lock, PRD §2 数据架构与权限 |

---

## 1. Overview

三级数据架构系统管理每个 Agent 的文件生命周期，从静态资源到动态文档再到归档交付，并提供 RAG 知识库能力。它由四个子系统组成：

1. **三级文件管理** — context/static / context/active / context/archives
2. **文件上传** — 支持本地文档上传到 context/static 和 context/active
3. **Project Flight Recorder** — 自动日志记录，存储在 context/archives
4. **知识库 (RAG Pipeline)** — 文件上传 → 清洗 → 分割 → 向量化 → 检索

---

## 2. Goals & Non-Goals

### 2.1 Goals
- **右侧栏三按钮**: 选中 Agent 后，右侧栏显示 "静态资源库"、"动态项目文档"、"归档与交付" 三个可展开按钮
- **文件浏览**: 点击按钮展开文件列表，点击文件弹出大弹窗显示内容
- **本地上传**: `context/static` 和 `context/active` 目录支持本地文件上传 (拖拽/按钮)
- **自动日志**: Project Flight Recorder 自动记录对话、工具调用、文件修改
- **知识库**: 每个 Agent 独立知识库，支持上传 (doc/txt)，自动清洗+分割+向量化

### 2.2 Non-Goals
- 云端同步/备份 (v2)
- 多 Agent 共享知识库 (v2)
- PDF 解析 (v1 仅 txt/doc/md)
- 实时文件监听 (v1 用手动触发或启动时扫描)

---

## 3. System Architecture

### 3.1 目录结构 (每个 Agent)

```text
data/{workspace}/{agent}/
├── context/
│   ├── static/              # 🔒 READ-ONLY 静态资源库
│   │   ├── brand_guide.pdf
│   │   └── template.md
│   ├── active/              # 📝 READ-WRITE 动态项目文档 (Living Docs)
│   │   ├── PRD_Master.md
│   │   └── Todo.txt
│   └── archives/            # 🗂 APPEND-ONLY 归档与交付
│       ├── Project_Activity_Log.md
│       └── Project_Activity_Log_ARCHIVE_20260210.md
├── knowledge_base/          # 🧠 RAG 知识库 (原始文件)
│   ├── uploaded_doc.txt
│   └── reference.md
├── vector_store/            # 📊 向量数据库 (ChromaDB)
│   └── chroma.sqlite3
└── config.json
```

### 3.2 组件依赖图

```mermaid
graph TD
    subgraph UI Layer
        RP[Right Panel<br>三级文件按钮]
        FV[File Viewer<br>大弹窗]
        UPL[Upload Widget<br>文件上传]
        KB[Knowledge Base<br>知识库按钮]
    end

    subgraph Core Layer
        FM[FileManager<br>Root Lock + 权限]
        PL[ProjectLogger<br>Flight Recorder]
        RAG[RAGIngestion<br>清洗+分割+嵌入]
    end

    subgraph Storage Layer
        FS[File System<br>context/{static/active/archives}]
        VS[Vector Store<br>ChromaDB]
    end

    RP -->|"展开文件列表"| FM
    RP -->|"点击文件"| FV
    UPL -->|"上传到 static/active"| FM
    KB -->|"上传到 knowledge_base"| RAG

    RAG -->|"Load → Clean → Split → Embed"| VS
    PL -->|"自动追加日志"| FS
    FM -->|"读/写/列"| FS
```

---

## 4. Interface Design

### 4.1 右侧栏 — 三级文件按钮

**位置**: 右侧栏 (Context Panel)，在 "Agent 设定" 下方

**结构**:
```
┌─────────────────────────┐
│ 🧠 知识库 [鲜艳按钮]      │  ← 最上方
├─────────────────────────┤
│ ⚙️ Agent 设定             │  ← 可展开
├─────────────────────────┤
│ 📦 静态资源库  [上传▲]     │  ← 可展开，含文件列表
│   📄 brand_guide.pdf      │
│   📄 template.md          │
├─────────────────────────┤
│ 📝 动态项目文档 [上传▲]    │  ← 可展开，含文件列表
│   📄 PRD_Master.md        │
│   📄 Todo.txt             │
├─────────────────────────┤
│ 🗂 归档与交付              │  ← 可展开，只读浏览
│   📄 Activity_Log.md      │
│   📄 Draft_v1.md          │
└─────────────────────────┘
```

**交互**:
- 点击 `📄 文件名` → 弹出大弹窗 (`st.dialog`) 显示文件内容
- 点击 `上传▲` → 弹出 `st.file_uploader`，文件保存到对应目录
- "归档与交付" 不提供上传 (系统自动写入)

### 4.2 知识库弹窗

**触发**: 点击右侧栏顶部 "🧠 知识库" 鲜艳按钮

**弹窗内容**:
```
┌──────────────────────────────┐
│ 🧠 知识库 — {Agent Name}      │
│                              │
│ 已上传文件:                    │
│   📄 company_report.txt [❌]  │
│   📄 product_manual.md  [❌]  │
│                              │
│ ┌──────────────────────┐     │
│ │    ➕ 上传新文件        │     │  ← st.file_uploader
│ │  支持: .txt, .md, .doc │     │
│ └──────────────────────┘     │
│                              │
│ ⚙️ 数据处理:                  │
│ [🧹 清洗数据] [✂️ 重新分割]    │  ← 手动触发
│                              │
│ 状态: ✅ 已索引 3 个文件       │
│ 最后更新: 2026-02-10 22:00   │
└──────────────────────────────┘
```

### 4.3 ProjectLogger API

```python
class ProjectLogger:
    """Project Flight Recorder — 自动追加日志到 archives/"""

    LOG_FILE = "Project_Activity_Log.md"
    MAX_SIZE = 2 * 1024 * 1024  # 2MB

    def __init__(self, file_manager: FileManager, workspace: str, agent_id: str):
        self.fm = file_manager
        self.log_path = f"{workspace}/{agent_id}/context/archives/{self.LOG_FILE}"

    def log_interaction(self, user_msg: str, ai_msg: str) -> None:
        """记录用户-AI对话"""
        # 格式: ### 🗣️ [timestamp] Interaction

    def log_tool_call(self, tool_name: str, args: dict, status: str) -> None:
        """记录工具调用"""
        # 格式: ### 🛠️ [timestamp] Tool Call

    def log_file_change(self, file_path: str, diff: str) -> None:
        """记录文件变更 (Diff)"""
        # 格式: ### 📝 [timestamp] File Change

    def _check_rotation(self) -> None:
        """检查文件大小，超过2MB自动轮转"""
        # Rename → Archive, Create new
```

### 4.4 RAG Ingestion Pipeline API

```python
class RAGIngestion:
    """知识库摄入管道: Load → Clean → Split → Embed → Store"""

    def __init__(self, workspace: str, agent_id: str):
        self.kb_path = f"data/{workspace}/{agent_id}/knowledge_base"
        self.vs_path = f"data/{workspace}/{agent_id}/vector_store"

    def ingest_file(self, file_path: str) -> int:
        """处理单个文件，返回生成的 chunk 数"""
        text = self._load(file_path)
        cleaned = self._clean(text)
        chunks = self._split(cleaned)
        self._embed_and_store(chunks, source=file_path)
        return len(chunks)

    def _load(self, path: str) -> str:
        """Loader Factory: 根据文件扩展名选择加载器"""
        # .txt, .md → TextLoader
        # .doc → python-docx
        # .csv → CSVLoader

    def _clean(self, text: str) -> str:
        """Auto-Cleaner: 清洗文本"""
        # 1. 多余换行 → 单换行
        # 2. 去除页码/页眉 (正则)
        # 3. 去除非打印字符

    def _split(self, text: str) -> list[str]:
        """Smart Splitter: RecursiveCharacterTextSplitter"""
        # chunk_size=1000, chunk_overlap=200

    def _embed_and_store(self, chunks: list[str], source: str) -> None:
        """嵌入并存储到 ChromaDB"""
        # 使用 sentence-transformers 或 Google Embedding

    def query(self, question: str, top_k: int = 5) -> list[dict]:
        """检索相关文档片段"""
        # 返回 [{content, source, score}]

    def rebuild_all(self) -> int:
        """重建整个知识库索引"""
        # 清空 vector_store → 重新 ingest 所有文件
```

---

## 5. Data Model

### 5.1 文件权限矩阵

| 目录 | Agent 读 | Agent 写 | 用户上传 | 用户下载 |
|------|---------|---------|---------|---------|
| `context/static/` | ✅ | ❌ | ✅ | ✅ |
| `context/active/` | ✅ | ✅ (Diff审批) | ✅ | ✅ |
| `context/archives/` | ✅ | ✅ (Append) | ❌ | ✅ |
| `knowledge_base/` | ✅ | ❌ (系统写) | ✅ | ✅ |
| `vector_store/` | ✅ (查询) | ❌ | ❌ | ❌ |

### 5.2 Activity Log 格式

```markdown
# Project Activity Log

### 🗣️ [2026-02-10 22:30:15] Interaction
**User**: "修改背景颜色为蓝色"
**AI**: "好的，我将更新 CSS 文件。"

### 🛠️ [2026-02-10 22:30:16] Tool Call
**Tool**: `read_file`
**Args**: `{"path": "context/active/style.css"}`
**Status**: Success

### 📝 [2026-02-10 22:30:20] File Change
**File**: `context/active/style.css`
**Change**:
```diff
- background-color: white;
+ background-color: blue;
```
```

### 5.3 Vector Store Schema (ChromaDB)

```python
{
    "collection_name": f"{agent_id}_knowledge",
    "documents": ["chunk text..."],
    "metadatas": [{"source": "report.txt", "chunk_index": 0}],
    "ids": ["report_txt_chunk_0"]
}
```

---

## 6. Technology Stack

| 组件 | 技术选型 | 理由 |
|------|---------|------|
| 文件管理 | `FileManager` (已有) | Root Lock + 三层权限 |
| 文件上传 | `st.file_uploader` | Streamlit 原生组件 |
| 弹窗 | `st.dialog` / `st.modal` | Streamlit 原生弹窗 |
| 文本分割 | `RecursiveCharacterTextSplitter` | LangChain 标准组件 |
| 向量数据库 | **ChromaDB** | 本地持久化, 零配置, Python原生 |
| 嵌入模型 | `sentence-transformers` (`all-MiniLM-L6-v2`) | 本地隐私优先, ~80MB, 零API成本 ✅ Confirmed |
| 文档加载 | `langchain.document_loaders` | 支持多格式 |
| 日志轮转 | 自定义 (os.path.getsize + rename) | 简单可靠 |

---

## 7. Trade-offs & Alternatives

### 7.1 向量数据库: ChromaDB vs FAISS vs SQLite-VSS
- **ChromaDB**: 零配置, Python原生, 支持持久化 ✅ 选择
- **FAISS**: 性能更好, 但需手动管理序列化
- **SQLite-VSS**: 最小依赖, 但社区支持少
- **理由**: 本地项目优先考虑易用性, ChromaDB 完美匹配

### 7.2 嵌入模型: 本地 vs 云端
- **本地 (sentence-transformers)**: 隐私最佳, 无API成本, 需要下载模型 (~80MB) ✅ **v1 最终选择**
- **云端 (Google Embedding API)**: 性能更好, 需API Key
- **决策**: **默认本地 `all-MiniLM-L6-v2`**, 可选云端。Config 中可增加 `embedding_provider` 字段切换

### 7.3 Project Logger: 后台自动 vs 用户手动
- **后台自动** (通过 Graph Node hooks): 用户无感知 ✅ 选择
- **用户手动**: 需要用户点击 "开始记录"
- **理由**: 日志是审计需求, 不应依赖用户主动操作

### 7.4 日志位置: archives/ vs living_docs/
- **archives/** ✅ 选择: 保持 living_docs 干净, 日志是历史记录
- **living_docs/**: 会污染 Agent 的工作上下文
- **理由**: 用户明确要求存放在 archives

### 7.5 知识库粒度: Per-Agent vs Per-Workspace
- **Per-Agent** ✅ 选择: 每个 Agent 有独立知识库, 上下文更精准
- **Per-Workspace**: 所有 Agent 共享, 实现更简单
- **理由**: 用户明确要求 "每个 agent 都匹配了不同的知识库"

---

## 8. Security Considerations

- **上传限制**: 限制文件大小 (默认 10MB), 限制文件类型 (txt/md/doc)
- **路径穿越**: `FileManager._resolve_and_validate()` 确保上传后的写入路径不逃逸
- **日志轮转**: 防止日志文件无限增长 (2MB 上限 + 自动归档)
- **向量注入**: ChromaDB 查询结果需过滤, 避免注入恶意 prompt

---

## 9. Performance Considerations

- **Embedding 延迟**: 本地模型编码 1000 个 chunk 约 30s, 建议异步处理 + 进度条
- **ChromaDB 查询**: 本地查询 < 100ms, 对于知识库场景完全足够
- **Activity Log**: Append-only + 2MB 轮转, 写入开销可忽略

---

## 10. Testing Strategy

### Unit Tests
- `ProjectLogger`: 测试日志格式、轮转逻辑 (Mock os.path.getsize)
- `RAGIngestion._clean()`: 测试文本清洗规则
- `RAGIngestion._split()`: 测试分割结果的 chunk 数量和 overlap

### Integration Tests
- 上传文件 → 验证存储到正确目录
- 上传到知识库 → 验证 ChromaDB 可检索
- Activity Log 写满 2MB → 验证自动轮转

### Manual Verification
- 右侧栏三按钮展开/收起
- 文件弹窗显示内容
- 知识库弹窗上传+清洗+分割流程

---

## 11. Implementation Notes (v1.1)

> [!NOTE]
> 以下是实际实现中确认的决策。

### 11.1 RAGIngestion 实际签名
```python
RAGIngestion(data_root: str, workspace: str, agent_id: str)
# data_root = abs path to data/
# 自动创建 knowledge_base/ 和 vector_store/ 子目录
```

### 11.2 LangGraph 集成
- `agent_node` 在构建 system prompt 时自动查询 ChromaDB (top-3 results)
- `tool_node` 每次工具调用后写入 Flight Recorder 日志
- `chat.py` 每次对话后写入 Flight Recorder 日志
- 所有集成均 fail-safe (try/except，失败不中断)

### 11.3 ProjectLogger 实际签名
```python
ProjectLogger(data_root: str, workspace: str, agent_id: str)
# 不使用 FileManager，直接操作文件系统
# 日志路径: data/{workspace}/{agent_id}/context/archives/Project_Activity_Log.md
```

### 11.4 确认的目录映射
| PRD 术语 | 实际路径 |
|---------|----------|
| `static/` | `context/static/` |
| `active/` (living_docs) | `context/active/` |
| `output/` (archives) | `context/archives/` |
