from fastapi import FastAPI, HTTPException
import os
import requests

app = FastAPI(title="Home Assistant MCP Server (Diagnostic)")

# Read HA token from environment variable set by add-on options
HA_TOKEN = os.environ.get("HA_TOKEN")

if not HA_TOKEN:
    print("⚠️ Warning: HA_TOKEN not set. Check add-on configuration!")
else:
    print(f"✅ HA_TOKEN detected: {HA_TOKEN[:8]}... (truncated for security)")

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}" if HA_TOKEN else "",
    "Content-Type": "application/json",
}

HA_URL = "http://supervisor/core/api"  # Supervisor API endpoint

@app.get("/api/overview")
def overview():
    """Return a summary of Home Assistant environment and counts."""
    if not HA_TOKEN:
        raise HTTPException(status_code=500, detail="HA_TOKEN missing, cannot contact HA API.")
    
    try:
        resp = requests.get(f"{HA_URL}/config", headers=HEADERS, timeout=5)
        resp.raise_for_status()
        config = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error contacting HA API: {e}")

    # Minimal overview
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
