import json
import os
import shutil
import requests
import time
import random
from logger import init_log, log_generation
from tqdm import tqdm
import argparse
from dotenv import load_dotenv

load_dotenv()

global SERVER

# ComfyUI server address
SERVER = "http://127.0.0.1:8188"


def load_variations(filepath):
    """Load variations from a JSON config file"""
    with open(filepath, "r") as f:
        data = json.load(f)
    return [(v["name"], v["prompt"]) for v in data["variations"]]


def queue_prompt(workflow):
    payload = {"prompt": workflow}
    response = requests.post(f"{SERVER}/prompt", json=payload)
    return response.json()


def load_workflow(filepath):
    with open(filepath, "r") as f:
        return json.load(f)


def wait_for_completion(prompt_id):
    print("  Waiting for generation...")
    attempts = 0
    while True:
        response = requests.get(f"{SERVER}/history/{prompt_id}")
        history = response.json()
        attempts += 1

        if attempts % 5 == 0:
            print(f"  Still waiting... {attempts} seconds")

        if prompt_id in history:
            entry = history[prompt_id]
            status = entry.get("status", {})
            completed = status.get("completed", False)

            if not completed:
                time.sleep(1)
                continue

            print(f"  Found in history! Status: {status}")
            outputs = entry["outputs"]
            print(f"  Output nodes: {list(outputs.keys())}")

            # Look for SaveImage node 18
            if "18" in outputs and "images" in outputs["18"]:
                return outputs["18"]["images"][0]["filename"]

            print("  Node 18 not found in outputs!")
            return None

        time.sleep(1)


def set_prompt(workflow, positive_text, seed):
    workflow["2"]["inputs"]["text"] = positive_text
    workflow["16"]["inputs"]["seed"] = seed
    return workflow


def get_drive_credentials():
    """Load OAuth token from env var or file"""
    from google.oauth2.credentials import Credentials as OAuthCredentials

    # Try env var first (Railway)
    token_json = os.getenv("GOOGLE_OAUTH_TOKEN")
    if token_json:
        print(f"    Loading token from env var")
        return OAuthCredentials.from_authorized_user_info(
            json.loads(token_json),
            scopes=['https://www.googleapis.com/auth/drive']
        )

    # Try local file (development)
    if os.path.exists('google_oauth_token.json'):
        print(f"    Loading token from file")
        return OAuthCredentials.from_authorized_user_file(
            'google_oauth_token.json',
            scopes=['https://www.googleapis.com/auth/drive']
        )

    raise ValueError("No OAuth token found!")


def upload_to_google_drive(file_path, filename):
    """Upload image to Google Drive folder and return shareable link"""
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        print(f"    Getting Drive credentials...")
        credentials = get_drive_credentials()
        print(f"    Building Drive service...")
        service = build('drive', 'v3', credentials=credentials)

        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        if not folder_id:
            print(f"    ERROR: GOOGLE_DRIVE_FOLDER_ID not set!")
            return None

        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }

        print(f"    Uploading {filename}...")
        media = MediaFileUpload(file_path, mimetype='image/png')

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        print(f"    File uploaded: {file['id']}")

        # Make file publicly viewable
        service.permissions().create(
            fileId=file['id'],
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()

        print(f"    Success! Drive link: {file['webViewLink']}")
        return file['webViewLink']
    except Exception as e:
        print(f"    ERROR uploading to Drive: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_variation(workflow_path, variation_name, prompt, save_dir):
    print(f"\nGenerating: {variation_name}")
    start_time = time.time()

    # Load fresh copy of workflow each time
    workflow = load_workflow(workflow_path)

    # Update the prompt and randomize seed
    seed = random.randint(0, 999999999999999)
    workflow = set_prompt(workflow, prompt, seed)

    # Queue it
    result = queue_prompt(workflow)
    prompt_id = result["prompt_id"]
    print(f"  Prompt ID: {prompt_id}")

    # Wait for completion and get filename
    filename = wait_for_completion(prompt_id)
    print(f"  Generated: {filename}")

    duration = time.time() - start_time
    log_generation(variation_name, prompt, seed, filename, duration)
    print(f"  Done in {duration:.1f}s")

    # Upload to Google Drive (runs locally, has file access)
    file_path = os.path.join(save_dir, filename)
    print(f"  Uploading to Google Drive...")
    drive_link = upload_to_google_drive(file_path, filename)

    return {"filename": filename, "drive_link": drive_link}


# --- Main ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ComfyUI batch generator")
    parser.add_argument("--workflow", required=True, help="Path to API workflow JSON")
    parser.add_argument("--variations", required=True, help="Path to variations JSON file")
    parser.add_argument("--output", default=r'D:\ComfyUI\_study\output', required=True,
                        help="Output directory for named images")
    parser.add_argument("--server", default="http://127.0.0.1:8188", help="ComfyUI server URL")
    args = parser.parse_args()

    # Override server if provided
    SERVER = args.server

    # Create output folder if it doesn't exist
    save_dir = args.output
    os.makedirs(save_dir, exist_ok=True)

    init_log()

    variations = load_variations(args.variations)

    print("Starting batch generation...")
    for variation_name, prompt in tqdm(variations, desc="Generating variations"):
        try:
            result = generate_variation(args.workflow, variation_name, prompt, save_dir)
            print(f"  Result: {result}")
        except Exception as e:
            print(f"  ERROR on {variation_name}: {e}")
            log_generation(variation_name, prompt, 0, "FAILED", 0, status="error")
            continue

    print("\nAll variations complete!")
    print(f"Images saved to: {save_dir}")