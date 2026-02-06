from fastapi import FastAPI, HTTPException
import os
import requests

app = FastAPI(title="Home Assistant MCP Server")

# -------------------------------
# HA Core API URL
# -------------------------------
HA_URL = "http://homeassistant:8123/api"

# -------------------------------
# Function to get HA headers safely
# -------------------------------
def get_ha_headers():
    """
    Reads HA_TOKEN from environment on each request.
    Raises RuntimeError if token is missing or empty.
    """
    token = os.environ.get("HA_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HA_TOKEN not set or empty. Check add-on config.")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

# -------------------------------
# Startup event to verify token
# -------------------------------
@app.on_event("startup")
def check_ha_token():
    try:
        _ = get_ha_headers()
        print("✅ HA_TOKEN is present at startup")
    except RuntimeError as e:
        print(f"❌ {e}")
        # Container continues running; endpoints will raise 500 if token missing

# -------------------------------
# Helper: fetch from HA Core
# -------------------------------
def ha_get(path: str):
    """
    GET request to Home Assistant Core API with proper headers.
    Raises HTTPException if request fails.
    """
    headers = get_ha_headers()
    try:
        resp = requests.get(f"{HA_URL}{path}", headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error contacting Home Assistant API: {e}")

# -------------------------------
# Health check endpoint
# -------------------------------
@app.get("/")
def root():
    return {
        "status": "running",
        "ha_token_present": bool(os.environ.get("HA_TOKEN", "").strip())
    }

# -------------------------------
# Overview endpoint
# -------------------------------
@app.get("/api/overview")
def overview():
    try:
        config = ha_get("/config")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException as e:
        raise e

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
# Entities endpoint
# -------------------------------
@app.get("/api/entities")
def entities():
    """
    Returns canonical entity inventory.
    Preserves entity_id, device_id, area_id exactly as in Home Assistant.
    """
    try:
        states = ha_get("/states")
        areas = ha_get("/areas")
        devices = ha_get("/devices")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException as e:
        raise e

    # Map areas and devices
    area_map = {area["area_id"]: area["name"] for area in areas}
    device_map = {device["id"]: {"name": device.get("name"), "area_id": device.get("area_id")} for device in devices}

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

            "attributes": {k: v for k, v in attrs.items() if k not in ("friendly_name", "device_id")}
        })

    return {
        "total": len(results),
        "entities": results
    }

# -------------------------------
# Tasks endpoint (stub)
# -------------------------------
@app.get("/api/tasks")
def tasks():
    """
    Placeholder for future AI task endpoints.
    """
    return []
