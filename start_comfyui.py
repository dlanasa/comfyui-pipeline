import subprocess
import requests
import time
import sys

COMFYUI_BAT = r'D:\ComfyUI\run_nvidia_gpu_study.bat'
COMFYUI_URL = 'http://127.0.0.1:8188'


def is_comfyui_running():
    """Check if ComfyUI is already running"""
    try:
        response = requests.get(f'{COMFYUI_URL}/system_stats', timeout=3)
        return response.status_code == 200
    except:
        return False


def start_comfyui():
    """Start ComfyUI via bat file"""
    print("🚀 Starting ComfyUI...")
    subprocess.Popen(
        COMFYUI_BAT,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


# Check if already running
print("🔍 Checking if ComfyUI is already running...")
if is_comfyui_running():
    print("✅ ComfyUI already running!")
else:
    start_comfyui()
    print("⏳ Waiting for ComfyUI to start...")
    for i in range(60):
        time.sleep(2)
        if is_comfyui_running():
            print(f"✅ ComfyUI started! ({(i+1)*2}s)")
            break
        if i % 5 == 0:
            print(f"  Still waiting... ({(i+1)*2}s)")
    else:
        print("❌ ComfyUI failed to start after 120s. Check the bat file.")
        sys.exit(1)

print()
print("=" * 50)
print("✅ ComfyUI ready!")
print(f"   URL:      {COMFYUI_URL}")
print(f"   Browser:  http://127.0.0.1:8188")
print("=" * 50)
print()
print("Keep this terminal open to keep ComfyUI running.")
print("Press Ctrl+C to stop ComfyUI.")

# Keep running
try:
    while True:
        time.sleep(30)
        if not is_comfyui_running():
            print("⚠️  ComfyUI stopped! Restarting...")
            start_comfyui()
            time.sleep(10)
            if is_comfyui_running():
                print("✅ ComfyUI restarted!")
except KeyboardInterrupt:
    print("\n👋 ComfyUI monitor stopped.")