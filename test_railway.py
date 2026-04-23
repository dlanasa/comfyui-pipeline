import requests
import time
import os

RAILWAY_URL = 'https://comfyui-pipeline-production.up.railway.app'
NGROK_URL = 'https://20d6-172-251-166-164.ngrok-free.app'
OUTPUT_DIR = r'D:\ComfyUI\_study\output'

# Submit generation job to RAILWAY (public URL)
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

        # Push local file list to Railway so gallery shows all images
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