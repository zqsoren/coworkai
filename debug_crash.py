import sys
import os
import traceback

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    print("Importing src.app...")
    import src.app
    print("Imported.")
    
    print("Running init_platform...")
    # init_platform is decorated. It might fail if no streamlit context.
    # We hope it runs enough to hit logic errors.
    try:
        src.app.init_platform()
        print("init_platform successful!")
        with open("crash_log.txt", "w") as f:
            f.write("Success! init_platform finished.")
    except Exception as e:
        # If it's a StreamlitAPIException about missing context, we might ignore it 
        # but better to see it.
        with open("crash_log.txt", "w") as f:
            f.write(traceback.format_exc())

except Exception:
    with open("crash_log.txt", "w") as f:
        f.write(traceback.format_exc())
