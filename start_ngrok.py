import subprocess
import requests
import time
import os
import argparse
from dotenv import load_dotenv

load_dotenv()

RAILWAY_URL = 'https://comfyui-pipeline-production.up.railway.app'
NGROK_PATH = r'D:\ngrok\ngrok.exe'

parser = argparse.ArgumentParser()
parser.add_argument('--restart', action='store_true', help='Kill existing ngrok and restart')
args = parser.parse_args()


def register_images_with_railway(ngrok_url):
    """Push local image list to Railway after ngrok starts"""
    output_dir = r'D:\ComfyUI\_study\output'

    if not os.path.exists(output_dir):
        print("  Output directory not found — skipping image registration")
        return

    local_files = sorted([f for f in os.listdir(output_dir) if f.endswith('.png')], reverse=True)

    try:
        response = requests.post(
            f'{RAILWAY_URL}/register-images',
            params={'server': ngrok_url},
            json=local_files
        )
        result = response.json()
        print(f"✅ Registered {result.get('count', 0)} images with Railway gallery")
    except Exception as e:
        print(f"⚠️  Could not register images: {e}")


def wait_for_railway_ready(timeout=300):
    """Wait for Railway to finish redeploying"""
    print("⏳ Waiting for Railway to come back online...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f'{RAILWAY_URL}/health', timeout=5)
            if response.status_code == 200:
                print(f"✅ Railway is back online! ({int(time.time()-start)}s)")
                return True
        except:
            pass
        time.sleep(5)
        print(f"  Still waiting... ({int(time.time()-start)}s)")
    print("⚠️  Railway did not come back online within timeout")
    return False


def kill_ngrok():
    """Kill any running ngrok processes"""
    try:
        subprocess.run(['taskkill', '/f', '/im', 'ngrok.exe'],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        print("  Killed existing ngrok process")
    except:
        pass


def start_ngrok():
    """Start ngrok in background"""
    print("🚀 Starting ngrok...")
    subprocess.Popen([NGROK_PATH, 'http', '8188'])
    for i in range(10):
        time.sleep(1)
        url = get_ngrok_url()
        if url:
            return url
        print(f"  Waiting for ngrok to start... ({i+1}/10)")
    return None


def get_ngrok_url():
    """Auto-detect current ngrok tunnel URL"""
    try:
        response = requests.get('http://127.0.0.1:4040/api/tunnels')
        tunnels = response.json()['tunnels']
        for tunnel in tunnels:
            if tunnel['proto'] == 'https':
                return tunnel['public_url']
    except:
        return None
    return None


def update_railway_ngrok(ngrok_url):
    """Update COMFYUI_SERVER on Railway with current ngrok URL"""
    token = os.getenv("RAILWAY_TOKEN")
    project_id = os.getenv("RAILWAY_PROJECT_ID")
    environment_id = os.getenv("RAILWAY_ENVIRONMENT_ID")
    service_id = os.getenv("RAILWAY_SERVICE_ID")

    if not all([token, project_id, environment_id, service_id]):
        print("⚠️  Railway credentials not found in .env — skipping Railway update")
        return False

    query = """
    mutation variableUpsert($input: VariableUpsertInput!) {
        variableUpsert(input: $input)
    }
    """
    variables = {
        "input": {
            "projectId": project_id,
            "environmentId": environment_id,
            "serviceId": service_id,
            "name": "COMFYUI_SERVER",
            "value": ngrok_url
        }
    }
    response = requests.post(
        "https://backboard.railway.app/graphql/v2",
        json={"query": query, "variables": variables},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    result = response.json()
    if "errors" in result:
        print(f"⚠️  Railway update failed: {result['errors']}")
        return False
    return True


# Handle restart flag
if args.restart:
    print("🔄 Restart requested — killing existing ngrok...")
    kill_ngrok()

# Check if ngrok is already running
print("🔍 Checking if ngrok is already running...")
NGROK_URL = get_ngrok_url()

if NGROK_URL:
    print(f"✅ ngrok already running: {NGROK_URL}")
else:
    NGROK_URL = start_ngrok()
    if not NGROK_URL:
        print("❌ Failed to start ngrok. Check D:\\ngrok\\ngrok.exe exists.")
        exit(1)
    print(f"✅ ngrok started: {NGROK_URL}")

# Update Railway and wait for redeploy
print("🔄 Updating Railway COMFYUI_SERVER...")
if update_railway_ngrok(NGROK_URL):
    print("✅ Railway updated!")
    wait_for_railway_ready()
    print("🔄 Registering images with Railway gallery...")
    register_images_with_railway(NGROK_URL)
else:
    print("⚠️  Railway not updated — continuing anyway")
    register_images_with_railway(NGROK_URL)

print()
print("=" * 50)
print("✅ ngrok ready!")
print(f"   ngrok URL:  {NGROK_URL}")
print(f"   Dashboard:  http://127.0.0.1:4040")
print(f"   Gallery:    {RAILWAY_URL}/gallery?server={NGROK_URL}")
print(f"   API Docs:   {RAILWAY_URL}/docs")
print("=" * 50)
print()
print("Keep this terminal open to keep ngrok running.")
print("Press Ctrl+C to stop.  |  Restart: python start_ngrok.py --restart")

try:
    counter = 0
    while True:
        time.sleep(60)
        counter += 1

        # Re-register ALL local images every 10 minutes
        if counter % 10 == 0:
            print("🔄 Re-registering images with Railway...")
            register_images_with_railway(NGROK_URL)

        # Check ngrok is still running
        url = get_ngrok_url()
        if not url:
            print("⚠️  ngrok stopped! Restarting...")
            NGROK_URL = start_ngrok()
            if NGROK_URL:
                update_railway_ngrok(NGROK_URL)
                wait_for_railway_ready()
                register_images_with_railway(NGROK_URL)
                print(f"✅ ngrok restarted: {NGROK_URL}")
except KeyboardInterrupt:
    print("\n👋 ngrok stopped.")