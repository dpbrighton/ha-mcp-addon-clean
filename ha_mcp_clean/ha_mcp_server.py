from fastapi import FastAPI, HTTPException
import os
import requests
import uuid
from datetime import datetime

# -------------------------------------------------------------------
# App setup
# -------------------------------------------------------------------
app = FastAPI(title="Home Assistant MCP Server")

SESSION_ID = uuid.uuid4().hex[:8]

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[MCP {SESSION_ID}] [{ts}] {msg}", flush=True)

# -------------------------------------------------------------------
# Environment + token handling (ADD-ON SAFE)
# -------------------------------------------------------------------
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "").strip()
HA_TOKEN = os.environ.get("HA_TOKEN", "").strip()

HA_API_BASE = "http://supervisor/core/api"
HA_BASE = "http://homeassistant:8123/api"

HEADERS_SUPERVISOR = {
    "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
    "Content-Type": "application/json",
}

HEADERS_HA = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

# -------------------------------------------------------------------
# Startup diagnostics ONLY (no hard crash unless token missing)
# -------------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    log("=== MCP STARTUP BEGIN ===")
    visible_keys = sorted(os.environ.keys())
    log(f"Environment keys visible: {visible_keys}")

    if not SUPERVISOR_TOKEN:
        log("❌ SUPERVISOR_TOKEN is missing")
        raise RuntimeError("SUPERVISOR_TOKEN not set (this must run as a Home Assistant add-on)")

    log("✅ SUPERVISOR_TOKEN present (value not logged)")

    # Connectivity check (diagnostic, but fatal if unauthorized)
    try:
        log("Performing Home Assistant connectivity check")
        resp = requests.get(f"{HA_API_BASE}/config", headers=HEADERS_SUPERVISOR, timeout=5)
        log(f"HA connectivity check status: {resp.status_code}")
        if resp.status_code != 200:
            log(f"HA response body: {resp.text}")
            raise RuntimeError("Home Assistant API did not return 200 at startup")
        log("✅ Home Assistant connectivity confirmed")
    except Exception as e:
        log(f"❌ Exception during HA connectivity check: {e}")
        raise

    log("=== MCP STARTUP COMPLETE ===")

# -------------------------------------------------------------------
# Health check
# -------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "status": "running",
        "session_id": SESSION_ID,
        "supervisor_token_present": bool(SUPERVISOR_TOKEN),
        "ha_token_present": bool(HA_TOKEN),
    }

# -------------------------------------------------------------------
# Overview endpoint
# -------------------------------------------------------------------
@app.get("/api/overview")
def overview():
    try:
        resp = requests.get(f"{HA_API_BASE}/config", headers=HEADERS_SUPERVISOR, timeout=5)
        resp.raise_for_status()
        config = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error contacting Home Assistant API: {e}")

    return {
        "home_assistant": {
            "version": config.get("version"),
            "location_name": config.get("name"),
            "time_zone": config.get("time_zone"),
            "unit_system": config.get("unit_system"),
            "installation_type": "homeassistant_os",
        },
        "counts": {
            "areas": 0,
            "devices": 0,
            "entities": 0,
            "automations": 0,
            "scripts": 0,
            "dashboards": 0,
        },
    }

# -------------------------------------------------------------------
# Entities endpoint
# -------------------------------------------------------------------
@app.get("/api/entities")
def entities():
    try:
        resp = requests.get(f"{HA_API_BASE}/states", headers=HEADERS_SUPERVISOR, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error fetching entities: {e}")

    return {
        "count": len(data),
        "entities": [
            {
                "entity_id": e.get("entity_id"),
                "state": e.get("state"),
                "domain": e.get("entity_id", "").split(".")[0],
            }
            for e in data
        ],
    }

# -------------------------------------------------------------------
# Tasks endpoint (stub)
# -------------------------------------------------------------------
@app.get("/api/tasks")
def tasks():
    return []

# -------------------------------------------------------------------
# Automations endpoint
# -------------------------------------------------------------------
@app.get("/api/automations")
def automations():
    try:
        resp = requests.get(f"{HA_BASE}/config/automation/config", headers=HEADERS_HA, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        log(f"Automations fetch failed: {e}")
        raise HTTPException(status_code=502, detail=f"Error fetching automations: {e}")

    return {
        "count": len(data),
        "automations": data,
    }

# -------------------------------------------------------------------
# Devices endpoint
# -------------------------------------------------------------------
@app.get("/api/devices")
def devices():
    try:
        resp = requests.get(f"{HA_BASE}/device_registry", headers=HEADERS_HA, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        log(f"Devices fetch failed: {e}")
        return []

    return {
        "count": len(data),
        "devices": [
            {
                "id": d.get("id"),
                "name": d.get("name"),
                "model": d.get("model"),
                "manufacturer": d.get("manufacturer"),
            }
            for d in data
        ],
    }

# -------------------------------------------------------------------
# Areas endpoint
# -------------------------------------------------------------------
@app.get("/api/areas")
def areas():
    try:
        resp = requests.get(f"{HA_BASE}/area_registry", headers=HEADERS_HA, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        log(f"Areas fetch failed: {e}")
        return []

    return {
        "count": len(data),
        "areas": [
            {
                "id": a.get("id"),
                "name": a.get("name"),
                "description": a.get("description"),
            }
            for a in data
        ],
    }
