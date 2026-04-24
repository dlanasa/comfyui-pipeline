import subprocess
import requests
import time
import sys
import os
import argparse

UVICORN_URL = 'http://127.0.0.1:8000'
PROJECT_DIR = r'D:\ComfyUI\_study'
VENV_PYTHON = r'D:\ComfyUI\_study\.venv\Scripts\python.exe'

parser = argparse.ArgumentParser()
parser.add_argument('--restart', action='store_true', help='Kill existing uvicorn and restart')
args = parser.parse_args()


def kill_uvicorn():
    """Kill any running uvicorn/python processes on port 8000"""
    try:
        # Find and kill process on port 8000
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if ':8000' in line and 'LISTENING' in line:
                pid = line.strip().split()[-1]
                subprocess.run(['taskkill', '/f', '/pid', pid],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"  Killed process on port 8000 (PID {pid})")
        time.sleep(1)
    except:
        pass


def is_uvicorn_running():
    """Check if FastAPI is already running"""
    try:
        response = requests.get(f'{UVICORN_URL}/health', timeout=3)
        return response.status_code == 200
    except:
        return False


def start_uvicorn():
    """Start uvicorn"""
    print("🚀 Starting uvicorn...")
    return subprocess.Popen(
        [VENV_PYTHON, '-m', 'uvicorn', 'api:app', '--reload', '--port', '8000'],
        cwd=PROJECT_DIR
    )


# Handle restart flag
if args.restart:
    print("🔄 Restart requested — killing existing uvicorn...")
    kill_uvicorn()

# Check if already running
print("🔍 Checking if uvicorn is already running...")
if is_uvicorn_running() and not args.restart:
    print("✅ uvicorn already running!")
    process = None
else:
    process = start_uvicorn()
    print("⏳ Waiting for uvicorn to start...")
    for i in range(20):
        time.sleep(1)
        if is_uvicorn_running():
            print(f"✅ uvicorn started! ({i+1}s)")
            break
        if i % 5 == 4:
            print(f"  Still waiting... ({i+1}s)")
    else:
        print("❌ uvicorn failed to start. Check api.py for errors.")
        sys.exit(1)

print()
print("=" * 50)
print("✅ uvicorn ready!")
print(f"   Local API:  {UVICORN_URL}")
print(f"   API Docs:   {UVICORN_URL}/docs")
print(f"   Gallery:    {UVICORN_URL}/gallery?server=http://127.0.0.1:8188")
print("=" * 50)
print()
print("NOTE: Local development only — Railway runs its own uvicorn.")
print("Press Ctrl+C to stop.  |  Restart: python start_uvicorn.py --restart")

try:
    while True:
        time.sleep(30)
        if not is_uvicorn_running():
            print("⚠️  uvicorn stopped! Restarting...")
            process = start_uvicorn()
            time.sleep(3)
            if is_uvicorn_running():
                print("✅ uvicorn restarted!")
except KeyboardInterrupt:
    if process:
        process.terminate()
    print("\n👋 uvicorn stopped.")