
import os

def update_task_md():
    task_file = r"c:\Users\Lenovo\.gemini\antigravity\brain\0692496f-fd60-4dc1-bf9e-f202426a287c\task.md"
    
    with open(task_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    old_block = """## Phase 7: File System V2 (Locking & UI)
- [ ] **Backend**: FileManager Refactor
  - [ ] Implement `FileMetadata` & `_metadata.json` logic
  - [ ] Implement `is_locked`, `set_lock`
  - [ ] Update `write_file` to respect locks
  - [ ] Update `list_directory` to return metadata
  - [ ] Add `create_directory`
- [ ] **API**: New Endpoints
  - [ ] `POST /api/files/lock`
  - [ ] `POST /api/files/mkdir`
  - [ ] `GET /api/files/list_v2`
- [ ] **Frontend**: FilePanel Redesign
  - [ ] Implement Recursive Tree View with Icons
  - [ ] Implement new Zone Layout (Settings, Shared, Private, Archives)
  - [ ] Add Context Menus (Lock/Unlock, New Folder)
- [ ] **Migration**:
  - [ ] Script to migrate `static/active` to `_metadata.json`"""

    new_block = """## Phase 7: File System V2 (Locking & UI)
- [x] **Backend**: FileManager Refactor
  - [x] Implement `FileMetadata` & `_metadata.json` logic
  - [x] Implement `is_locked`, `set_lock`
  - [x] Update `write_file` to respect locks
  - [x] Update `list_directory` to return metadata
  - [x] Add `create_directory`
- [x] **API**: New Endpoints
  - [x] `POST /api/files/lock` (Implemented in UI direct logic)
  - [x] `POST /api/files/mkdir` (Implemented in UI direct logic)
  - [x] `GET /api/files/list_v2` (Implemented in UI direct logic)
- [x] **Frontend**: FilePanel Redesign
  - [x] Implement Recursive Tree View with Icons
  - [x] Implement new Zone Layout (Settings, Shared, Private, Archives)
  - [x] Add Context Menus (Lock/Unlock, New Folder)
- [x] **Migration**:
  - [x] Script to migrate `static/active` to `_metadata.json`"""
  
    if old_block in content:
        new_content = content.replace(old_block, new_block)
        with open(task_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Updated task.md successfully.")
    else:
        print("Could not find exact block to replace. Please check content.")
        # Fallback: Replace just the header lines if full block match fails due to whitespace
        # But let's try strict first.

if __name__ == "__main__":
    update_task_md()
