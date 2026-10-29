import os
import sys
import time
import socket
import socketserver
import http.server
import threading
import subprocess
import webbrowser
import urllib.request

def check_dependencies():
    required = ["fastapi", "uvicorn", "sqlalchemy", "pydantic", "bcrypt", "jwt"]
    missing = []
    for mod in required:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        print("[WARNING] The following required packages are missing:")
        print(f"          {', '.join(missing)}")
        print("          Run: pip install -r requirements.txt")

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def wait_for_backend(url: str = "http://127.0.0.1:8000/health", timeout: float = 10.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(base_dir, "frontend")

    print("=" * 55)
    print(" FixMyCampus - Development Server")
    print("=" * 55)

    check_dependencies()

    if is_port_in_use(8000):
        print("[NOTICE] Port 8000 is already in use.")
        print("         If FastAPI is already running, the frontend will connect to it.")
    if is_port_in_use(5500):
        print("[ERROR] Port 5500 is already in use by another process.")
        print("        Please close the process on port 5500 or use: python -m http.server 5173 --directory frontend")
        return

    python_exe = os.path.join(base_dir, ".venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable

    backend_proc = None
    if not is_port_in_use(8000):
        print("[1/2] Starting FastAPI backend on http://127.0.0.1:8000 ...")
        backend_proc = subprocess.Popen(
            [python_exe, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=base_dir
        )
    else:
        print("[1/2] Existing FastAPI backend detected on http://127.0.0.1:8000")

    print("[2/2] Starting Frontend static server on http://127.0.0.1:5500 ...")
    class FrontendHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=frontend_dir, **kwargs)
        def log_message(self, format, *args):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    frontend_server = socketserver.TCPServer(("127.0.0.1", 5500), FrontendHandler)
    frontend_thread = threading.Thread(target=frontend_server.serve_forever, daemon=True)
    frontend_thread.start()

    print("\nServer URLs:")
    print("  • Public Portal:    http://127.0.0.1:5500/index.html")
    print("  • Login:            http://127.0.0.1:5500/login.html")
    print("  • Admin Dashboard:  http://127.0.0.1:5500/admin.html  (login required)")
    print("  • Track Issue:      http://127.0.0.1:5500/track.html")
    print("  • Backend API Docs: http://127.0.0.1:8000/docs")
    print("=" * 55)

    print("Checking backend readiness...")
    if wait_for_backend():
        print("Backend is ready!")
    else:
        print("Backend starting...")

    print("Opening browser portal...")
    try:
        webbrowser.open("http://127.0.0.1:5500/index.html")
    except Exception as e:
        print(f"Note: Could not open browser automatically: {e}")

    print("\nFixMyCampus is now live! Press Ctrl+C in this terminal to stop.")
    try:
        while True:
            if backend_proc and backend_proc.poll() is not None:
                print("\nBackend process exited unexpectedly.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down FixMyCampus...")
    finally:
        if backend_proc and backend_proc.poll() is None:
            backend_proc.terminate()
            try:
                backend_proc.wait(timeout=3)
            except Exception:
                backend_proc.kill()
        frontend_server.shutdown()
        frontend_server.server_close()
        print("Servers stopped successfully.")

if __name__ == "__main__":
    main()
