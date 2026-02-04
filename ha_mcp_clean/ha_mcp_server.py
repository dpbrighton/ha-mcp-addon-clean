from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
import requests

app = FastAPI(title="Home Assistant MCP Server")

# Read token from add-on GUI config
HA_TOKEN = os.environ.get("HA_TOKEN")
if not HA_TOKEN:
    raise RuntimeError("HA_TOKEN not set! Please configure it in the add-on options.")

# Base headers for Home Assistant Supervisor API
HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

# Base URL for Home Assistant Supervisor API
HA_BASE_URL = "http://supervisor/core/api"


@app.get("/api/overview")
def overview():
    """Return general Home Assistant overview information."""
    try:
        url = f"{HA_BASE_URL}/states"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        states = resp.json()
        areas = set()
        devices = set()
        entities_count = len(states)
        automations_count = 0
        scripts_count = 0
        dashboards_count = 0

        # Count unique areas and devices
        for entity in states:
            area = entity.get("attributes", {}).get("area_id")
            if area:
                areas.add(area)
            device = entity.get("attributes", {}).get("device_id")
            if device:
                devices.add(device)

            # Count automations and scripts
            domain = entity.get("entity_id", "").split(".")[0]
            if domain == "automation":
                automations_count += 1
            elif domain == "script":
                scripts_count += 1
            elif domain == "dashboard":
                dashboards_count += 1

        data = {
            "home_assistant": {
                "version": os.environ.get("SUPERVISOR_VERSION", "unknown"),
                "installation_type": "Home Assistant OS",
                "location_name": "Home",
                "time_zone": "Europe/London",
                "currency": "GBP",
                "unit_system": {"length": "metric", "mass": "metric", "temperature": "celsius"},
            },
            "counts": {
                "areas": len(areas),
                "devices": len(devices),
                "entities": entities_count,
                "automations": automations_count,
                "scripts": scripts_count,
                "dashboards": dashboards_count,
            },
        }
        return JSONResponse(content=data)
    except requests.RequestException as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/entities")
def entities():
    """Return all entities with domain, area, and state info."""
    try:
        url = f"{HA_BASE_URL}/states"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        states = resp.json()

        data = []
        for entity in states:
            data.append({
                "entity_id": entity.get("entity_id"),
                "state": entity.get("state"),
                "attributes": entity.get("attributes", {}),
                "area": entity.get("attributes", {}).get("area_id"),
                "domain": entity.get("entity_id", "").split(".")[0],
            })

        return JSONResponse(content={"entities": data})
    except requests.RequestException as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
