from fastapi import FastAPI, HTTPException
import os
import requests

app = FastAPI(title="Home Assistant MCP Server")

# Read HA token from environment variable set by add-on options
HA_TOKEN = os.environ.get("HA_TOKEN")
if not HA_TOKEN:
    raise RuntimeError(
        "HA_TOKEN not set! Please configure it in the add-on options in Home Assistant."
    )

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

HA_URL = "http://supervisor/core/api"  # Supervisor API endpoint

@app.get("/api/overview")
def overview():
    """Return a summary of Home Assistant environment and counts."""
    try:
        resp = requests.get(f"{HA_URL}/config", headers=HEADERS, timeout=5)
        resp.raise_for_status()
        config = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error contacting HA API: {e}")

    # Dummy counts for demonstration; can expand to real counts later
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
