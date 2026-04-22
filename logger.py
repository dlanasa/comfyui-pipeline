import csv
import os
from datetime import datetime

LOG_FILE = r"D:\ComfyUI\_study\generation_log.csv"

def init_log():
    """Create log file with headers if it doesn't exist"""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "variation", "prompt",
                             "seed", "filename", "duration_seconds", "status"])
        print(f"Log created: {LOG_FILE}")

def log_generation(variation, prompt, seed, filename, duration, status="success"):
    """Append a generation record to the log"""
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            variation,
            prompt,
            seed,
            filename,
            round(duration, 2),
            status
        ])