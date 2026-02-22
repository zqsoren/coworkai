
import os

def update_plan_md():
    plan_file = r"c:\Users\Lenovo\.gemini\antigravity\brain\0692496f-fd60-4dc1-bf9e-f202426a287c\implementation_plan.md"
    
    with open(plan_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    new_backend_section = """## 2. API Layer (backend/routers/files.py)
- [x] **Create Router**: `backend/routers/files.py`
    - [x] Endpoint `GET /list`: Params `workspace_id`, `agent_id`, `root_type` (shared/private). Returns nested JSON tree.
    - [x] Endpoint `POST /lock`: Params `path`, `locked`. Calls `fm.set_file_lock`.
    - [x] Endpoint `POST /mkdir`: Params `path`. Calls `fm.create_directory`.
    - [x] Endpoint `DELETE /delete`: Params `path`. Calls `os.remove` or `shutil.rmtree` (with safety check).
- [x] **Register**: Add `app.include_router(files.router)` in `backend/server.py`.

## 3. Frontend (React)
- [ ] **API Client**: Update `frontend/src/lib/api.ts` with new endpoints.
- [ ] **Component**: Create `frontend/src/components/FileTree.tsx`.
    - [ ] Recursive rendering of nodes.
    - [ ] Icons: Folder/File, Lock/Unlock.
    - [ ] Actions: Click to view (preview), toggle lock (if authorized), context menu (New Folder/Delete).
- [ ] **Integration**: Update `frontend/src/components/RightPanel.tsx`.
    - [ ] Replace `Accordion` with new Layout.
    - [ ] Zone 1: Settings/KB Buttons.
    - [ ] Zone 2: Workspace Shared (Tree).
    - [ ] Zone 3: Agent Private (Tree).
    - [ ] Zone 4: Archives (Tree)."""

    # Look for "## 2. API Layer" in the old content and replace from there
    marker = "## 2. API Layer"
    
    if marker in content:
        start_idx = content.find(marker)
        pre = content[:start_idx]
        
        # We append our new plan
        new_content = pre + new_backend_section
        
        with open(plan_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Updated implementation_plan.md successfully.")
    else:
        print("Could not find marker.")

if __name__ == "__main__":
    update_plan_md()
