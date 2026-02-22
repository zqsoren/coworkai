import sys
import os

print(f"CWD: {os.getcwd()}")
print(f"sys.path: {sys.path}")

try:
    from src.core.workspace import WorkspaceManager
    print("Import Successful")
except ImportError as e:
    print(f"Import Failed: {e}")
