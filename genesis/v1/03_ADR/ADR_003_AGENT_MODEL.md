# ADR 003: Agent Model & Tool Layering

**Status**: Accepted
**Date**: 2026-02-10

## Context
需要防止工具库变得杂乱无章，同时支持灵活的智能体定义。

## Decision

### 1. 三层能力架构
- **Layer 1 (Tools)**: 无状态原子函数 (Function)。
- **Layer 2 (Skills)**: 有状态、包含业务逻辑的类 (Class)。
- **Layer 3 (Custom)**: 用户动态加载的脚本。

### 2. Meta-Agent 模式
- 引入一个特殊的系统级智能体。
- **职责**: 能够调用 `AgentRegistry` 和 `FileSystem` 来创建新的智能体配置。
- **实现**: 作为一个预装的 "Admin Agent" 存在。

### 3. Context Slicing (@Mention)
- **问题**: 长对话历史导致 Token 浪费和注意力分散。
- **策略**: 
  - 路由层拦截 `@Mention`。
  - 使用轻量模型 (GPT-4o-mini) 提取相关上下文摘要。
  - 仅将摘要 + 指令发送给目标 Agent。

## Consequences
- 需要维护两套 LLM 调用逻辑（主对话 和 摘要提取）。
- 技能类的设计需要遵循统一接口，以便被 Agent 加载器识别。
