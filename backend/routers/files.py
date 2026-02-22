from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import shutil

from src.core.file_manager import FileManager
from backend.user_deps import get_user_file_manager, get_user_data_root

router = APIRouter(prefix="/api/files", tags=["files"])

# Models
class LockRequest(BaseModel):
    path: str
    locked: bool

class MkdirRequest(BaseModel):
    path: str

class DeleteRequest(BaseModel):
    path: str

class RenameRequest(BaseModel):
    old_path: str
    new_path: str

@router.get("/tree")
def get_file_tree(workspace_id: str, request: Request, agent_id: Optional[str] = None, root_type: str = "shared"):
    """Get recursive file tree with metadata."""
    fm = get_user_file_manager(request)
    user_data_root = get_user_data_root(request)
    
    if root_type == "shared":
        start_path = os.path.join(workspace_id, "shared")
    elif root_type == "private":
        if not agent_id:
             raise HTTPException(400, "agent_id required for private tree")
        start_path = os.path.join(workspace_id, agent_id)
    elif root_type == "archives":
        if not agent_id:
             raise HTTPException(400, "agent_id required for archives tree")
        start_path = os.path.join(workspace_id, agent_id, "archives")
    else:
        raise HTTPException(400, f"Invalid root_type: {root_type}")

    full_root = os.path.join(user_data_root, start_path)
    if not os.path.exists(full_root):
        if root_type == "archives":
            os.makedirs(full_root, exist_ok=True)
        else:
            return []

    def build_tree(current_rel_path, depth=0):
        if depth > 10:
            return []
        try:
             items = fm.list_directory(current_rel_path)
        except Exception:
             return []
        
        nodes = []
        for item in items:
            if root_type == "private" and depth == 0:
                if item["name"] in ["archives", "knowledge_base", "vector_store", "context", "_metadata.json"]:
                    continue
            node = {
                "name": item["name"],
                "path": item["path"],
                "is_dir": item["is_dir"],
                "locked": item.get("locked", False),
                "children": []
            }
            if item["is_dir"]:
                node["children"] = build_tree(item["path"], depth + 1)
            nodes.append(node)
        return nodes

    return build_tree(start_path)

@router.post("/upload")
def upload_files(path: str = Form(...), files: List[UploadFile] = File(...), request: Request = None):
    """Upload files to a specific path within the workspace structure."""
    try:
        fm = get_user_file_manager(request)
        target_dir = fm._resolve_and_validate(path)
        os.makedirs(target_dir, exist_ok=True)
        saved = []
        for file in files:
            file_path = os.path.join(target_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved.append(file.filename)
        return {"status": "success", "saved": saved}
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/lock")
def set_lock(req: LockRequest, request: Request):
    try:
        fm = get_user_file_manager(request)
        fm.set_file_lock(req.path, req.locked)
        return {"status": "success", "locked": req.locked, "path": req.path}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/mkdir")
def make_directory(req: MkdirRequest, request: Request):
    try:
        fm = get_user_file_manager(request)
        fm.create_directory(req.path)
        return {"status": "success", "path": req.path}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/rename")
def rename_item(req: RenameRequest, request: Request):
    try:
        fm = get_user_file_manager(request)
        fm.move_file(req.old_path, req.new_path)
        return {"status": "success", "from": req.old_path, "to": req.new_path}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Move failed: {str(e)}")

@router.delete("/delete")
def delete_item(req: DeleteRequest, request: Request):
    try:
        fm = get_user_file_manager(request)
        resolved = fm._resolve_and_validate(req.path)
        fm._check_write_permission(resolved)
        if os.path.isfile(resolved):
            os.remove(resolved)
        elif os.path.isdir(resolved):
            shutil.rmtree(resolved)
        return {"status": "success", "path": req.path}
    except Exception as e:
        raise HTTPException(500, str(e))
