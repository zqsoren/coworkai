from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import os

from backend.user_deps import get_user_workspace_manager

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

class CreateWorkspaceRequest(BaseModel):
    name: str

class RenameWorkspaceRequest(BaseModel):
    workspace_id: str
    new_name: str

@router.post("/create")
def create_workspace(req: CreateWorkspaceRequest, request: Request):
    try:
        wm = get_user_workspace_manager(request)
        workspace_id = wm.create_workspace(req.name)
        return {"status": "success", "workspace_id": workspace_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rename")
def rename_workspace(req: RenameWorkspaceRequest, request: Request):
    try:
        wm = get_user_workspace_manager(request)
        wm.rename_workspace(req.workspace_id, req.new_name)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{workspace_id}")
def delete_workspace(workspace_id: str, request: Request):
    try:
        wm = get_user_workspace_manager(request)
        wm.delete_workspace(workspace_id)
        return {"status": "success"}
    except PermissionError as e:
         raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
