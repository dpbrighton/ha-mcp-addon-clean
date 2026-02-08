import os
import requests
from fastapi import FastAPI

app = FastAPI()

# Load Home Assistant token from environment
HA_TOKEN = os.environ.get("HA_TOKEN")
HA_WS_TOKEN = os.environ.get("HA_WS_TOKEN")  # Optional, for WebSocket

HEADERS = {"Authorization": f"Bearer {HA_TOKEN}"} if HA_TOKEN else {}

# -----------------
# Helper functions
# -----------------
def ha_get(endpoint):
    url = f"http://homeassistant:8123{endpoint}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        print(f"HTTP error fetching {endpoint}: {e}")
        raise
    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")
        raise

# -----------------
# Endpoints
# -----------------
@app.get("/api/entities")
def entities():
    return ha_get("/api/states")  # This works

@app.get("/api/tasks")
def tasks():
    return ha_get("/api/tasks")  # Assuming this works

@app.get("/api/automations")
def automations():
    # This is the version that was failing
    try:
        return ha_get("/api/config/automation/config")  # Failing endpoint
    except Exception as e:
        print("Automations fetch failed:", e)
        return {"error": "Automations fetch failed", "details": str(e)}

@app.get("/api/devices")
def devices():
    # Working devices code after token fix
    try:
        return ha_get("/api/config/device_registry/list")
    except Exception as e:
        print("Devices fetch failed:", e)
        return {"error": "Devices fetch failed", "details": str(e)}

@app.get("/api/areas")
def areas():
    # Working areas code after token fix
    try:
        return ha_get("/api/config/area_registry/list")
    except Exception as e:
        print("Areas fetch failed:", e)
        return {"error": "Areas fetch failed", "details": str(e)}
