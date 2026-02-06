from fastapi import FastAPI, HTTPException
import os
import requests

app = FastAPI(title="Home Assistant MCP Server")

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

HA_URL = "http://homeassistant:8123/api"

# -------------------------------------------------
# TOKEN HANDLING
# -------------------------------------------------

def get_ha_headers():
    """
    Read HA_TOKEN from environment on each request.
    Strip whitespace to avoid copy/paste issues.
    """
    token = os.environ.get("HA_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HA_TOKEN not set or empty. Check add-on config.")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

# -------------------------------------------------
# DIAGNOSTICS (startup only)
# -------------------------------------------------

print("=== MCP OPTIONS CHECK ===", flush=True)
print(f"ha_token present: {bool(os.environ.get('HA_TOKEN', '').strip())}", flush=True)
print("=== END OPTIONS CHECK ===", flush=True)

# -------------------------------------------------
# HELPER: GET FROM HA
# -------------------------------------------------

def ha_get(path: str):
    headers = get_ha_headers()
    resp = requests.get(f"{HA_URL}{path}", headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()

# -------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------

@app.get("/")
def root():
    return {
        "status": "running",
        "ha_token_present": bool(os.environ.get("HA_TOKEN", "").strip())
    }

# -------------------------------------------------
# OVERVIEW ENDPOINT
# -------------------------------------------------

@app.get("/api/overview")
def overview():
    try:
        config = ha_get("/config")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

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

# -------------------------------------------------
# ENTITIES ENDPOINT (PHASE 1 CORE)
# -------------------------------------------------

@app.get("/api/entities")
def entities():
    """
    Canonical entity inventory.
    Identifiers exactly match Home Assistant.
    """
    try:
        states = ha_get("/states")
        areas = ha_get("/areas")
        devices = ha_get("/devices")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Build lookup maps
    area_map = {
        area["area_id"]: area["name"]
        for area in areas
    }

    device_map = {
        device["id"]: {
            "name": device.get("name"),
            "area_id": device.get("area_id"),
        }
        for device in devices
    }

    results = []

    for state in states:
        entity_id = state["entity_id"]
        domain = entity_id.split(".")[0]

        attrs = state.get("attributes", {})
        device_id = attrs.get("device_id")
        device = device_map.get(device_id, {})

        area_id = device.get("area_id")
        area_name = area_map.get(area_id)

        results.append({
            "entity_id": entity_id,
            "domain": domain,
            "name": attrs.get("friendly_name"),
            "state": state.get("state"),

            "area_id": area_id,
            "area_name": area_name,

            "device_id": device_id,
            "device_name": device.get("name"),

            # Preserve attributes but exclude noisy identity fields
            "attributes": {
                k: v
                for k, v in attrs.items()
                if k not in ("friendly_name", "device_id")
            }
        })

    return {
        "total": len(results),
        "entities": results
    }

# -------------------------------------------------
# TASKS (STUB FOR FUTURE MCP ACTIONS)
# -------------------------------------------------

@app.get("/api/tasks")
def tasks():
    return []
