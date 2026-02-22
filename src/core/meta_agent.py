"""
Meta-Agent - The Overseer (Layer 3 Logic)
双模式：Builder (创建 Agent) + Observer (全局观察与委派)
"""

import os
import json
from .file_manager import FileManager
from .agent_registry import AgentRegistry


class MetaAgent:
    """
    Meta-Agent (The Overseer) — 双模式

    Builder Mode:  创建新 Agent（目录+配置+注册）
    Observer Mode: 全局文件搜索、跨 Agent 读取、任务委派建议
    """

    def __init__(self, file_manager: FileManager, registry: AgentRegistry):
        self.fm = file_manager
        self.registry = registry

    # ================================================================
    # Builder Mode — 创建 Agent
    # ================================================================

    def create_agent(self, workspace_id: str, agent_id: str, 
                    name: str, role_desc: str, 
                    tools: list[str] = None, skills: list[str] = None,
                    provider_id: str = "gemini_default", model_name: str = "gemini-2.0-flash",
                    system_prompt: str = None) -> str:
        """
        创建一个新的 Agent：
        1. 创建目录结构 (data/workspace/agent)
        2. 生成 config.json
        3. 注册到 Registry
        """
        tools = tools or ["read_file", "write_file", "google_search"]
        skills = skills or []
        
        # 1. 确保目录结构
        agent_path = self.fm.ensure_agent_dirs(workspace_id, agent_id)
        
        # 2. 生成 System Prompt (Override if provided)
        if not system_prompt:
             system_prompt = f"""你是一个 {name}。
角色描述: {role_desc}
请利用你的工具和技能协助用户。
"""
        
        # 3. 准备配置
        config = {
            "name": name,
            "workspace": workspace_id,
            "system_prompt": system_prompt,
            "provider_id": provider_id,
            "model_name": model_name,
            "tools": tools,
            "skills": skills,
            "tags": ["custom"],
            "created_at": None  # registry handles this
        }
        
        # 4. 写入本地 config.json
        config_path = os.path.join(agent_path, "config.json")
        self.fm.write_file(config_path, json.dumps(config, ensure_ascii=False, indent=2))
        
        # 5. 注册
        try:
            self.registry.register_agent(agent_id, config)
        except ValueError:
            self.registry.update_agent(agent_id, config)
            
        return f"Agent '{name}' ({agent_id}) 创建成功！"

    def delete_agent(self, workspace_id: str, agent_id: str) -> str:
        """删除 Agent (目录 + 注册表)"""
        agent_path = self.fm._resolve_and_validate(os.path.join(workspace_id, agent_id))
        
        # 1. 删除文件
        if os.path.exists(agent_path):
            import shutil
            shutil.rmtree(agent_path)
            
        # 2. 删除注册表
        try:
            self.registry.remove_agent(agent_id)
        except KeyError:
            pass # 可能只是文件残留
            
        return f"Agent {agent_id} 已删除。"

    def rename_agent(self, workspace_id: str, agent_id: str, new_name: str) -> str:
        """重命名 Agent (仅修改显示名称，不改 ID)"""
        # 1. 更新注册表
        self.registry.update_agent(agent_id, {"name": new_name})
        
        # 2. 更新本地 config.json
        agent_path = self.fm._resolve_and_validate(os.path.join(workspace_id, agent_id))
        config_path = os.path.join(agent_path, "config.json")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                config["name"] = new_name
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Warning: Failed to update local config for {agent_id}: {e}")
                
        return f"Agent {agent_id} 重命名为 '{new_name}'。"

    # ================================================================
    # Observer Mode — 全局观察
    # ================================================================

    def list_all_files(self, workspace_id: str, max_depth: int = 5) -> list[dict]:
        """递归列出工作区内所有文件"""
        ws_path = self.fm._resolve_and_validate(workspace_id)
        if not os.path.isdir(ws_path):
            return []

        results = []
        for root, dirs, files in os.walk(ws_path):
            # 计算深度
            depth = root.replace(ws_path, "").count(os.sep)
            if depth > max_depth:
                dirs.clear()
                continue

            rel_root = os.path.relpath(root, self.fm.data_root).replace("\\", "/")
            for f in files:
                full = os.path.join(root, f)
                results.append({
                    "name": f,
                    "path": f"{rel_root}/{f}",
                    "size": os.path.getsize(full),
                    "agent": self._extract_agent_from_path(rel_root),
                })
        return results

    def read_any_file(self, file_path: str) -> str:
        """
        读取 data/ 下任意文件（Observer 特权）
        仍遵守 Root Lock，但不受 tier 读权限限制
        """
        resolved = self.fm._resolve_and_validate(file_path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if os.path.isdir(resolved):
            raise IsADirectoryError(f"路径是目录: {file_path}")

        try:
            with open(resolved, "r", encoding="utf-8") as f:
                content = f.read()
            # 超长文件截断
            if len(content) > 10000:
                content = content[:10000] + "\n\n...[内容过长，已截断]"
            return content
        except UnicodeDecodeError:
            return f"[二进制文件，无法读取: {file_path}]"

    def search_files(self, workspace_id: str, keyword: str) -> list[dict]:
        """在工作区所有文本文件中搜索关键词"""
        ws_path = self.fm._resolve_and_validate(workspace_id)
        if not os.path.isdir(ws_path):
            return []

        TEXT_EXTS = {".txt", ".md", ".json", ".csv", ".py", ".yaml", ".yml", ".toml"}
        results = []

        for root, _, files in os.walk(ws_path):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext not in TEXT_EXTS:
                    continue

                full = os.path.join(root, f)
                try:
                    with open(full, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                    if keyword.lower() in content.lower():
                        # 找到匹配行
                        lines = content.split("\n")
                        matches = [
                            (i + 1, line.strip())
                            for i, line in enumerate(lines)
                            if keyword.lower() in line.lower()
                        ]
                        rel = os.path.relpath(full, self.fm.data_root).replace("\\", "/")
                        results.append({
                            "file": rel,
                            "agent": self._extract_agent_from_path(rel),
                            "matches": matches[:5],  # 最多5行
                            "total_matches": len(matches),
                        })
                except Exception:
                    continue

        return results

    # ================================================================
    # Delegation — 委派建议
    # ================================================================

    def suggest_delegation(self, target_agent_id: str, task_description: str) -> dict:
        """
        生成委派建议（v1 手动模式）
        返回结构化数据供 UI 渲染为可点击按钮
        """
        agent_config = self.registry.get_agent(target_agent_id)
        agent_name = agent_config.get("name", target_agent_id) if agent_config else target_agent_id

        return {
            "type": "delegation_suggestion",
            "target_agent_id": target_agent_id,
            "target_agent_name": agent_name,
            "task_description": task_description,
            "message": f"💡 建议委派给 **@{agent_name}**：{task_description}",
            "action_label": f"🔄 切换到 {agent_name}",
        }

    # ================================================================
    # Helpers
    # ================================================================

    def _extract_agent_from_path(self, rel_path: str) -> str:
        """从相对路径提取 agent_id"""
        parts = rel_path.replace("\\", "/").split("/")
        for p in parts:
            if p.startswith("agent_"):
                return p
        return "unknown"

