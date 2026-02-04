from fastapi import FastAPI
import os
import requests

app = FastAPI()

# Home Assistant API URL and token
HA_URL = "http://supervisor/core/api"  # Supervisor API endpoint
HA_TOKEN = os.environ.get("HA_TOKEN")  # This is set via the add-on options in HA

if not HA_TOKEN:
    raise RuntimeError("HA_TOKEN not set! Please configure it in the add-on options.")

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

@app.get("/api/overview")
def overview():
    """Return basic overview info about Home Assistant and counts of areas, devices, entities, automations, scripts, dashboards"""
    try:
        # Example: get general info from Supervisor API
        resp = requests.get(f"{HA_URL}/core/info", headers=HEADERS)
        resp.raise_for_status()
        core_info = resp.json()
    except Exception:
        # Fallback if Supervisor API not reachable
        core_info = {}

    # Minimal example counts (you can expand later)
    overview_data = {
        "home_assistant": {
            "version": core_info.get("version", "unknown"),
            "installation_type": core_info.get("installation_type", "unknown"),
            "location_name": core_info.get("location_name", "unknown"),
            "time_zone": core_info.get("time_zone", "unknown"),
            "currency": core_info.get("currency", "unknown"),
            "unit_system": core_info.get("unit_system", {"length": "unknown", "mass": "unknown", "temperature": "unknown"}),
        },
        "counts": {
            "areas": 0,
            "devices": 0,
            "entities": 0,
            "automations": 0,
            "scripts": 0,
            "dashboards": 0
        }
    }

    return overview_data
