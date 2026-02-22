"""
SkillLoader - 动态技能加载器（Layer 3）
扫描 custom_skills/ 目录，动态加载用户自定义技能。

约定：每个技能文件 (.py) 导出：
- SKILL_NAME: str      技能名称
- SKILL_DESCRIPTION: str 技能描述
- run(**kwargs) -> str  执行函数
"""

import os
import importlib.util
from typing import Optional


class SkillLoader:
    """动态加载 custom_skills/ 下的 .py 技能文件"""

    def __init__(self, skills_dir: str):
        self.skills_dir = skills_dir
        self.skills: dict[str, dict] = {}

    def scan_and_load(self) -> int:
        """扫描目录并加载所有技能（包括标准技能），返回加载数量"""
        loaded = 0
        
        # 1. 加载标准技能 (src/skills/*.py)
        # 获取 src/skills 的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        standard_dirs = [current_dir, self.skills_dir]
        
        for directory in standard_dirs:
            if not os.path.isdir(directory):
                continue
                
            for filename in os.listdir(directory):
                if not filename.endswith(".py") or filename.startswith("_") or filename == "skill_loader.py":
                    continue
                
                filepath = os.path.join(directory, filename)
                try:
                    skill = self._load_skill_file(filepath)
                    if skill:
                        self.skills[skill["name"]] = skill
                        loaded += 1
                except Exception as e:
                    print(f"[SkillLoader] 加载 {filename} 失败: {e}")
                    
        return loaded

    def _load_skill_file(self, filepath: str) -> Optional[dict]:
        """加载单个技能文件"""
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 检查必要导出
        name = getattr(module, "SKILL_NAME", None)
        run_func = getattr(module, "run", None)
        if not name or not callable(run_func):
            return None

        return {
            "name": name,
            "description": getattr(module, "SKILL_DESCRIPTION", ""),
            "run": run_func,
            "module": module,
            "file": filepath,
        }

    def get_skill(self, name: str) -> Optional[dict]:
        """获取已加载的技能"""
        return self.skills.get(name)

    def list_skills(self) -> list[dict]:
        """列出所有已加载的技能"""
        return [
            {"name": s["name"], "description": s["description"], "file": s["file"]}
            for s in self.skills.values()
        ]

    def run_skill(self, name: str, **kwargs) -> str:
        """执行技能"""
        skill = self.skills.get(name)
        if not skill:
            return f"技能 '{name}' 未找到。可用技能: {', '.join(self.skills.keys())}"
        try:
            return skill["run"](**kwargs)
        except Exception as e:
            return f"技能 '{name}' 执行出错: {str(e)}"
