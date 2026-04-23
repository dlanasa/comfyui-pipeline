import requests
import time

# Submit generation job
response = requests.post('http://127.0.0.1:8000/generate', json={
    'workflow_path': 'workflow.json',
    'output_dir': r'D:\ComfyUI\_study\output',
    'server': 'http://127.0.0.1:8188',
    'variations': [
        {'name': 'test_drive',
         'prompt': 'full body portrait of a woman, red dress, standing pose, photorealistic, 8k, sharp focus, clothed'}
    ]
})

job_result = response.json()
job_id = job_result['job_id']
print(f"Job submitted: {job_id}")
print(f"Status: {job_result['status']}\n")

# Wait a moment for the job to start
time.sleep(1)

# Poll status until complete
while True:
    status_response = requests.get(f'http://127.0.0.1:8000/status/{job_id}')
    status = status_response.json()

    print(f"Status: {status['status']}")

    if status['status'] == 'complete':
        print("\n✅ Generation complete!")
        print(f"Results: {status['results']}")
        if status['errors']:
            print(f"Errors: {status['errors']}")
        print(f"\n🖼️  View gallery at:")
        print(f"http://127.0.0.1:8000/gallery?server=http://127.0.0.1:8188")
        break

    print("  Waiting 2 seconds...\n")
    time.sleep(2)