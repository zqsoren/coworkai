import sys
import os
import traceback

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print(f"Project Root: {PROJECT_ROOT}")
print(f"Sys Path: {sys.path}")

try:
    print("Attempting to import backend.routers.agent...")
    import backend.routers.agent
    print("Import backend.routers.agent OK")
    
    print("Attempting to import backend.server...")
    import backend.server
    print("Import backend.server OK")
    
except Exception:
    traceback.print_exc()
