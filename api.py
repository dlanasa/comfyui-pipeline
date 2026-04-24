import sys
import os
import uuid
import httpx
import comfyui_api
import urllib.parse

from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from comfyui_api import generate_variation
from logger import init_log, log_generation

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
@asynccontextmanager
async def lifespan(app: FastAPI):
    output_dir = r"D:\ComfyUI\_study\output"
    if os.path.exists(output_dir):
        files = sorted([f for f in os.listdir(output_dir) if f.endswith('.png')], reverse=True)
        image_store.extend([{"filename": f} for f in files])
        print(f"  Auto-loaded {len(files)} images from {output_dir}")
    else:
        print(f"  Output dir not found: {output_dir}")
    yield

app = FastAPI(title="ComfyUI Pipeline API", lifespan=lifespan)

jobs = {}

COMFYUI_SERVER = os.getenv("COMFYUI_SERVER", "http://127.0.0.1:8188")

# Persistent image store (survives job restarts but not uvicorn restarts)
image_store = []

class VariationItem(BaseModel):
    name: str
    prompt: str

class GenerationRequest(BaseModel):
    workflow_path: str
    variations: List[VariationItem]
    output_dir: Optional[str] = ""
    server: Optional[str] = "http://127.0.0.1:8188"

def run_batch(job_id: str, request: GenerationRequest):
    """Run batch generation in the background"""
    jobs[job_id]["status"] = "running"
    comfyui_api.SERVER = request.server or COMFYUI_SERVER

    # Only create output dir if one was specified
    if request.output_dir:
        os.makedirs(request.output_dir, exist_ok=True)

    init_log()

    for variation in request.variations:
        try:
            result = generate_variation(
                request.workflow_path,
                variation.name,
                variation.prompt,
                request.output_dir,
                request.server or COMFYUI_SERVER
            )

            if result and result.get("filename"):
                jobs[job_id]["results"].append({
                    "variation": variation.name,
                    "status": "success",
                    "filename": result["filename"],
                    "image_url": result.get("image_url")
                })
            else:
                jobs[job_id]["results"].append({
                    "variation": variation.name,
                    "status": "error"
                })

        except Exception as e:
            jobs[job_id]["errors"].append({
                "variation": variation.name,
                "error": str(e)
            })

    jobs[job_id]["status"] = "complete"

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "comfyui_server": COMFYUI_SERVER
    }

@app.post("/generate")
async def generate(request: GenerationRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "results": [], "errors": []}
    background_tasks.add_task(run_batch, job_id, request)
    return {"job_id": job_id, "status": "queued"}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        return {"error": "job not found"}
    return jobs[job_id]

@app.get("/download/{variation_name}")
async def download(variation_name: str, output_dir: str):
    # Decode the output_dir from URL encoding
    output_dir = urllib.parse.unquote(output_dir)

    filepath = os.path.join(output_dir, f"{variation_name}.png")

    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}

    return FileResponse(
        path=filepath,
        media_type="image/png",
        filename=f"{variation_name}.png",
        headers={"Content-Disposition": "inline"}
    )


@app.get("/view/{filename}")
async def view(filename: str, output_dir: str = r"D:\ComfyUI\_study\output"):
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}

    return FileResponse(
        path=filepath,
        media_type="image/png",
        headers={"Content-Disposition": "inline"}
    )


@app.get("/proxy-download/{filename}")
async def proxy_download(filename: str, server: str = "http://127.0.0.1:8188"):
    url = f"{server}/view?filename={filename}&subfolder=&type=output"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers={"ngrok-skip-browser-warning": "true"})

    return StreamingResponse(
        iter([response.content]),
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/refresh")
async def refresh(output_dir: str = r"D:\ComfyUI\_study\output", server: str = "http://127.0.0.1:8188"):
    """Scan output folder and register all images"""
    global image_store

    if not os.path.exists(output_dir):
        return {"error": "Output directory not found"}

    files = sorted([f for f in os.listdir(output_dir) if f.endswith('.png')], reverse=True)
    image_store = [{"filename": f, "server": server} for f in files]

    return {"message": f"Registered {len(files)} images", "count": len(files)}


# Persistent image store - add this near the top of api.py with other globals
image_store = []

@app.post("/register-images")
async def register_images(filenames: List[str], server: str = "http://127.0.0.1:8188"):
    global image_store
    image_store = [{"filename": f, "server": server} for f in filenames]
    return {"message": f"Registered {len(filenames)} images", "count": len(filenames)}

@app.post("/refresh")
async def refresh(output_dir: str = r"D:\ComfyUI\_study\output", server: str = "http://127.0.0.1:8188"):
    """Scan output folder and register all images"""
    global image_store

    if not os.path.exists(output_dir):
        return {"error": "Output directory not found"}

    files = sorted([f for f in os.listdir(output_dir) if f.endswith('.png')], reverse=True)
    image_store = [{"filename": f, "server": server} for f in files]

    return {"message": f"Registered {len(files)} images", "count": len(files)}


@app.get("/gallery")
async def gallery(server: str = "http://127.0.0.1:8188"):
    # Get file list from ComfyUI via HTTP (works locally AND via ngrok on Railway)
    files = []
    try:
        async with httpx.AsyncClient() as client:
            history_response = await client.get(f"{server}/history")
            history = history_response.json()

        # Extract all generated filenames from history
        for prompt_id, entry in history.items():
            outputs = entry.get("outputs", {})
            if "18" in outputs and "images" in outputs["18"]:
                for img in outputs["18"]["images"]:
                    if img["filename"] not in files:
                        files.append(img["filename"])

    except Exception as e:
        print(f"  Could not get history from ComfyUI: {e}")

    # Fall back to image_store if history is empty
    # Add image_store files that aren't already in history
    history_files = set(files)
    for img in image_store:
        if img["filename"] not in history_files:
            files.append(img["filename"])

    files = sorted(files, reverse=True)

    image_tags = ""
    for filename in files:
        view_url = f"/proxy-download/{filename}?server={urllib.parse.quote(server)}"
        download_url = f"/proxy-download/{filename}?server={urllib.parse.quote(server)}"
        image_tags += f"""
            <div class="card">
                <img src="{view_url}" alt="{filename}"/>
                <div class="card-info">
                    <span class="card-name">{filename}</span>
                    <a href="{download_url}" class="download-btn">Download</a>
                </div>
            </div>
            """

    html = f"""
    <html>
    <head>
        <title>ComfyUI Pipeline Gallery</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ background: #0f0f0f; color: white; font-family: Arial; padding: 40px; }}
            h1 {{ font-size: 28px; margin-bottom: 20px; }}
            .subtitle {{ color: #888; font-size: 14px; margin-bottom: 40px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 24px; }}
            .card {{ background: #1a1a1a; border-radius: 12px; overflow: hidden; }}
            .card img {{ width: 100%; height: 340px; object-fit: cover; }}
            .card-info {{ padding: 16px; display: flex; justify-content: space-between; align-items: center; }}
            .card-name {{ font-size: 14px; color: #fff; }}
            .download-btn {{ background: #1a4a8a; color: white; padding: 8px 12px; text-decoration: none; border-radius: 6px; }}
            .download-btn:hover {{ background: #2563b0; }}
        </style>
    </head>
    <body>
        <h1>ComfyUI Pipeline Gallery</h1>
        <p class="subtitle">{len(files)} images found</p>
        <div class="grid">
            {image_tags if image_tags else "<p>No images found. Run /refresh to load existing images.</p>"}
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
