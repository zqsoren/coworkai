import sys
import os

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.server import app

print("Registered Routes:")
for route in app.routes:
    print(f"{route.methods} {route.path}")
