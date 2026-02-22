import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.file_manager import FileManager
import shutil

fm = FileManager("data")
ws = "workspace_zzzap"
fm.ensure_workspace_shared_dirs(ws)

# Test 1: Move file to existing dir
try:
    src = f"{ws}/shared/test_move.txt"
    dst_dir = f"{ws}/shared/test_dir"
    dst = f"{dst_dir}/test_move.txt"
    fm.write_file(src, "test")
    fm.create_directory(dst_dir)
    fm.move_file(src, dst)
    print("Test 1 SUCCESS")
except Exception as e:
    print(f"Test 1 FAILED: {type(e).__name__}({e})")

# Test 2: Move directory
try:
    src_dir = f"{ws}/shared/src_folder"
    dst_dir = f"{ws}/shared/dst_folder"
    dst = f"{dst_dir}/src_folder"
    fm.create_directory(src_dir)
    fm.create_directory(dst_dir)
    fm.move_file(src_dir, dst)
    print("Test 2 SUCCESS")
except Exception as e:
    print(f"Test 2 FAILED: {type(e).__name__}({e})")

# Test 3: Move over existing file
try:
    src = f"{ws}/shared/file_a.txt"
    dst = f"{ws}/shared/file_b.txt" # This file exists
    fm.write_file(src, "A")
    fm.write_file(dst, "B")
    fm.move_file(src, dst)
    print("Test 3 SUCCESS")
except Exception as e:
    print(f"Test 3 FAILED: {type(e).__name__}({e})")

# Cleanup workspace dir (be careful!)
try:
    shutil.rmtree(f"data/{ws}/shared/test_dir", ignore_errors=True)
    shutil.rmtree(f"data/{ws}/shared/src_folder", ignore_errors=True)
    shutil.rmtree(f"data/{ws}/shared/dst_folder", ignore_errors=True)
    for f in ["test_move.txt", "file_a.txt", "file_b.txt"]:
        if os.path.exists(f"data/{ws}/shared/{f}"):
            os.remove(f"data/{ws}/shared/{f}")
except:
    pass
