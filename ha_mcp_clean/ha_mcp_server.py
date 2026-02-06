import os
import requests
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Home Assistant MCP Server")

# === Global HA token ===
HA_TOKEN = os.environ.get("HA_TOKEN")
if not HA_TOKEN:
    raise RuntimeError("HA_TOKEN not set or empty. Check add-on config.")

# === Home Assistant connection settings ===
HA_HOST = os.environ.get("HA_HOST", "http://homeassistant.local:8123")
HEADERS = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}

# === Startup event ===
@app.on_event("startup")
def startup_event():
    # Simple check to confirm we can talk to HA
    try:
        resp = requests.get(f"{HA_HOST}/api/", headers=HEADERS, timeout=5)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to connect to Home Assistant at {HA_HOST}: {e}")

# === Overview endpoint ===
@app.get("/api/overview")
def get_overview():
    try:
        resp = requests.get(f"{HA_HOST}/api/states", headers=HEADERS, timeout=5)
        resp.raise_for_status()
        states = resp.json()
        overview = {
            "entity_count": len(states),
            "entities": [s["entity_id"] for s in states],
        }
        return overview
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error fetching overview: {e}")

# === Entities endpoint ===
@app.get("/api/entities")
def get_entities():
    try:
        resp = requests.get(f"{HA_HOST}/api/states", headers=HEADERS, timeout=5)
        resp.raise_for_status()
        states = resp.json()
        results = []
        for s in states:
            results.append({
                "entity_id": s.get("entity_id"),
                "state": s.get("state"),
                "attributes": s.get("attributes", {}),
            })
        return results
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error fetching entities: {e}")
