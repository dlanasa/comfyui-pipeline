# ComfyUI Pipeline

A production-grade character look development pipeline built on ComfyUI, exposing Stable Diffusion image generation via a FastAPI service with async job execution, Docker containerization, and cloud deployment.

## What It Does

Generates costume/look variations of a character from a reference pose using ControlNet (OpenPose). Accepts batch generation requests via HTTP API, tracks job status asynchronously, and serves results through a web gallery.

## Architecture

```
Internet User
    ↓
https://comfyui-pipeline-production.up.railway.app  (FastAPI on Railway)
    ↓ HTTP via ngrok tunnel
Your Local Machine  (ComfyUI + RTX A6000)
    ↓
Generated Images served back via ngrok
```

The FastAPI service runs in a Docker container on Railway. ComfyUI runs locally on a GPU machine. ngrok creates a secure tunnel between them. The ngrok URL is auto-detected at runtime via the ngrok local API — no manual URL updates needed.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/generate` | POST | Submit batch generation job |
| `/status/{job_id}` | GET | Poll job status |
| `/gallery` | GET | Browse generated images |
| `/proxy-download/{filename}` | GET | Download image via proxy |
| `/register-images` | POST | Register local images with gallery |
| `/refresh` | POST | Reload image store from local folder |

## Tech Stack

- **ComfyUI** — Stable Diffusion workflow engine
- **ControlNet (OpenPose)** — Pose-consistent character generation
- **FastAPI** — Async HTTP API with Pydantic validation
- **Docker** — Containerized deployment
- **Railway** — Cloud deployment platform
- **ngrok** — Local-to-cloud tunnel (URL auto-detected via ngrok API)
- **GitHub** — Auto-deploy on push to main

## Quick Start

### Prerequisites
- Python 3.11
- ComfyUI installed with RTX GPU
- ngrok account
- Railway account

### Local Development (no ngrok needed)

1. Clone the repo:
```bash
git clone https://github.com/dlanasa/comfyui-pipeline.git
cd comfyui-pipeline
```

2. Create virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3. Start services (2 terminals):
```bash
# Terminal 1 - ComfyUI
D:\ComfyUI\run_nvidia_gpu_study.bat

# Terminal 2 - FastAPI
uvicorn api:app --reload --port 8000
```

4. Test:
```bash
python test_local.py
```

5. View gallery:
```
http://127.0.0.1:8000/gallery?server=http://127.0.0.1:8188
```

### Railway Testing (ngrok required)

1. Start ComfyUI and ngrok:
```bash
# Terminal 1
D:\ComfyUI\run_nvidia_gpu_study.bat

# Terminal 2
D:\ngrok\ngrok.exe http 8188
```

2. Run test — ngrok URL is auto-detected, no manual update needed:
```bash
python test_railway.py
```

3. Gallery URL is printed automatically when generation completes.

## Environment Variables (Railway)

| Variable | Description |
|----------|-------------|
| `COMFYUI_SERVER` | Default ComfyUI server URL fallback |

## Project Structure

```
comfyui-pipeline/
├── api.py              # FastAPI service - routes, job tracking, gallery
├── comfyui_api.py      # ComfyUI orchestration - workflow, generation, polling
├── logger.py           # CSV audit logging
├── workflow.json       # ComfyUI API-format workflow (ControlNet OpenPose)
├── variations.json     # Batch generation prompts config
├── test_local.py       # Local testing script (localhost only, no ngrok)
├── test_railway.py     # Railway testing script (auto-detects ngrok URL)
├── Dockerfile          # Container definition
├── requirements.txt    # Python dependencies
└── .gitignore          # Excludes secrets and local paths
```

## License

MIT
