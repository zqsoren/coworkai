"""
MCP Builder Skill - MCP 服务器开发指南
指导 LLM 如何通过标准流程构建高质量 MCP (Model Context Protocol) 服务器。
"""

SKILL_NAME = "mcp_builder"
SKILL_DESCRIPTION = "MCP 服务器开发指南：指导构建高质量 MCP 服务器，包括调研、实现、测试和评估四大阶段"


# 将 SKILL.md 内容作为指导手册嵌入
_MCP_GUIDE = """
# MCP Server Development Guide

## Overview
Create MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools.

## 🚀 Four Phases

### Phase 1: Deep Research and Planning

**API Coverage vs. Workflow Tools:**
Balance comprehensive API endpoint coverage with specialized workflow tools. Prioritize comprehensive API coverage when uncertain.

**Tool Naming:** Use consistent prefixes (e.g., `github_create_issue`), action-oriented naming.

**Context Management:** Design tools that return focused, relevant data with pagination support.

**Actionable Error Messages:** Error messages should guide agents toward solutions.

**Study MCP Protocol Documentation:**
- Start with sitemap: `https://modelcontextprotocol.io/sitemap.xml`
- Fetch pages with `.md` suffix for markdown format

**Recommended Stack:**
- Language: TypeScript (recommended) or Python
- Transport: Streamable HTTP for remote, stdio for local

### Phase 2: Implementation

**Project Structure:**
- TypeScript: package.json, tsconfig.json, src/
- Python: module organization, dependencies

**Core Infrastructure:**
- API client with authentication
- Error handling helpers
- Response formatting (JSON/Markdown)
- Pagination support

**For Each Tool:**
- Input Schema: Zod (TS) or Pydantic (Python) with constraints
- Output Schema: Define `outputSchema` for structured data
- Tool Description: Concise summary + parameter descriptions
- Implementation: Async/await, error handling, pagination
- Annotations: readOnlyHint, destructiveHint, idempotentHint, openWorldHint

### Phase 3: Review and Test
- No duplicated code (DRY)
- Consistent error handling
- Full type coverage
- TypeScript: `npm run build` + MCP Inspector
- Python: `python -m py_compile` + MCP Inspector

### Phase 4: Create Evaluations
Create 10 evaluation questions that are:
- Independent, Read-only, Complex, Realistic, Verifiable, Stable

Output format: XML with `<evaluation>` > `<qa_pair>` > `<question>` + `<answer>`

## SDK References
- TypeScript SDK: `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`
- Python SDK: `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- MCP Spec: `https://modelcontextprotocol.io/specification/draft.md`
"""


async def run(task: str = "", language: str = "typescript", **kwargs) -> str:
    """
    启动 MCP 服务器开发指导流程

    Args:
        task: 要构建的 MCP 服务器描述（如 "为 GitHub API 构建 MCP 服务器"）
        language: 开发语言，typescript 或 python，默认 typescript
    """
    guide = _MCP_GUIDE.strip()

    if not task:
        return f"""# MCP Server 开发指南

{guide}

---

💡 **使用方式**: 请提供要构建的 MCP 服务器描述，例如：
- "为 GitHub API 构建 MCP 服务器"
- "创建一个天气查询 MCP 服务器"
- "构建数据库管理 MCP 服务器"
"""

    lang_tip = ""
    if language.lower() == "python":
        lang_tip = """
**Python 实现要点:**
- 使用 FastMCP 框架
- 通过 `@mcp.tool` 装饰器注册工具
- 使用 Pydantic 定义输入模型
- SDK: `pip install mcp`
"""
    else:
        lang_tip = """
**TypeScript 实现要点:**
- 使用 `@modelcontextprotocol/sdk`
- 通过 `server.registerTool()` 注册工具
- 使用 Zod 定义输入 Schema
- SDK: `npm install @modelcontextprotocol/sdk`
"""

    return f"""# MCP Server 开发计划: {task}

## 开发语言: {language.upper()}
{lang_tip}

{guide}

---

## 下一步行动

请按照以上四个阶段开始构建 MCP 服务器：

1. **Phase 1**: 研究 {task} 相关的 API 文档，确定需要实现的工具列表
2. **Phase 2**: 搭建项目结构，实现核心工具
3. **Phase 3**: 构建测试，确保代码质量
4. **Phase 4**: 创建评估问题验证效果
"""
