# ComfyUI Pipeline

A production-grade character look development pipeline built on ComfyUI, exposing Stable Diffusion image generation via a FastAPI service with async job execution, Docker containerization, and cloud deployment.

## What It Does

Generates costume/look variations of a character from a reference pose using ControlNet (OpenPose). Accepts batch generation requests via HTTP API, tracks job status asynchronously, and serves results through a web gallery accessible locally and remotely.

## Architecture

```
Remote User / Internet
    ↓ HTTPS
Railway Cloud (FastAPI Service — runs 24/7)
    ↓ HTTPS via ngrok tunnel
GPU Machine — local computer running ComfyUI + ngrok
    ↓ GPU inference (RTX A6000)
Generated images saved locally
    ↓ Served back via ngrok → Railway → User
```

**Key point:** ComfyUI and ngrok MUST run on the GPU machine. Railway only runs the FastAPI API layer. Remote users never connect directly to the GPU machine — all traffic goes through Railway.

## How image_store Works

Railway keeps an in-memory list of all generated images (`image_store`). This is how the gallery knows what to show:

```
On Railway startup (lifespan):
    → Loads recent images from ComfyUI history via ngrok (immediate)

Every 10 minutes (start_ngrok.py loop):
    → Pushes ALL local images from D:\ComfyUI\_study\output\ to Railway
    → Gallery shows complete history

After Railway redeploys (code push):
    → image_store wiped
    → Lifespan reloads from ComfyUI history (25 recent images)
    → Within 10 minutes: start_ngrok.py re-registers all images
    → Full gallery restored automatically
```

**Note:** After a Railway redeploy, gallery may show only recent images for up to 10 minutes. This is expected behavior.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check + current ComfyUI server URL |
| `/generate` | POST | Submit batch generation job |
| `/status/{job_id}` | GET | Poll job status |
| `/gallery` | GET | Browse generated images |
| `/proxy-download/{filename}` | GET | Download image via proxy |
| `/register-images` | POST | Push local file list to Railway gallery |
| `/refresh` | POST | Reload image store from local folder |
| `/refresh-from-history` | POST | Reload image store from ComfyUI history |

## Tech Stack

- **ComfyUI** — Stable Diffusion workflow engine
- **ControlNet (OpenPose)** — Pose-consistent character generation
- **FastAPI** — Async HTTP API with Pydantic validation
- **Docker** — Containerized deployment
- **Railway** — Cloud deployment platform
- **ngrok** — Local-to-cloud tunnel (auto-started, auto-updates Railway)
- **GitHub** — Auto-deploy on push to main

## For GPU Owner — Local Development

No ngrok needed. Everything runs on localhost.

```bash
# Terminal 1 - ComfyUI
python start_comfyui.py

# Terminal 2 - local FastAPI
python start_uvicorn.py

# Terminal 3 - test
python test_local.py
```

Checks: test_local.py verifies uvicorn and ComfyUI are running before proceeding.

Gallery: `http://127.0.0.1:8000/gallery?server=http://127.0.0.1:8188`

Force restart if needed:
```bash
python start_uvicorn.py --restart
```

## For GPU Owner — Railway Testing

ngrok required. Railway runs FastAPI, your machine runs ComfyUI.

```bash
# Terminal 1 - ComfyUI
python start_comfyui.py

# Terminal 2 - ngrok (start once, leave running)
python start_ngrok.py

# Terminal 3 - test
python test_railway.py
```

**start_ngrok.py behavior:**
- Starts ngrok tunnel to port 8188
- Updates Railway COMFYUI_SERVER env var with ngrok URL
- Waits for Railway to finish redeploying
- Registers ALL local images with Railway gallery
- Re-registers ALL images every 10 minutes automatically
- Auto-restarts ngrok if it dies

**test_railway.py behavior:**
- Checks ngrok and ComfyUI are running
- Auto-detects ngrok URL
- Does NOT update Railway (no redeploy triggered)
- Submits generation job to Railway
- Polls until complete
- Registers ALL local images with Railway gallery
- Prints gallery URL

Force restart ngrok: `python start_ngrok.py --restart`

## For Remote Users

No setup needed. GPU owner must have start_comfyui.py and start_ngrok.py running.

**Option 1: Python script**
```bash
python test_remote.py
```

**Option 2: Standalone exe (no Python needed)**
Double-click `dist\test_remote_v1.exe`

**Option 3: Interactive browser**
```
https://comfyui-pipeline-production.up.railway.app/docs
```

**test_remote behavior:**
- Gets current ComfyUI server URL from Railway /health automatically
- No hardcoded URLs — works regardless of current ngrok URL
- Submits generation job to Railway
- Polls until complete
- Calls /refresh-from-history to update gallery
- Prints gallery URL

**Gallery after test_remote runs:**
- Shows ComfyUI session history immediately
- Shows ALL images within 10 minutes (when start_ngrok.py re-registers)

## Building test_remote.exe

```bash
# Double-click build_test_remote_exe.bat
# Output: dist\test_remote_v1.exe (auto-increments: v2, v3...)
```

Share `dist\test_remote_vN.exe` with remote users. They just double-click it.

## Environment Variables

### Railway Dashboard (auto-managed)
| Variable | Description |
|----------|-------------|
| `COMFYUI_SERVER` | Current ngrok URL — auto-updated by start_ngrok.py |

### Local .env file (GPU machine only, never commit)
```
RAILWAY_TOKEN=your_railway_api_token
RAILWAY_PROJECT_ID=b6d15edf-b462-43b3-96ac-91ebe0d2f74b
RAILWAY_ENVIRONMENT_ID=2e5c267c-c248-4c63-a1af-1c941a7d4d9e
RAILWAY_SERVICE_ID=22964829-7f96-4376-92f5-5d6ce42ec3c8
```

## Project Structure

```
comfyui-pipeline/
├── api.py                    # FastAPI service
├── comfyui_api.py            # ComfyUI orchestration
├── logger.py                 # CSV audit logging
├── workflow.json             # ComfyUI API-format workflow
├── variations.json           # Preset batch prompts (CLI only)
├── start_comfyui.py          # Starts ComfyUI (GPU machine)
├── start_ngrok.py            # Starts ngrok + auto-updates Railway
├── start_uvicorn.py          # Starts local FastAPI (dev only)
├── test_local.py             # Local development testing
├── test_railway.py           # Railway testing (GPU machine)
├── test_remote.py            # Remote user testing
├── build_test_remote_exe.bat # Builds versioned test_remote exe
├── Dockerfile                # Container definition
├── requirements.txt          # Python dependencies
└── .gitignore                # Excludes secrets and local paths
```

## Common Issues

| Error | Fix |
|-------|-----|
| Gallery shows only recent images | Wait up to 10 minutes for start_ngrok.py to re-register all images |
| ngrok URL expired | `python start_ngrok.py --restart` |
| Port 8000 in use | `python start_uvicorn.py --restart` |
| test_local: uvicorn not running | `python start_uvicorn.py` |
| test_railway: ngrok not running | `python start_ngrok.py` |
| test_remote: no comfyui_server | GPU owner needs start_comfyui.py and start_ngrok.py running |
| Railway not redeploying | Click Deploy manually in Railway dashboard |

## License

MIT
