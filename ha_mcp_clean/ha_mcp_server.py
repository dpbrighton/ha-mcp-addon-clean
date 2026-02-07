import os
import time
import uuid
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException

# -----------------------------------------------------------------------------
# Diagnostic helpers
# -----------------------------------------------------------------------------

STARTUP_ID = str(uuid.uuid4())[:8]

def log(msg: str):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[MCP {STARTUP_ID}] [{ts}] {msg}", flush=True)

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------

app = FastAPI()

HA_TOKEN: str | None = None
HA_HEADERS: dict | None = None
HA_BASE_URL = "http://supervisor/core/api"

# -----------------------------------------------------------------------------
# Startup
# -----------------------------------------------------------------------------

@app.on_event("startup")
def startup_event():
    global HA_TOKEN, HA_HEADERS

    log("=== MCP STARTUP BEGIN ===")

    # Dump environment keys (NOT values) for diagnostics
    env_keys = sorted(os.environ.keys())
    log(f"Environment keys visible: {env_keys}")

    HA_TOKEN = os.environ.get("HA_TOKEN")

    if not HA_TOKEN or not HA_TOKEN.strip():
        log("❌ HA_TOKEN is missing or empty")
        raise RuntimeError("HA_TOKEN not set or empty. Check add-on configuration.")

    log("✅ HA_TOKEN present (value not logged)")

    HA_HEADERS = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    # Sanity check: call Home Assistant once at startup
    log("Performing Home Assistant connectivity check")
    try:
        r = requests.get(f"{HA_BASE_URL}/", headers=HA_HEADERS, timeout=5)
        log(f"HA connectivity check status: {r.status_code}")
        if r.status_code != 200:
            log(f"HA response body: {r.text}")
            raise RuntimeError("Home Assistant API did not return 200 at startup")
    except Exception as e:
        log(f"❌ Exception during HA connectivity check: {e}")
        raise

    log("=== MCP STARTUP COMPLETE ===")

# -----------------------------------------------------------------------------
# API endpoints
# -----------------------------------------------------------------------------

@app.get("/api/overview")
def api_overview():
    log("Handling /api/overview request")

    if not HA_HEADERS:
        log("❌ HA_HEADERS not initialized")
        raise HTTPException(status_code=500, detail="Server not initialized")

    try:
        r = requests.get(
            f"{HA_BASE_URL}/states",
            headers=HA_HEADERS,
            timeout=10,
        )
        log(f"/states status: {r.status_code}")

        if r.status_code != 200:
            log(f"/states error body: {r.text}")
            raise HTTPException(status_code=502, detail="Home Assistant API error")

        states = r.json()
        log(f"Retrieved {len(states)} states from Home Assistant")

        # Minimal, stable overview
        result = {
            "startup_id": STARTUP_ID,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "entity_count": len(states),
        }

        return result

    except HTTPException:
        raise
    except Exception as e:
        log(f"❌ Exception in /api/overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))
