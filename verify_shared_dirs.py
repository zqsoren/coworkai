
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from src.core.file_manager import FileManager

DATA_ROOT = "data"
WORKSPACE = "workspace_啊啊"

def main():
    fm = FileManager(DATA_ROOT)
    
    # 1. Ensure dirs
    print(f"Ensuring workspace dirs for {WORKSPACE}...")
    fm.ensure_workspace_dirs(WORKSPACE)
    
    static_path = os.path.join(DATA_ROOT, WORKSPACE, "static_assets")
    living_path = os.path.join(DATA_ROOT, WORKSPACE, "living_docs")
    
    if os.path.exists(static_path):
        print(f"✅ static_assets exists: {static_path}")
    else:
        print(f"❌ static_assets MISSING: {static_path}")
        
    if os.path.exists(living_path):
        print(f"✅ living_docs exists: {living_path}")
    else:
        print(f"❌ living_docs MISSING: {living_path}")

    # 2. Test Write to Static (Should Fail)
    print("\nTesting Write to Static Assets...")
    try:
        fm.write_file(f"{WORKSPACE}/static_assets/test.txt", "Should fail")
        print("❌ Write to static_assets SUCCEEDED (Unexpected)")
    except PermissionError as e:
        print(f"✅ Write to static_assets FAILED as expected: {e}")
    except Exception as e:
        print(f"❓ Unexpected error writing to static: {type(e)} {e}")

    # 3. Test Write to Living Docs (Should return ChangeRequest)
    print("\nTesting Write to Living Docs...")
    try:
        cr = fm.write_file(f"{WORKSPACE}/living_docs/todo.md", "# New Todo")
        if cr:
            print(f"✅ Change Request created: {cr.file_path} [Status: {cr.status}]")
        else:
            print("❌ No Change Request returned (maybe direct write?)")
    except Exception as e:
        print(f"❌ Error writing to living_docs: {e}")

if __name__ == "__main__":
    main()
