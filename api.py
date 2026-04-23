import sys
import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import uuid
import httpx
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

sys.path.append(r"D:\ComfyUI\_study")
from comfyui_api import generate_variation
from logger import init_log, log_generation

import comfyui_api
import urllib.parse

app = FastAPI(title="ComfyUI Pipeline API")

jobs = {}

COMFYUI_SERVER = os.getenv("COMFYUI_SERVER", "http://127.0.0.1:8188")

class VariationItem(BaseModel):
    name: str
    prompt: str

class GenerationRequest(BaseModel):
    workflow_path: str
    variations: List[VariationItem]
    output_dir: str
    server: Optional[str] = "http://127.0.0.1:8188"

def run_batch(job_id: str, request: GenerationRequest):
    """Run batch generation in the background"""
    jobs[job_id]["status"] = "running"
    comfyui_api.SERVER = request.server or COMFYUI_SERVER

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
    return {"status": "ok"}

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
        response = await client.get(url)

    return StreamingResponse(
        iter([response.content]),
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/gallery")
async def gallery(server: str = "http://127.0.0.1:8188", output_dir: str = r"D:\ComfyUI\_study\output"):
    import urllib.parse

    if not os.path.exists(output_dir):
        # On Railway - list files not possible, show message
        return HTMLResponse("<h2>Running on Railway - use local gallery instead</h2>")

    files = [f for f in os.listdir(output_dir) if f.endswith('.png')]
    files = sorted(files, reverse=True)

    image_tags = ""
    for filename in files:
        # Use server URL for images (works via ngrok on Railway)
        view_url = f"{server}/view?filename={filename}&subfolder=&type=output"
        download_url = f"/proxy-download/{filename}?server={server}"
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
            {image_tags if image_tags else "<p>No images in folder.</p>"}
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)