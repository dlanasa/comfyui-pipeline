import requests
import time

RAILWAY_URL = 'https://comfyui-pipeline-production.up.railway.app'


def get_comfyui_server():
    """Get current ComfyUI server URL from Railway health check"""
    try:
        response = requests.get(f'{RAILWAY_URL}/health')
        return response.json().get('comfyui_server')
    except:
        return None


# Get current ngrok URL from Railway
print("🔍 Getting current ComfyUI server from Railway...")
COMFYUI_SERVER = get_comfyui_server()

if not COMFYUI_SERVER:
    print("❌ Could not get ComfyUI server URL. GPU owner may not be online.")
    exit(1)

print(f"✅ ComfyUI server: {COMFYUI_SERVER}\n")

# Submit generation job
response = requests.post(f'{RAILWAY_URL}/generate', json={
    'workflow_path': 'workflow.json',
    'output_dir': '',
    'server': COMFYUI_SERVER,
    'variations': [
        {'name': 'my_generation',
         'prompt': 'full body portrait of a woman, red dress, standing pose, photorealistic, 8k, sharp focus, clothed'}
    ]
})

job_result = response.json()
job_id = job_result['job_id']
print(f"Job submitted: {job_id}")
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
        print(f"\n🖼️  View gallery at:")
        print(f"{RAILWAY_URL}/gallery?server={COMFYUI_SERVER}")
        break

    print("  Waiting 2 seconds...\n")
    time.sleep(2)