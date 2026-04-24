import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

RAILWAY_URL = 'https://comfyui-pipeline-production.up.railway.app'
OUTPUT_DIR = r'D:\ComfyUI\_study\output'

def check_uvicorn():
    """Check if uvicorn is running before proceeding"""
    try:
        response = requests.get('http://127.0.0.1:8000/health', timeout=3)
        if response.status_code == 200:
            print("✅ uvicorn is running")
            return True
    except:
        pass
    print("❌ uvicorn is not running!")
    print("   Start it with: python start_uvicorn.py")
    input("Press Enter to exit...")
    exit(1)

def get_ngrok_url():
    """Auto-detect current ngrok tunnel URL via local ngrok API"""
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


# Auto-create output directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"📁 Created output directory: {OUTPUT_DIR}")
else:
    print(f"📁 Output directory: {OUTPUT_DIR}")

check_uvicorn()

# Auto-detect ngrok URL
NGROK_URL = get_ngrok_url()
if not NGROK_URL:
    print("❌ ngrok not running! Start it with: python start_ngrok.py")
    input("Press Enter to exit...")
    exit(1)

print(f"✅ ngrok URL detected: {NGROK_URL}")

# Update Railway
print("🔄 Updating Railway COMFYUI_SERVER...")
if update_railway_ngrok(NGROK_URL):
    print("✅ Railway updated!")
else:
    print("⚠️  Railway not updated — continuing anyway")
print()

# Submit generation job
response = requests.post(f'{RAILWAY_URL}/generate', json={
    'workflow_path': 'workflow.json',
    'output_dir': OUTPUT_DIR,
    'server': NGROK_URL,
    'variations': [
        {'name': 'test_railway_drive',
         'prompt': 'full body portrait of a woman, blue dress, standing pose, photorealistic, 8k, sharp focus, clothed'}
    ]
})

job_result = response.json()
job_id = job_result['job_id']
print(f"Job submitted to Railway: {job_id}")
print(f"Status: {job_result['status']}\n")

# Poll status until complete
while True:
    status_response = requests.get(f'{RAILWAY_URL}/status/{job_id}')
    status = status_response.json()

    print(f"Status: {status['status']}")

    if status['status'] == 'complete':
        print("\n✅ Generation complete!")
        print(f"Results: {status['results']}")
        if status['errors']:
            print(f"Errors: {status['errors']}")

        # Register local images with Railway gallery
        print("\n🔄 Registering images with Railway gallery...")
        local_files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith('.png')], reverse=True)
        refresh_response = requests.post(
            f'{RAILWAY_URL}/register-images',
            params={'server': NGROK_URL},
            json=local_files
        )
        print(f"Registered: {refresh_response.json()}")

        print(f"\n🖼️  View gallery at:")
        print(f"{RAILWAY_URL}/gallery?server={NGROK_URL}")
        break

    print("  Waiting 2 seconds...\n")
    time.sleep(2)

input("\nPress Enter to exit...")
