from fastapi import FastAPI, HTTPException
import os
import requests

app = FastAPI(title="Home Assistant MCP Server")

# -------------------------------
# HA TOKEN read once at startup
# -------------------------------
HA_TOKEN = os.environ.get("HA_TOKEN", "").strip()
if not HA_TOKEN:
    raise RuntimeError("HA_TOKEN not set or empty. Check add-on config.")

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

HA_URL = "http://homeassistant:8123/api"

# -------------------------------
# Diagnostics (can comment out later)
# -------------------------------
import datetime
def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[MCP {ts}] {msg}", flush=True)

log("=== MCP STARTUP BEGIN ===")
log(f"Environment keys visible: {list(os.environ.keys())}")
log(f"HA_TOKEN present: {'✅' if HA_TOKEN else '❌'}")

# -------------------------------
# HEALTH CHECK
# -------------------------------
@app.get("/")
def root():
    return {
        "status": "running",
        "ha_token_present": bool(HA_TOKEN)
    }

# -------------------------------
# OVERVIEW ENDPOINT
# -------------------------------
@app.get("/api/overview")
def overview():
    try:
        resp = requests.get(f"{HA_URL}/config", headers=HEADERS, timeout=5)
        resp.raise_for_status()
        config = resp.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error contacting Home Assistant API: {e}"
        )
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

# -------------------------------
# ENTITIES ENDPOINT
# -------------------------------
@app.get("/api/entities")
def entities():
    try:
        resp = requests.get(f"{HA_URL}/states", headers=HEADERS, timeout=5)
        resp.raise_for_status()
        states = resp.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error contacting Home Assistant API: {e}"
        )
    return {
        "count": len(states),
        "entities": states
    }

# -------------------------------
# TASKS ENDPOINT (new)
# -------------------------------
@app.get("/api/tasks")
def tasks():
    # For now, this is a stub returning an empty list
    # Later we can implement real task aggregation
    return []

# -------------------------------
# ADDITIONAL ENDPOINTS (stubs for later)
# -------------------------------
@app.get("/api/automations")
def automations():
    return []

@app.get("/api/devices")
def devices():
    return []

@app.get("/api/areas")
def areas():
    return []

# -------------------------------
# STARTUP EVENT
# -------------------------------
@app.on_event("startup")
def startup_event():
    log("=== MCP STARTUP COMPLETE ===")
