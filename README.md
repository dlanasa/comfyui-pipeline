# ComfyUI Pipeline

A production-grade character look development pipeline built on ComfyUI, exposing Stable Diffusion image generation via a FastAPI service with async job execution, Docker containerization, and cloud deployment.

## What It Does

Generates costume/look variations of a character from a reference pose using ControlNet (OpenPose). Accepts batch generation requests via HTTP API, tracks job status asynchronously, and serves results through a web gallery.

## Architecture

```
Remote User / Internet
    ↓ HTTPS
Railway Cloud (FastAPI Service — runs 24/7)
    ↓ HTTPS via ngrok tunnel
GPU Machine — local computer running ComfyUI + ngrok
    ↓ GPU inference (RTX A6000)
Generated images served back via ngrok → Railway → User
```

The FastAPI service runs in a Docker container on Railway. ComfyUI runs locally on a GPU machine. ngrok creates a secure tunnel between them. `start_ngrok.py` automatically starts ngrok and updates Railway with the current URL — no manual configuration needed.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check + current ComfyUI server URL |
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
- **ngrok** — Local-to-cloud tunnel (auto-started and auto-updated)
- **GitHub** — Auto-deploy on push to main

## For GPU Owner — Local Development

```bash
# Terminal 1 - ComfyUI
python start_comfyui.py

# Terminal 2 - local FastAPI
python start_uvicorn.py

# Terminal 3 - test
python test_local.py
```

Gallery: `http://127.0.0.1:8000/gallery?server=http://127.0.0.1:8188`

Force restart if needed: `python start_uvicorn.py --restart`

## For GPU Owner — Railway Testing

```bash
# Terminal 1 - ComfyUI
python start_comfyui.py

# Terminal 2 - ngrok (auto-updates Railway)
python start_ngrok.py

# Terminal 3 - test
python test_railway.py
```

Force restart ngrok if needed: `python start_ngrok.py --restart`

## For Remote Users

No setup needed. GPU owner must have ComfyUI and ngrok running.

```bash
python test_remote.py
```

Or use the interactive API docs:
```
https://comfyui-pipeline-production.up.railway.app/docs
```

## Environment Variables

### Railway Dashboard
| Variable | Description |
|----------|-------------|
| `COMFYUI_SERVER` | Auto-updated by start_ngrok.py — never set manually |

### Local .env file (never commit to GitHub)
| Variable | Description |
|----------|-------------|
| `RAILWAY_TOKEN` | Railway API token |
| `RAILWAY_PROJECT_ID` | Railway project ID |
| `RAILWAY_ENVIRONMENT_ID` | Railway environment ID |
| `RAILWAY_SERVICE_ID` | Railway service ID |

## Project Structure

```
comfyui-pipeline/
├── api.py               # FastAPI service
├── comfyui_api.py       # ComfyUI orchestration
├── logger.py            # CSV audit logging
├── workflow.json        # ComfyUI API-format workflow
├── variations.json      # Batch generation prompts
├── start_comfyui.py     # Starts ComfyUI (GPU machine only)
├── start_ngrok.py       # Starts ngrok + auto-updates Railway
├── start_uvicorn.py     # Starts local FastAPI (dev only)
├── test_local.py        # Local development testing
├── test_railway.py      # Railway testing (GPU machine)
├── test_remote.py       # Remote user testing script
├── Dockerfile           # Container definition
├── requirements.txt     # Python dependencies
└── .gitignore           # Excludes secrets and local paths
```

## License

MIT

## Building test_railway.exe

To build a standalone exe that anyone on the GPU machine can double-click:

1. Copy `build_test_railway_exe.bat` to `D:\ComfyUI\_study\`
2. Double-click it in Windows Explorer
3. Output: `dist\test_railway.exe`

The exe:
- Auto-detects ngrok URL via local ngrok API
- Auto-creates `D:\ComfyUI\_study\output\` if it doesn't exist
- Pauses at the end so you can read the output
- Requires ComfyUI and ngrok to be running first
