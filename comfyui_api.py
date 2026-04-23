import json
import os
import shutil
import requests
import time
import random
from logger import init_log, log_generation
from tqdm import tqdm
import argparse

global SERVER

#ComfyUI server address
SERVER = "http://127.0.0.1:8188"
# this is tied to the bat file  that comfyUI is started with
#OUTPUT_DIR = r"D:\ComfyUI\_study\output"


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


def generate_variation(workflow_path, variation_name, prompt, save_dir):
    print(f"\nGenerating: {variation_name}")
    start_time = time.time()

    workflow = load_workflow(workflow_path)
    seed = random.randint(0, 999999999999999)
    workflow = set_prompt(workflow, prompt, seed)

    result = queue_prompt(workflow)
    prompt_id = result["prompt_id"]
    print(f"  Prompt ID: {prompt_id}")

    filename = wait_for_completion(prompt_id)
    print(f"  Generated: {filename}")

    duration = time.time() - start_time
    log_generation(variation_name, prompt, seed, filename, duration)
    print(f"  Done in {duration:.1f}s")

# --- Main ---
if __name__ == "__main__":


    #WORKFLOW_PATH = r"D:\ComfyUI\_study\workflows\tutorial1_controlnet_openpose_workflow.json"

    parser = argparse.ArgumentParser(description="ComfyUI batch generator")
    parser.add_argument("--workflow", required=True, help="Path to API workflow JSON")
    parser.add_argument("--variations", required=True, help="Path to variations JSON file")
    parser.add_argument("--output", default=r'D:\ComfyUI\_study\output', required=True, help="Output directory for named images")
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
            generate_variation(args.workflow, variation_name, prompt, save_dir)
        except Exception as e:
            print(f"  ERROR on {variation_name}: {e}")
            log_generation(variation_name, prompt, 0, "FAILED", 0, status="error")
            continue

    print("\nAll variations complete!")
    print(f"Images saved to: {save_dir}")