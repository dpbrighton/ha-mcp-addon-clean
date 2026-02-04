from fastapi import FastAPI, HTTPException
import os
import requests

app = FastAPI()

# Get Home Assistant token from environment variable set by add-on
HA_TOKEN = os.environ.get("HA_TOKEN")
if not HA_TOKEN:
    raise RuntimeError("HA_TOKEN not set! Please configure it in the add-on options.")

# Base URL for Home Assistant Supervisor API
HA_URL = "http://supervisor/core/api"

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

@app.get("/api/overview")
def overview():
    """Return a high-level overview of Home Assistant installation"""
    try:
        resp = requests.get(f"{HA_URL}/config", headers=HEADERS, timeout=10)
        resp.raise_for_status()
        config_data = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to get overview: {e}")

    # Count areas, devices, entities, automations, scripts, dashboards
    try:
        resp_states = requests.get(f"{HA_URL}/states", headers=HEADERS, timeout=10)
        resp_states.raise_for_status()
        states = resp_states.json()
    except requests.RequestException:
        states = []

    # Return a structured overview
    return {
        "home_assistant": {
            "version": config_data.get("version"),
            "installation_type": config_data.get("installation_type"),
            "location_name": config_data.get("location_name"),
            "time_zone": config_data.get("time_zone"),
            "currency": config_data.get("currency"),
            "unit_system": config_data.get("unit_system"),
        },
        "counts": {
            "areas": len(config_data.get("areas", [])),
            "devices": len(config_data.get("devices", [])),
            "entities": len(states),
            "automations": len(config_data.get("automations", [])),
            "scripts": len(config_data.get("scripts", [])),
            "dashboards": len(config_data.get("dashboards", [])),
        }
    }

@app.get("/api/entities")
def entities():
    """Return all entities with their domain, area, attributes, and state"""
    try:
        resp = requests.get(f"{HA_URL}/states", headers=HEADERS, timeout=10)
        resp.raise_for_status()
        states = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to get entities: {e}")

    data = []
    for entity in states:
        entity_id = entity.get("entity_id")
        attributes = entity.get("attributes", {})
        data.append({
            "entity_id": entity_id,
            "state": entity.get("state"),
            "attributes": attributes,
            "area": attributes.get("area_id"),
            "domain": entity_id.split(".")[0] if entity_id else None
        })

    return {"entities": data}
