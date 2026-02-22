import webview
import sys
import os
import socket
import subprocess
import time
import threading
import contextlib
import requests
import signal

# Configuration
BACKEND_PORT = 8000
FRONTEND_PORT = 5173
BACKEND_URL = f"http://localhost:{BACKEND_PORT}"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"

def is_port_open(port):
    """Check if a port is currently open."""
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        try:
            s.connect(('localhost', port))
            return True
        except ConnectionRefusedError:
            return False

def wait_for_service(url, timeout=30, name="Service"):
    """Wait for a service to become responsive."""
    print(f"Waiting for {name} at {url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(url, timeout=1)
            print(f"✅ {name} serves at {url}")
            return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.5)
    print(f"❌ {name} failed to start.")
    return False

def run_backend():
    """Launch the FastAPI backend."""
    print("🚀 Launching Backend...")
    # Assume we are in project root
    cmd = [sys.executable, "backend/server.py"]
    
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    
    return subprocess.Popen(
        cmd,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        startupinfo=startupinfo
    )

def run_frontend():
    """Launch the Vite frontend."""
    print("🚀 Launching Frontend...")
    # Use npm run dev
    # On Windows, npm is a bat file, so shell=True or finding npm.cmd is needed.
    # shell=True is simpler for "npm" command resolution.
    cmd = "npm run dev"
    
    return subprocess.Popen(
        cmd,
        cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend"),
        shell=True
        # We don't hide this window easily with shell=True, but let's try keeping it managed
    )

def main():
    processes = []

    # Check/Start Backend
    if not is_port_open(BACKEND_PORT):
        backend_proc = run_backend()
        processes.append(backend_proc)
        if not wait_for_service(BACKEND_URL, timeout=15, name="Backend"):
             print("Backend failed. Exiting.")
             return
    else:
        print(f"✅ Backend already running on port {BACKEND_PORT}")

    # Check/Start Frontend
    if not is_port_open(FRONTEND_PORT):
        frontend_proc = run_frontend()
        processes.append(frontend_proc)
        # Wait for Vite to bind port. Vite usually serves immediately but 'npm run dev' takes a moment.
        # We can poll the URL.
        if not wait_for_service(FRONTEND_URL, timeout=30, name="Frontend"):
             print("Frontend failed. Exiting.")
             # Kill backend if we started it
             if backend_proc in processes: backend_proc.terminate()
             return
    else:
        print(f"✅ Frontend already running on port {FRONTEND_PORT}")

    def on_closed():
        print("🛑 Window closed. Cleaning up processes...")
        for p in processes:
            try:
                # Basic terminate
                p.terminate()
                
                # Windows taskill for aggressive cleanup of npm tree
                if os.name == 'nt' and p.pid:
                     subprocess.call(['taskkill', '/F', '/T', '/PID', str(p.pid)])
            except Exception as e:
                print(f"Error killing process: {e}")

    # Create Window
    webview.create_window(
        "AgentOS", 
        url=FRONTEND_URL, 
        width=1280, 
        height=800,
        resizable=True,
        confirm_close=True
    )
    
    try:
        webview.start(debug=True)
    except Exception as e:
        print(f"WebView Error: {e}")
    finally:
        on_closed()

if __name__ == '__main__':
    main()
