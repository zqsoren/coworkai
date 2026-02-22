from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from src.core.file_manager import FileManager, ChangeRequest
import os

router = APIRouter(prefix="/api/sys", tags=["system"])

# Dependencies (Re-init for now, similar to other routers)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_ROOT = os.path.join(PROJECT_ROOT, "data")
file_manager = FileManager(DATA_ROOT)

class ApplyChangeRequest(BaseModel):
    file_path: str
    original_content: str
    new_content: str
    diff_lines: List[str]
    status: str = "pending" # Should be passed as "approved" to apply, or we override it here

@router.post("/change/apply")
def apply_change(request: ApplyChangeRequest):
    """Apply a change request to the file system."""
    try:
        # Construct ChangeRequest object
        cr = ChangeRequest(
            file_path=request.file_path,
            original_content=request.original_content,
            new_content=request.new_content,
            diff_lines=request.diff_lines,
            status="approved" # Force approved status to apply
        )
        
        file_manager.apply_change(cr)
        return {"status": "success", "message": f"Change applied to {request.file_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
