from fastapi import FastAPI, HTTPException
import os
import requests

app = FastAPI(title="Home Assistant MCP Server")

# Read token from add-on environment
HA_TOKEN = os.environ.get("HA_TOKEN")

if not HA_TOKEN:
    raise RuntimeError(
        "HA_TOKEN not set. Please configure ha_token in the add-on options."
    )

# Normal Home Assistant Core API (NOT Supervisor)
HA_URL = "http://homeassistant:8123/api"

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}


@app.get("/api/tasks")
def tasks():
    """Simple heartbeat endpoint for MCP client."""
    return {"status": "ok"}


@app.get("/api/overview")
def overview():
    """Return a basic overview of Home Assistant."""
    try:
        resp = requests.get(
            f"{HA_URL}/config",
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        config = resp.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error contacting Home Assistant API: {e}",
        )

    return {
        "home_assistant": {
            "version": config.get("version"),
            "installation_type": config.get("installation_type"),
            "location_name": config.get("location_name"),
            "time_zone": config.get("time_zone"),
            "unit_system": config.get("unit_system"),
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
