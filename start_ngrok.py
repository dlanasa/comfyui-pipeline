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

# Update Railway
print("🔄 Updating Railway COMFYUI_SERVER...")
if update_railway_ngrok(NGROK_URL):
    print("✅ Railway updated!")
else:
    print("⚠️  Railway not updated — continuing anyway")

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
    while True:
        time.sleep(60)
        url = get_ngrok_url()
        if not url:
            print("⚠️  ngrok stopped! Restarting...")
            NGROK_URL = start_ngrok()
            if NGROK_URL:
                update_railway_ngrok(NGROK_URL)
                print(f"✅ ngrok restarted: {NGROK_URL}")
except KeyboardInterrupt:
    print("\n👋 ngrok stopped.")