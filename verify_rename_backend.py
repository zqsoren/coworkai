import os
import sys
import json

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.file_manager import FileManager
from src.core.workspace import WorkspaceManager

DATA_ROOT = os.path.join(PROJECT_ROOT, "data")
file_manager = FileManager(DATA_ROOT)
workspace_manager = WorkspaceManager(file_manager)

def test_rename():
    print("Testing Workspace Rename...")
    
    # 1. Create a test workspace
    try:
        ws_id = workspace_manager.create_workspace("Test Rename WS")
        print(f"Created workspace: {ws_id}")
    except FileExistsError:
        ws_id = "workspace_test_rename_ws"
        print(f"Workspace {ws_id} already exists, using it.")

    # 2. Rename it
    new_name = "Renamed Test WS"
    print(f"Renaming to: {new_name}")
    workspace_manager.rename_workspace(ws_id, new_name)
    
    # 3. Verify
    workspaces = workspace_manager.list_workspaces()
    found = False
    for ws in workspaces:
        if ws["id"] == ws_id:
            print(f"Found workspace {ws['id']}: name='{ws['name']}'")
            if ws["name"] == new_name:
                print("SUCCESS: Rename persisted.")
                found = True
            else:
                print(f"FAILURE: Name mismatch. Expected '{new_name}', got '{ws['name']}'")
    
    if not found:
        print("FAILURE: Workspace not found in list.")

    # Cleanup
    # workspace_manager.delete_workspace(ws_id)

if __name__ == "__main__":
    test_rename()
