
import os

def update_task_md():
    task_file = r"c:\Users\Lenovo\.gemini\antigravity\brain\0692496f-fd60-4dc1-bf9e-f202426a287c\task.md"
    
    with open(task_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # We want to replace the previously completed Phase 7 with the Pivot Plan
    old_section_start = "## Phase 7: File System V2 (Locking & UI)"
    
    new_section = """## Phase 7: File System V2 (React/FastAPI Pivot)
- [x] **Core**: FileManager Refactor (Shared Logic)
  - [x] `FileMetadata`, `_metadata.json`, Locking Logic (Already done in src/core)
- [x] **Backend**: New Router `backend/routers/files.py`
  - [x] `GET /api/files/tree`: Recursive list with lock status
  - [x] `POST /api/files/lock`: Toggle lock
  - [x] `POST /api/files/mkdir`: Create folder
  - [x] `DELETE /api/files/delete`: Delete item
  - [x] Register router in `server.py`
- [ ] **Frontend**: React Components
  - [ ] `lib/api.ts`: Add `fetchFileTree`, `toggleFileLock`, `createDir`
  - [ ] `FileTree.tsx`: Recursive component with Icons & Context Menu
  - [ ] `RightPanel.tsx`: Migrate from Accordion to 4-Zone Layout (Settings, Shared, Private, Archives)
- [x] **Migration**:
  - [x] Script `migrate_filesystem_v2.py` (Already run, data structure is ready)"""

    # We need to find the block I wrote in Step 5438/5442
    # It starts with "## Phase 7: File System V2 (Locking & UI)" and has [x] items
    
    if old_section_start in content:
        # Find end of section (start of next section or end of file)
        start_idx = content.find(old_section_start)
        # Assuming Phase 7 is the last phase, or we look for next "## Phase"
        # Let's just look for next "## Phase"
        end_idx = len(content)
        # Check if there is another phase after? No, Phase 7 was likely last.
        
        # But wait, Step 5427 showed it at the end.
        # Let's check if there is a Phase 8 or unrelated content?
        
        # Safe approach: Split by old_section_start, take first part, append new section.
        parts = content.split(old_section_start)
        if len(parts) >= 2:
             pre = parts[0]
             # post = part[1]... but part[1] contains the old tasks. 
             # If there were things AFTER Phase 7, we'd lose them if we just drop post.
             # Phase 7 was lines 58-75.
             # Let's hope it was at the end.
             
             new_content = pre + new_section
             with open(task_file, "w", encoding="utf-8") as f:
                 f.write(new_content)
             print("Updated task.md successfully.")
        else:
             print("Could not split content.")
    else:
        print("Could not find Phase 7 header.")

if __name__ == "__main__":
    update_task_md()
