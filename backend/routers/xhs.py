"""
XHS (小红书) Cookie 管理 API
用户粘贴自己的小红书 Cookie，存储在用户数据目录中，
供 xhs_scraper 技能注入到无头浏览器中获取点赞/评论等数据。
"""

import os
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/xhs", tags=["xhs"])

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class XhsCookieRequest(BaseModel):
    cookie: str


def _get_cookie_path(user_id: str) -> str:
    """获取用户 XHS Cookie 文件路径"""
    return os.path.join(PROJECT_ROOT, "data", user_id, ".xhs_cookie")


@router.post("/cookie")
def save_xhs_cookie(req: XhsCookieRequest, request: Request):
    """保存用户的小红书 Cookie"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(401, "Not authenticated")

    cookie_path = _get_cookie_path(user_id)
    os.makedirs(os.path.dirname(cookie_path), exist_ok=True)

    with open(cookie_path, "w", encoding="utf-8") as f:
        f.write(req.cookie.strip())

    return {"status": "success", "message": "Cookie 已保存"}


@router.get("/cookie")
def get_xhs_cookie(request: Request):
    """读取用户已保存的小红书 Cookie"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(401, "Not authenticated")

    cookie_path = _get_cookie_path(user_id)
    if os.path.exists(cookie_path):
        with open(cookie_path, "r", encoding="utf-8") as f:
            return {"cookie": f.read().strip()}

    return {"cookie": ""}


@router.delete("/cookie")
def delete_xhs_cookie(request: Request):
    """删除用户的小红书 Cookie"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(401, "Not authenticated")

    cookie_path = _get_cookie_path(user_id)
    if os.path.exists(cookie_path):
        os.remove(cookie_path)

    return {"status": "success", "message": "Cookie 已删除"}
