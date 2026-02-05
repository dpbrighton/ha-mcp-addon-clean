from fastapi import FastAPI, HTTPException
import os
import requests
import sys

app = FastAPI(title="Home Assistant MCP Server")

# -------------------------------
# DIAGNOSTIC ENVIRONMENT LOGGING
# -------------------------------
print("=== MCP ENVIRONMENT DUMP ===", flush=True)

for key, value in os.environ.items():
    if "HA" in key or "TOKEN" in key:
        print(f"{key}={value}", flush=True)

print("=== END ENV DUMP ===", flush=True)

# -------------------------------
# TOKEN HANDLING
# -------------------------------
HA_TOKEN = os.environ.get("HA_TOKEN")

if not HA_TOKEN:
    print("❌ ERROR: HA_TOKEN not found in environment", flush=True)
else:
    print(f"✅ HA_TOKEN detected (truncated): {HA_TOKEN[:10]}...", flush=True)

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}" if HA_TOKEN else "",
    "Content-Type": "application/json",
}

# Supervisor API endpoint (correct for add-ons)
HA_URL = "http://supervisor/core/api"

# -------------------------------
# HEALTH CHECK
# -------------------------------
@app.get("/")
def root():
    return {
        "status": "running",
        "ha_token_present": bool(HA_TOKEN),
    }

# -------------------------------
# OVERVIEW ENDPOINT
# -------------------------------
@app.get("/api/overview")
def overview():
    if not HA_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="HA_TOKEN not set in add-on environment",
        )

    try:
        resp = requests.get(
            f"{HA_URL}/config",
            headers=HEADERS,
            timeout=5,
        )
        resp.raise_for_status()
        config = resp.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error contacting Supervisor API: {e}",
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

# -------------------------------
# TASKS ENDPOINT (stub)
# -------------------------------
@app.get("/api/tasks")
def tasks():
    return []

