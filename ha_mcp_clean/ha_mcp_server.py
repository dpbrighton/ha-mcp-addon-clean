import os
import requests
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Home Assistant MCP Server")

# Global variable to store the token (filled at startup)
HA_TOKEN = None
HA_HOST = os.environ.get("HA_HOST", "http://homeassistant.local:8123")
HEADERS = {}

@app.on_event("startup")
def startup_event():
    global HA_TOKEN, HEADERS
    HA_TOKEN = os.environ.get("HA_TOKEN")
    if not HA_TOKEN:
        print("❌ HA_TOKEN not set or empty. Check add-on config.")
        return  # Do not raise at import time
    HEADERS = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}
    # Test connection
    try:
        resp = requests.get(f"{HA_HOST}/api/", headers=HEADERS, timeout=5)
        resp.raise_for_status()
        print("✅ Connected to Home Assistant")
    except requests.RequestException as e:
        print(f"⚠️ Failed to connect to Home Assistant: {e}")

@app.get("/api/overview")
def get_overview():
    if not HA_TOKEN:
        raise HTTPException(status_code=500, detail="HA_TOKEN not set")
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

@app.get("/api/entities")
def get_entities():
    if not HA_TOKEN:
        raise HTTPException(status_code=500, detail="HA_TOKEN not set")
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
