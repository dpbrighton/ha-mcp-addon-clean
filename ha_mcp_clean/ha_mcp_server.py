import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import requests

app = FastAPI(title="Home Assistant MCP Server")

# Global variable to hold the token
HA_TOKEN = None

# --- Startup event to safely load HA_TOKEN ---
@app.on_event("startup")
def startup_event():
    global HA_TOKEN
    HA_TOKEN = os.environ.get("HA_TOKEN", "").strip()
    if not HA_TOKEN:
        raise RuntimeError("HA_TOKEN not set or empty. Check add-on config.")
    print("✅ HA_TOKEN successfully loaded at startup")

# --- Helper function to make HA API requests ---
def ha_request(endpoint):
    url = f"http://homeassistant:8123{endpoint}"
    headers = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"[ERROR] Fetching {endpoint}: {e}")
        return None

# --- API endpoint: Overview ---
@app.get("/api/overview")
def get_overview():
    data = ha_request("/api/states")
    if data is None:
        return JSONResponse(status_code=500, content={"error": "Failed to fetch overview"})
    # Build simple overview structure
    overview = {"total_entities": len(data)}
    return overview

# --- API endpoint: Entities ---
@app.get("/api/entities")
def get_entities():
    data = ha_request("/api/states")
    if data is None:
        return JSONResponse(status_code=500, content={"error": "Failed to fetch entities"})
    results = []
    for entity in data:
        results.append({
            "entity_id": entity.get("entity_id"),
            "state": entity.get("state"),
            "attributes": entity.get("attributes")
        })
    return results

# --- Root endpoint ---
@app.get("/")
def root():
    return {"message": "Home Assistant MCP Server is running"}
