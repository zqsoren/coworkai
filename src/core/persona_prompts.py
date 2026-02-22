"""
Persona Prompts - 动态输出模式提示词
职责：从 config/output_modes.json 加载输出模式提示词
"""

import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_MODES_FILE = os.path.join(PROJECT_ROOT, "config", "output_modes.json")

# 内置兜底（文件不存在时使用）
_BUILTIN_PROMPTS = {
    "normal": "",
    "efficient": """## 输出要求（高效模式）
1. 请以高效的模式进行回答，不要说太多废话、夸奖的话
2. 将输出分为两个部分：
   - 【回答】：对用户问题的直接回答，不要有多余修饰
   - 【思考】：你的理由和思考过程，精炼有说服力

示例格式：
【回答】
（简洁的答案）

【思考】
（精炼的推理过程）""",
    "concise": """## 输出要求（精简模式）
1. 直接回答问题，极度简短
2. 不要解释、不要废话、不要客套
3. 只输出最核心的答案"""
}


def _load_modes_map() -> dict:
    """从 JSON 文件加载模式 id -> prompt 映射"""
    if os.path.exists(OUTPUT_MODES_FILE):
        try:
            with open(OUTPUT_MODES_FILE, "r", encoding="utf-8") as f:
                modes = json.load(f)
            return {m["id"]: m.get("prompt", "") for m in modes}
        except Exception:
            pass
    return dict(_BUILTIN_PROMPTS)


def get_persona_prompt(mode: str) -> str:
    """
    获取指定输出模式的提示词（动态从 JSON 加载）

    Args:
        mode: 模式 ID（如 'normal', 'efficient', 'concise' 或自定义 ID）

    Returns:
        对应的提示词字符串（普通模式返回空字符串）
    """
    modes_map = _load_modes_map()
    return modes_map.get(mode, "")
