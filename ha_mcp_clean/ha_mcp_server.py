from fastapi import FastAPI
import os
import requests

app = FastAPI()

# Read HA token from environment (set via add-on GUI)
HA_TOKEN = os.environ.get("HA_TOKEN")
if not HA_TOKEN:
    raise RuntimeError("HA_TOKEN not set! Please configure it in the add-on options.")

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

HA_URL = "http://supervisor/core/api"

@app.get("/api/overview")
def overview():
    """Return a high-level overview of Home Assistant"""
    # Fetch general info from the supervisor API
    resp = requests.get(f"{HA_URL}/config", headers=HEADERS)
    resp.raise_for_status()
    config = resp.json()

    # Example counts — fetch entities, areas, automations
    counts = {}
    try:
        states_resp = requests.get(f"{HA_URL}/states", headers=HEADERS)
        states_resp.raise_for_status()
        states = states_resp.json()
        counts["entities"] = len(states)
    except Exception:
        counts["entities"] = 0

    try:
        areas_resp = requests.get(f"{HA_URL}/areas", headers=HEADERS)
        areas_resp.raise_for_status()
        counts["areas"] = len(areas_resp.json())
    except Exception:
        counts["areas"] = 0

    try:
        automations_resp = requests.get(f"{HA_URL}/automations", headers=HEADERS)
        automations_resp.raise_for_status()
        counts["automations"] = len(automations_resp.json())
    except Exception:
        counts["automations"] = 0

    return {
        "home_assistant": {
            "version": config.get("version"),
            "installation_type": config.get("installation_type"),
            "location_name": config.get("location_name"),
            "time_zone": config.get("time_zone"),
            "currency": config.get("currency"),
            "unit_system": config.get("unit_system", {}),
        },
        "counts": counts
    }
