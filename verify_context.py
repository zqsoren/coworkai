
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
    
    # 1. Ensure keys files exist for testing
    fm.ensure_workspace_dirs(WORKSPACE)
    fm.ensure_agent_dirs(WORKSPACE, AGENT_ID)
    
    # Create dummy files (Direct write to bypass permission check for testing)
    static_file = os.path.join(DATA_ROOT, WORKSPACE, fm.SHARED_STATIC, "global_brand.txt")
    with open(static_file, "w", encoding="utf-8") as f:
        f.write("这是公司的品牌准则：必须使用红色。")
        
    living_file = os.path.join(DATA_ROOT, WORKSPACE, fm.SHARED_LIVING, "project_status.md")
    with open(living_file, "w", encoding="utf-8") as f:
        f.write("# 项目状态\n当前进度：99%")
    
    # 2. Get Context
    print(f"Getting context for {AGENT_ID} in {WORKSPACE}...")
    context = fm.get_agent_context(WORKSPACE, AGENT_ID)
    
    print("\n--- Context Keys ---")
    for k in context.keys():
        print(f"🔑 {k}")
        
    # 3. Check for shared files
    if "global_brand.txt" in context:
        print("\n✅ Shared Static file found in context.")
    else:
        print("\n❌ Shared Static file MISSING from context.")
        
    if "project_status.md" in context:
        print("✅ Shared Living file found in context.")
    else:
        print("❌ Shared Living file MISSING from context.")

if __name__ == "__main__":
    main()
