
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from src.core.file_manager import FileManager

DATA_ROOT = "data"
WORKSPACE = "workspace_啊啊"
AGENT_ID = "agent_fan"

def main():
    fm = FileManager(DATA_ROOT)
    
    # 1. Ensure Agent Static Dir exists
    agent_static_dir = os.path.join(DATA_ROOT, WORKSPACE, AGENT_ID, "context", "static")
    os.makedirs(agent_static_dir, exist_ok=True)
    
    # 2. Create dummy static file
    static_file_path = os.path.join(agent_static_dir, "legacy_static_doc.txt")
    with open(static_file_path, "w", encoding="utf-8") as f:
        f.write("This is a legacy static document that should be read.")
    print(f"Created/Overwrote: {static_file_path}")

    # 3. Get Context
    print(f"Getting context for {AGENT_ID} in {WORKSPACE}...")
    context = fm.get_agent_context(WORKSPACE, AGENT_ID)
    
    print("\n--- Context Keys ---")
    for k in context.keys():
        print(f"🔑 {k}")
        
    # 4. Verification
    if "legacy_static_doc.txt" in context:
        print("\n✅ Agent Static file found in context.")
    else:
        print("\n❌ Agent Static file MISSING from context.")

if __name__ == "__main__":
    main()
