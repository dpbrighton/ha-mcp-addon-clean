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
# Diagnostics
# -------------------------------
print("=== MCP ENVIRONMENT CHECK ===", flush=True)
print(f"HA_TOKEN present: {bool(HA_TOKEN)}", flush=True)
print("=== END ENV CHECK ===", flush=True)

# -------------------------------
# Helper function to fetch HA endpoints
# -------------------------------
def ha_get(path: str):
    resp = requests.get(f"{HA_URL}{path}", headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()

# -------------------------------
# Health check
# -------------------------------
@app.get("/")
def root():
    return {
        "status": "running",
        "ha_token_present": bool(HA_TOKEN)
    }

# -------------------------------
# Overview endpoint
# -------------------------------
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

# -------------------------------
# Entities endpoint
# -------------------------------
@app.get("/api/entities")
def entities():
    try:
        states = ha_get("/states")
        areas = ha_get("/areas")
        devices = ha_get("/devices")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

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

    return {"total": len(results), "entities": results}

# -------------------------------
# Tasks endpoint (stub)
# -------------------------------
@app.get("/api/tasks")
def tasks():
    return []
