import os
import sys
import time
import socketserver
import http.server
import threading
import subprocess
import webbrowser

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(base_dir, "frontend")

    print("=" * 55)
    print(" FixMyCampus - Development Server")
    print("=" * 55)

    python_exe = os.path.join(base_dir, ".venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable

    print("[1/2] Starting FastAPI backend on http://127.0.0.1:8000 ...")
    backend_proc = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=base_dir
    )

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

    time.sleep(1.5)
    print("Opening browser tabs...")
    try:
        webbrowser.open("http://127.0.0.1:5500/index.html")
        webbrowser.open("http://127.0.0.1:5500/login.html")
    except Exception as e:
        print(f"Note: Could not open browser automatically: {e}")

    print("\nFixMyCampus is now live! Press Ctrl+C in this terminal to stop.")
    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down FixMyCampus...")
        backend_proc.terminate()
        frontend_server.shutdown()
        print("Servers stopped successfully.")

if __name__ == "__main__":
    main()
