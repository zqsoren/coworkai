# ADR 002: Data Architecture & Permissions

**Status**: Accepted
**Date**: 2026-02-10
**Context**: AgentOS v1

## Context
智能体需要操作文件，但必须防止其破坏重要数据或产生混乱。需要一种严格的机制来管理文件权限和生命周期。

## Decision

### 1. File-Centric Memory
- **决策**: 放弃 SQL 数据库，所有业务数据（Memory, Todo, Logs）均以人类可读的文件格式 (MD, JSON, YAML) 存储。
- **好处**: 用户拥有数据主权，易于迁移和备份。

### 2. 三级目录权限模型
强制 `FileManager` 类实现以下逻辑检查：
- **/static_assets (READ-ONLY)**: 
  - 禁止任何写操作。
  - 仅供 Agent 读取作为参考。
- **/living_docs (READ-WRITE with Approval)**:
  - 写操作必须触发 `ChangeRequest` 流程。
  - 必须生成 Git-style Diff 供用户人工审批。
- **/archives (WRITE-ONLY / APPEND)**:
  - 允许直接写入（通常是新文件）。
  - 用于日志、草稿、中间产物。

### 3. Root Directory Lock
- **决策**: Agent 的文件操作被严格限制在 `./data` 及其子目录下。
- **实现**: 在 `FileSystemTools` 中校验绝对路径是否以 `PROJECT_ROOT/data` 开头。

## Consequences
- 开发复杂度增加：需实现一个健壮的 `FileManager` 包装器。
- 交互流程变长：修改核心文档需要用户介入，但这提升了安全性。
