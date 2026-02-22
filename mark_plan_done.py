
import os

def mark_plan_done():
    plan_file = r"c:\Users\Lenovo\.gemini\antigravity\brain\0692496f-fd60-4dc1-bf9e-f202426a287c\implementation_plan.md"
    
    with open(plan_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Simple replace for Frontend Plan
    replacements = [
        ("- [ ] **API Client**: Update `frontend/src/lib/api.ts` with new endpoints.", "- [x] **API Client**: Update `frontend/src/lib/api.ts` with new endpoints."),
        ("- [ ] **Component**: Create `frontend/src/components/FileTree.tsx`.", "- [x] **Component**: Create `frontend/src/components/FileTree.tsx`."),
        ("- [ ] Recursive rendering of nodes.", "- [x] Recursive rendering of nodes."),
        ("- [ ] Icons: Folder/File, Lock/Unlock.", "- [x] Icons: Folder/File, Lock/Unlock."),
        ("- [ ] Actions: Click to view (preview), toggle lock (if authorized), context menu (New Folder/Delete).", "- [x] Actions: Click to view (preview), toggle lock (if authorized), context menu (New Folder/Delete)."),
        ("- [ ] **Integration**: Update `frontend/src/components/RightPanel.tsx`.", "- [x] **Integration**: Update `frontend/src/components/RightPanel.tsx`."),
        ("- [ ] Replace `Accordion` with new Layout.", "- [x] Replace `Accordion` with new Layout."),
        ("- [ ] Zone 1: Settings/KB Buttons.", "- [x] Zone 1: Settings/KB Buttons."),
        ("- [ ] Zone 2: Workspace Shared (Tree).", "- [x] Zone 2: Workspace Shared (Tree)."),
        ("- [ ] Zone 3: Agent Private (Tree).", "- [x] Zone 3: Agent Private (Tree)."),
        ("- [ ] Zone 4: Archives (Tree).", "- [x] Zone 4: Archives (Tree).")
    ]
    
    new_content = content
    for old, new in replacements:
        new_content = new_content.replace(old, new)
        
    if new_content != content:
        with open(plan_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Marked plan tasks as done.")
    else:
        print("No changes made.")

if __name__ == "__main__":
    mark_plan_done()
