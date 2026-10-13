import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"

LOG_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(PROJECT_ROOT))

log_file = open(
    LOG_DIR / "netwatch.log",
    "a",
    buffering=1,
)

error_file = open(
    LOG_DIR / "netwatch-error.log",
    "a",
    buffering=1,
)

sys.stdout = log_file
sys.stderr = error_file


import uvicorn


uvicorn.run(
    "backend.main:app",
    host="127.0.0.1",
    port=8000,
    log_level="info",
)