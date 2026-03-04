"""
Output Modes Router - 自定义输出模式 CRUD API（Supabase 版）
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.supabase_client import supabase

router = APIRouter(prefix="/api/output-modes", tags=["output-modes"])


class OutputModeCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    prompt: str


class OutputModeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None


@router.get("")
def list_output_modes():
    """获取所有输出模式"""
    result = supabase.table("output_modes").select("*").execute()
    return result.data


@router.post("")
def create_output_mode(req: OutputModeCreate):
    """新建自定义输出模式"""
    # 防重名
    existing = supabase.table("output_modes").select("id").eq("name", req.name).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail=f"模式名称 '{req.name}' 已存在")

    import time
    mode_id = f"custom_{int(time.time())}"

    new_mode = {
        "id": mode_id,
        "name": req.name,
        "description": req.description or "",
        "prompt": req.prompt,
        "is_builtin": False
    }
    supabase.table("output_modes").insert(new_mode).execute()
    return new_mode


@router.put("/{mode_id}")
def update_output_mode(mode_id: str, req: OutputModeUpdate):
    """更新输出模式（内建模式的名称不可改，但 prompt 可改）"""
    result = supabase.table("output_modes").select("*").eq("id", mode_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"模式 '{mode_id}' 不存在")

    mode = result.data[0]

    updates = {}

    if mode.get("is_builtin"):
        if req.name is not None and req.name != mode["name"]:
            raise HTTPException(status_code=403, detail="内建模式名称不可修改")

    if req.name is not None:
        # 检查重名
        dup = supabase.table("output_modes").select("id").eq("name", req.name).neq("id", mode_id).execute()
        if dup.data:
            raise HTTPException(status_code=400, detail=f"模式名称 '{req.name}' 已存在")
        updates["name"] = req.name
    if req.description is not None:
        updates["description"] = req.description
    if req.prompt is not None:
        updates["prompt"] = req.prompt

    if updates:
        supabase.table("output_modes").update(updates).eq("id", mode_id).execute()

    # 返回更新后的结果
    result = supabase.table("output_modes").select("*").eq("id", mode_id).execute()
    return result.data[0] if result.data else mode


@router.delete("/{mode_id}")
def delete_output_mode(mode_id: str):
    """删除自定义输出模式（内建模式不可删除）"""
    result = supabase.table("output_modes").select("*").eq("id", mode_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"模式 '{mode_id}' 不存在")

    mode = result.data[0]
    if mode.get("is_builtin"):
        raise HTTPException(status_code=403, detail=f"内建模式 '{mode['name']}' 不可删除")

    supabase.table("output_modes").delete().eq("id", mode_id).execute()
    return {"status": "success", "deleted": mode_id}
