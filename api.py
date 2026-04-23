import sys
import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import uuid
from fastapi.responses import FileResponse, HTMLResponse
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Import your existing pipeline functions
sys.path.append(r"D:\ComfyUI\_study")
from comfyui_api import generate_variation
from logger import init_log, log_generation
from dotenv import load_dotenv

load_dotenv()

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

    import comfyui_api
    comfyui_api.SERVER = request.server or COMFYUI_SERVER

    os.makedirs(request.output_dir, exist_ok=True)
    init_log()

    for variation in request.variations:
        try:
            # Generate and get back the filename
            actual_filename = generate_variation(
                request.workflow_path,
                variation.name,
                variation.prompt,
                request.output_dir
            )

            print(f"  Returned filename: {actual_filename}")

            if actual_filename:
                file_path = os.path.join(request.output_dir, actual_filename)
                print(f"  Uploading to Drive: {file_path}")
                print(f"  Folder ID: {os.getenv('GOOGLE_DRIVE_FOLDER_ID')}")

                drive_link = upload_to_google_drive(
                    file_path,
                    os.getenv("GOOGLE_DRIVE_FOLDER_ID"),
                    actual_filename
                )

                print(f"  Drive link result: {drive_link}")

                jobs[job_id]["results"].append({
                    "variation": variation.name,
                    "status": "success",
                    "filename": actual_filename,
                    "drive_link": drive_link
                })
            else:
                print(f"  ERROR: No filename returned!")
                jobs[job_id]["results"].append({
                    "variation": variation.name,
                    "status": "error",
                    "filename": "unknown"
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


def get_drive_credentials():
    """Load OAuth credentials from env var or file"""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials as OAuthCredentials

    token_file = 'google_oauth_token.json'
    creds = None

    # Try to load existing token
    if os.path.exists(token_file):
        creds = OAuthCredentials.from_authorized_user_file(token_file, scopes=['https://www.googleapis.com/auth/drive'])

    # If no token, do OAuth flow
    if not creds or not creds.valid:
        from google_auth_oauthlib.flow import InstalledAppFlow

        # Try env var first, then file
        creds_json = os.getenv("GOOGLE_CREDENTIALS")
        if creds_json:
            flow = InstalledAppFlow.from_client_config(
                json.loads(creds_json),
                scopes=['https://www.googleapis.com/auth/drive']
            )
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'google_oauth_credentials.json',
                scopes=['https://www.googleapis.com/auth/drive']
            )

        creds = flow.run_local_server(port=0)

        # Save token for next time
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    return creds


def upload_to_google_drive(file_path, folder_id, filename):
    """Upload image to Google Drive folder and return shareable link"""
    try:
        credentials = get_drive_credentials()
        service = build('drive', 'v3', credentials=credentials)

        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }

        media = MediaFileUpload(file_path, mimetype='image/png')

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        # Make file publicly viewable
        service.permissions().create(
            fileId=file['id'],
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()

        return file['webViewLink']
    except Exception as e:
        print(f"Error uploading to Drive: {e}")
        return None


