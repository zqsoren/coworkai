"""
Skill Creator - 技能创建者
指导如何创建高质量的 Skill 技能包，扩展 Agent 的专业能力。
"""

SKILL_NAME = "skill_creator"
SKILL_DESCRIPTION = "技能创建者：指导设计和构建高质量 Skill 技能包，包括工作流、工具集成和领域知识封装"


_SKILL_GUIDE = """
# Skill Creator Guide

## About Skills
Skills are modular packages that extend Agent capabilities with:
1. Specialized workflows - Multi-step procedures
2. Tool integrations - File formats or APIs
3. Domain expertise - Company-specific knowledge
4. Bundled resources - Scripts, references, assets

## Core Principles

### Concise is Key
Context window is shared. Only add what the model doesn't already know.
Prefer concise examples over verbose explanations.

### Degrees of Freedom
- **High freedom**: Multiple approaches valid, text instructions
- **Medium freedom**: Preferred pattern exists, pseudocode/scripts
- **Low freedom**: Fragile operations, specific scripts

### Skill Anatomy
```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name + description)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/     - Executable code
    ├── references/  - Documentation for context
    └── assets/      - Output files (templates, icons)
```

### Progressive Disclosure
1. **Metadata** (name + description) - Always in context (~100 words)
2. **SKILL.md body** - When skill triggers (<5k words)
3. **Bundled resources** - As needed

## Creation Process
1. Understand the skill with concrete examples
2. Plan reusable contents (scripts, references, assets)
3. Initialize the skill structure
4. Implement resources and write SKILL.md
5. Package and test the skill
6. Iterate based on real usage
"""


async def run(task: str = "", skill_name: str = "", **kwargs) -> str:
    """
    启动技能创建指导流程

    Args:
        task: 要创建的技能描述（如 "创建一个 PDF 处理技能"）
        skill_name: 技能名称（英文，如 "pdf_processor"）
    """
    guide = _SKILL_GUIDE.strip()

    if not task:
        return f"""# 技能创建指南

{guide}

---

💡 **使用方式**: 请描述你想创建的技能，例如：
- "创建一个 PDF 文档处理技能"
- "创建一个邮件自动化技能"
- "创建一个数据清洗技能"
"""

    name = skill_name or task.replace(" ", "_").lower()[:30]

    return f"""# 技能创建计划: {task}

## 技能名称: {name}

{guide}

---

## 具体实施步骤

### 1. 创建技能文件
```python
# src/skills/{name}.py

SKILL_NAME = "{name}"
SKILL_DESCRIPTION = "{task}"

async def run(**kwargs) -> str:
    # 实现技能逻辑
    pass
```

### 2. 注册到前端
在 `AgentSkillsModal.tsx` 中添加:
- `SKILL_LABELS` 中添加中文名
- `MCP_MARKET_ITEMS` 中添加市场条目

### 3. 测试
重启后端，从工具市场添加技能到 Agent，验证功能正常。
"""
