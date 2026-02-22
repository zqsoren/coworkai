import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.file_manager import FileManager

# Initialize
fm = FileManager("data")

print("Setting up test...")
# Create a dummy workspace and files
ws = "test_move_ws"
fm.ensure_workspace_shared_dirs(ws)

test_file = f"{ws}/shared/test_file.txt"
test_dir = f"{ws}/shared/test_dir"

fm.create_directory(test_dir)
fm.write_file(test_file, "Hello World")
print(f"Created {test_file}")

print("Attempting to move file...")
try:
    # Target path includes the filename like RightPanel does: `${targetFolder}/${fileName}`
    target_path = f"{test_dir}/test_file.txt"
    fm.move_file(test_file, target_path)
    print("Move successful!")
except Exception as e:
    import traceback
    traceback.print_exc()

print("Cleaning up...")
try:
    # Cleanup
    import shutil
    shutil.rmtree(os.path.join("data", ws))
except:
    pass
