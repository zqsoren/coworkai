
import os
import shutil
import glob
from src.core.file_manager import FileManager

def migrate_workspace(workspace_name="workspace_default"):
    project_root = os.getcwd()
    data_root = os.path.join(project_root, "data")
    fm = FileManager(data_root)
    
    print(f"Starting Migration for: {workspace_name}")
    
    # 1. Migrate Workspace Shared
    shared_root = os.path.join(data_root, workspace_name, "shared")
    if os.path.exists(shared_root):
        print(f"Processing Shared Area: {shared_root}")
        migrate_legacy_dir(fm, shared_root, "static", locked=True)
        migrate_legacy_dir(fm, shared_root, "active", locked=False)
        
    # 2. Migrate Agents
    ws_path = os.path.join(data_root, workspace_name)
    agents = [d for d in os.listdir(ws_path) if os.path.isdir(os.path.join(ws_path, d))]
    
    for agent_id in agents:
        if agent_id == "shared" or agent_id.startswith("."):
            continue
            
        print(f"Processing Agent: {agent_id}")
        agent_context_root = os.path.join(ws_path, agent_id, "context")
        
        if os.path.exists(agent_context_root):
            # Target is Agent Root
            target_dir = os.path.join(ws_path, agent_id)
            
            # Migrate Static
            migrate_legacy_dir(fm, agent_context_root, "static", locked=True, target_override=target_dir)
            
            # Migrate Active
            migrate_legacy_dir(fm, agent_context_root, "active", locked=False, target_override=target_dir)
            
            # Migrate Archives (Keep in archives dir, but move from context/archives to archives/)
            # V2 Archives path: agent/archives
            # Legacy Archives path: agent/context/archives
            legacy_archives = os.path.join(agent_context_root, "archives")
            v2_archives = os.path.join(target_dir, "archives")
            
            if os.path.exists(legacy_archives):
                print(f"  Moving Archives: {legacy_archives} -> {v2_archives}")
                os.makedirs(v2_archives, exist_ok=True)
                for item in os.listdir(legacy_archives):
                    src = os.path.join(legacy_archives, item)
                    dst = os.path.join(v2_archives, item)
                    if not os.path.exists(dst):
                         shutil.move(src, dst)
                
                # Cleanup
                try:
                    os.rmdir(legacy_archives)
                except:
                    pass

            # Try to cleanup context dir if empty
            try:
                if not os.listdir(agent_context_root):
                    os.rmdir(agent_context_root)
            except:
                pass


def migrate_legacy_dir(fm: FileManager, base_path: str, sub_name: str, locked: bool, target_override: str = None):
    """
    Moves files from base_path/sub_name to base_path (or target_override)
    and sets lock status.
    """
    source_dir = os.path.join(base_path, sub_name)
    if not os.path.exists(source_dir):
        return

    # Determine target directory
    target_dir = target_override if target_override else base_path
    
    print(f"  Migrating {sub_name}: {source_dir} -> {target_dir} (Locked={locked})")
    
    files_moved = 0
    for item in os.listdir(source_dir):
        src_path = os.path.join(source_dir, item)
        dst_path = os.path.join(target_dir, item)
        
        if os.path.isfile(src_path):
            # Move
            if not os.path.exists(dst_path):
                shutil.move(src_path, dst_path)
                files_moved += 1
            else:
                print(f"    Skipping {item} (Target exists)")
                
            # Set Lock
            # Use FM relative path
            # Need strict relative path from data_root
            rel_path = os.path.relpath(dst_path, fm.data_root)
            fm.set_file_lock(rel_path, locked)
            
        elif os.path.isdir(src_path):
             # Move folder
             if not os.path.exists(dst_path):
                 shutil.move(src_path, dst_path)
                 files_moved += 1
                 # TODO: Recursive lock set? For now V2 lock is file-based or folder-based?
                 # FM.set_file_lock works on folders too in _save_metadata logic (it just stores the path)
                 rel_path = os.path.relpath(dst_path, fm.data_root)
                 fm.set_file_lock(rel_path, locked)
             else:
                 print(f"    Skipping Folder {item} (Target exists)")

    print(f"    Moved {files_moved} items.")
    
    # Cleanup empty source dir
    try:
        os.rmdir(source_dir)
    except OSError:
        pass # Not empty

if __name__ == "__main__":
    migrate_workspace()
