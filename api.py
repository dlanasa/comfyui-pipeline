import sys
import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import uuid
from fastapi.responses import FileResponse, HTMLResponse

# Import your existing pipeline functions
sys.path.append(r"D:\ComfyUI\_study")
from comfyui_api import generate_variation
from logger import init_log, log_generation

app = FastAPI(title="ComfyUI Pipeline API")

# In-memory job tracking
jobs = {}

COMFYUI_SERVER = os.getenv("COMFYUI_SERVER", "http://127.0.0.1:8188")

# Request schema
class VariationItem(BaseModel):
    name: str
    prompt: str

class GenerationRequest(BaseModel):
    workflow_path: str
    variations: List[VariationItem]
    output_dir: str
    server: Optional[str] = "http://127.0.0.1:8188"

# Background task
def run_batch(job_id: str, request: GenerationRequest):
    """Run batch generation in the background"""
    jobs[job_id]["status"] = "running"

    # Override the server in comfyui_api
    import comfyui_api
    comfyui_api.SERVER = request.server or COMFYUI_SERVER

    # Create output folder
    os.makedirs(request.output_dir, exist_ok=True)
    init_log()

    for variation in request.variations:
        try:
            generate_variation(
                request.workflow_path,
                variation.name,
                variation.prompt,
                request.output_dir
            )
            jobs[job_id]["results"].append({
                "variation": variation.name,
                "status": "success"
            })
        except Exception as e:
            jobs[job_id]["errors"].append({
                "variation": variation.name,
                "error": str(e)
            })
            log_generation(variation.name, variation.prompt, 0, "FAILED", 0, status="error")

    jobs[job_id]["status"] = "complete"

# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}

# Submit a generation job
@app.post("/generate")
async def generate(request: GenerationRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "results": [], "errors": []}
    background_tasks.add_task(run_batch, job_id, request)
    return {"job_id": job_id, "status": "queued"}

# Check job status
@app.get("/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        return {"error": "job not found"}
    return jobs[job_id]

@app.get("/download/{variation_name}")
async def download(variation_name: str, output_dir: str):
    filepath = os.path.join(output_dir, f"{variation_name}.png")
    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}
    return FileResponse(
        path=filepath,
        media_type="image/png",
        filename=f"{variation_name}.png",
        headers={"Content-Disposition": "inline"}
    )


@app.get("/gallery")
async def gallery(output_dir: str):
    if not os.path.exists(output_dir):
        return HTMLResponse("<h2>Output directory not found</h2>")

    files = [f for f in os.listdir(output_dir) if f.endswith(".png")]

    if not files:
        return HTMLResponse("<h2>No images found</h2>")

    # Build HTML gallery
    image_tags = ""
    for filename in sorted(files):
        name = filename.replace(".png", "")
        download_url = f"/download/{name}?output_dir={output_dir}"
        image_tags += f"""
            <div class="card">
                <img src="{download_url}" alt="{name}"/>
                <div class="card-info">
                    <span class="card-name">{name}</span>
                    <a href="{download_url}" download class="download-btn">Download</a>
                </div>
            </div>
            """

    html = f"""
        <html>
        <head>
            <title>ComfyUI Pipeline Gallery</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ 
                    background: #0f0f0f; 
                    color: white; 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    padding: 40px;
                }}
                h1 {{ 
                    font-size: 28px; 
                    font-weight: 600;
                    margin-bottom: 8px;
                    color: #ffffff;
                }}
                .subtitle {{
                    color: #888;
                    font-size: 14px;
                    margin-bottom: 40px;
                }}
                .grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                    gap: 24px;
                }}
                .card {{
                    background: #1a1a1a;
                    border-radius: 12px;
                    overflow: hidden;
                    transition: transform 0.2s, box-shadow 0.2s;
                }}
                .card:hover {{
                    transform: translateY(-4px);
                    box-shadow: 0 12px 40px rgba(0,0,0,0.4);
                }}
                .card img {{
                    width: 100%;
                    height: 340px;
                    object-fit: cover;
                    display: block;
                }}
                .card-info {{
                    padding: 16px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .card-name {{
                    font-size: 15px;
                    font-weight: 600;
                    text-transform: capitalize;
                    color: #ffffff;
                }}
                .download-btn {{
                    background: #1a4a8a;
                    color: white;
                    text-decoration: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: 500;
                    transition: background 0.2s;
                }}
                .download-btn:hover {{
                    background: #2563b0;
                }}
                .empty {{
                    color: #555;
                    font-size: 18px;
                    text-align: center;
                    margin-top: 100px;
                }}
            </style>
        </head>
        <body>
            <h1>ComfyUI Pipeline Gallery</h1>
            <p class="subtitle">{len(files)} variation{"s" if len(files) != 1 else ""} generated</p>
            <div class="grid">
                {image_tags}
            </div>
        </body>
        </html>
        """
    return HTMLResponse(content=html)