"""
Output Modes Router - 自定义输出模式 CRUD API
"""

import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/output-modes", tags=["output-modes"])

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_MODES_FILE = os.path.join(PROJECT_ROOT, "config", "output_modes.json")

DEFAULT_MODES = [
    {
        "id": "normal",
        "name": "普通模式",
        "description": "正常输出，无特殊限制",
        "prompt": "",
        "is_builtin": True
    },
    {
        "id": "efficient",
        "name": "高效模式",
        "description": "简短精炼，分离回答与思考",
        "prompt": "## 输出要求（高效模式）\n1. 请以高效的模式进行回答，不要说太多废话、夸奖的话\n2. 将输出分为两个部分：\n   - 【回答】：对用户问题的直接回答，不要有多余修饰\n   - 【思考】：你的理由和思考过程，精炼有说服力\n\n示例格式：\n【回答】\n（简洁的答案）\n\n【思考】\n（精炼的推理过程）",
        "is_builtin": True
    },
    {
        "id": "concise",
        "name": "精简模式",
        "description": "极简回答，直击要点",
        "prompt": "## 输出要求（精简模式）\n1. 直接回答问题，极度简短\n2. 不要解释、不要废话、不要客套\n3. 只输出最核心的答案",
        "is_builtin": True
    }
]


class OutputModeCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    prompt: str


class OutputModeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None


def _load_modes() -> list:
    """加载输出模式列表，如果文件不存在则初始化"""
    if not os.path.exists(OUTPUT_MODES_FILE):
        os.makedirs(os.path.dirname(OUTPUT_MODES_FILE), exist_ok=True)
        _save_modes(DEFAULT_MODES)
        return DEFAULT_MODES
    try:
        with open(OUTPUT_MODES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_MODES


def _save_modes(modes: list) -> None:
    """保存输出模式列表"""
    os.makedirs(os.path.dirname(OUTPUT_MODES_FILE), exist_ok=True)
    with open(OUTPUT_MODES_FILE, "w", encoding="utf-8") as f:
        json.dump(modes, f, ensure_ascii=False, indent=2)


@router.get("")
def list_output_modes():
    """获取所有输出模式"""
    return _load_modes()


@router.post("")
def create_output_mode(req: OutputModeCreate):
    """新建自定义输出模式"""
    modes = _load_modes()

    # 生成唯一 ID
    import time
    mode_id = f"custom_{int(time.time())}"

    # 防重名
    if any(m["name"] == req.name for m in modes):
        raise HTTPException(status_code=400, detail=f"模式名称 '{req.name}' 已存在")

    new_mode = {
        "id": mode_id,
        "name": req.name,
        "description": req.description or "",
        "prompt": req.prompt,
        "is_builtin": False
    }
    modes.append(new_mode)
    _save_modes(modes)
    return new_mode


@router.put("/{mode_id}")
def update_output_mode(mode_id: str, req: OutputModeUpdate):
    """更新输出模式（内建模式的名称不可改，但 prompt 可改）"""
    modes = _load_modes()
    idx = next((i for i, m in enumerate(modes) if m["id"] == mode_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"模式 '{mode_id}' 不存在")

    mode = modes[idx]

    # 内建模式：只允许修改 prompt 和 description，不允许改 name
    if mode.get("is_builtin"):
        if req.name is not None and req.name != mode["name"]:
            raise HTTPException(status_code=403, detail="内建模式名称不可修改")

    if req.name is not None:
        # 检查重名
        if any(m["name"] == req.name and m["id"] != mode_id for m in modes):
            raise HTTPException(status_code=400, detail=f"模式名称 '{req.name}' 已存在")
        mode["name"] = req.name
    if req.description is not None:
        mode["description"] = req.description
    if req.prompt is not None:
        mode["prompt"] = req.prompt

    _save_modes(modes)
    return mode


@router.delete("/{mode_id}")
def delete_output_mode(mode_id: str):
    """删除自定义输出模式（内建模式不可删除）"""
    modes = _load_modes()
    idx = next((i for i, m in enumerate(modes) if m["id"] == mode_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"模式 '{mode_id}' 不存在")

    mode = modes[idx]
    if mode.get("is_builtin"):
        raise HTTPException(status_code=403, detail=f"内建模式 '{mode['name']}' 不可删除")

    modes.pop(idx)
    _save_modes(modes)
    return {"status": "success", "deleted": mode_id}
