
import os

def mark_done():
    task_file = r"c:\Users\Lenovo\.gemini\antigravity\brain\0692496f-fd60-4dc1-bf9e-f202426a287c\task.md"
    
    with open(task_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Simple replace for the 3 items
    replacements = [
        ("- [ ] **Frontend**: React Components", "- [x] **Frontend**: React Components"),
        ("- [ ] `lib/api.ts`: Add `fetchFileTree`, `toggleFileLock`, `createDir`", "- [x] `lib/api.ts`: Add `fetchFileTree`, `toggleFileLock`, `createDir`"),
        ("- [ ] `FileTree.tsx`: Recursive component with Icons & Context Menu", "- [x] `FileTree.tsx`: Recursive component with Icons & Context Menu"),
        ("- [ ] `RightPanel.tsx`: Migrate from Accordion to 4-Zone Layout (Settings, Shared, Private, Archives)", "- [x] `RightPanel.tsx`: Migrate from Accordion to 4-Zone Layout (Settings, Shared, Private, Archives)")
    ]
    
    new_content = content
    for old, new in replacements:
        new_content = new_content.replace(old, new)
        
    if new_content != content:
        with open(task_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Marked tasks as done.")
    else:
        print("No changes made (maybe already done or text mismatch).")

if __name__ == "__main__":
    mark_done()
