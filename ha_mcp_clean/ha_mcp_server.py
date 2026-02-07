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

print(f"[MCP {id(app)}] [{timestamp()}] === MCP STARTUP BEGIN ===", flush=True)
print(f"[MCP {id(app)}] [{timestamp()}] Environment keys visible: {list(os.environ.keys())}", flush=True)
print(f"[MCP {id(app)}] [{timestamp()}] ✅ HA_TOKEN present (value not logged)", flush=True)

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
        all_entities = resp.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error fetching entities: {e}"
        )
    return {
        "count": len(all_entities),
        "entities": all_entities
    }

# -------------------------------
# TASKS ENDPOINT - FULL IMPLEMENTATION
# -------------------------------
@app.get("/api/tasks")
def tasks():
    """
    Returns Home Assistant tasks (currently maps to scripts & automations that are in 'on' state)
    """
    try:
        # Fetch scripts
        resp_scripts = requests.get(f"{HA_URL}/states", headers=HEADERS, timeout=5)
        resp_scripts.raise_for_status()
        entities = resp_scripts.json()

        tasks_list = []
        for entity in entities:
            if entity["entity_id"].startswith("script.") and entity["state"] == "on":
                tasks_list.append({
                    "entity_id": entity["entity_id"],
                    "state": entity["state"],
                    "attributes": entity.get("attributes", {})
                })
        # Return tasks
        return tasks_list

    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error fetching tasks: {e}"
        )

# -------------------------------
# PLACEHOLDER ENDPOINTS (to be implemented later)
# -------------------------------
@app.get("/api/automations")
def automations():
    raise HTTPException(status_code=404, detail="Endpoint not implemented yet")

@app.get("/api/devices")
def devices():
    raise HTTPException(status_code=404, detail="Endpoint not implemented yet")

@app.get("/api/areas")
def areas():
    raise HTTPException(status_code=404, detail="Endpoint not implemented yet")
