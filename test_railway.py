import requests
import time

# Submit generation job to RAILWAY (public URL)
response = requests.post('https://comfyui-pipeline-production.up.railway.app/generate', json={
    'workflow_path': 'workflow.json',
    'output_dir': r'D:\ComfyUI\_study\output',
    'server': 'https://20d6-172-251-166-164.ngrok-free.app',
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
    status_response = requests.get(f'https://comfyui-pipeline-production.up.railway.app/status/{job_id}')
    status = status_response.json()

    print(f"Status: {status['status']}")

    if status['status'] == 'complete':
        print("\n✅ Generation complete!")
        print(f"Results: {status['results']}")
        if status['errors']:
            print(f"Errors: {status['errors']}")
        print(f"\n🖼️  View gallery at:")
        print(
            f"https://comfyui-pipeline-production.up.railway.app/gallery?server=https://20d6-172-251-166-164.ngrok-free.app")
        break

    print("  Waiting 2 seconds...\n")
    time.sleep(2)