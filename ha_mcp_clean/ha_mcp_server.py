from fastapi import FastAPI, HTTPException
import os
import requests
from datetime import datetime

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
# Diagnostics
# -------------------------------
def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

print(f"[{timestamp()}] === MCP ENVIRONMENT DUMP ===", flush=True)
for key, value in os.environ.items():
    if "HA" in key or "TOKEN" in key:
        print(f"[{timestamp()}] {key}='{value}'", flush=True)
print(f"[{timestamp()}] === END ENV DUMP ===", flush=True)

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
# TASKS ENDPOINT
# -------------------------------
@app.get("/api/tasks")
def tasks():
    try:
        resp = requests.get(f"{HA_URL}/services/task", headers=HEADERS, timeout=5)
        if resp.status_code == 404:
            # If HA does not have tasks configured, return empty list
            return []
        resp.raise_for_status()
        tasks_data = resp.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error fetching tasks from Home Assistant API: {e}"
        )
    return tasks_data

# -------------------------------
# AUTOMATIONS ENDPOINT
# -------------------------------
@app.get("/api/automations")
def automations():
    try:
        resp = requests.get(f"{HA_URL}/states", headers=HEADERS, timeout=5)
        resp.raise_for_status()
        all_states = resp.json()
        automations_list = [
            state for state in all_states if state.get("entity_id", "").startswith("automation.")
        ]
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error fetching automations from Home Assistant API: {e}"
        )
    return automations_list

# -------------------------------
# ENTRY POINT
# -------------------------------
@app.on_event("startup")
def startup_event():
    print(f"[{timestamp()}] === MCP STARTUP BEGIN ===", flush=True)
    print(f"[{timestamp()}] Environment keys visible: {list(os.environ.keys())}", flush=True)
    
    # Simple connectivity check
    try:
        resp = requests.get(f"{HA_URL}/config", headers=HEADERS, timeout=5)
        if resp.status_code != 200:
            raise RuntimeError("Home Assistant API did not return 200 at startup")
        print(f"[{timestamp()}] ✅ Home Assistant connectivity confirmed", flush=True)
    except Exception as e:
        print(f"[{timestamp()}] ❌ Exception during HA connectivity check: {e}", flush=True)
        raise

    print(f"[{timestamp()}] === MCP STARTUP COMPLETE ===", flush=True)
