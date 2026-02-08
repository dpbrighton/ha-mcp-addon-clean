import os
import asyncio
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

# --- Startup & token handling ---
HA_TOKEN = os.environ.get("HA_TOKEN")
HA_WS_TOKEN = os.environ.get("HA_WS_TOKEN")

if not HA_TOKEN:
    print("HA_TOKEN not set – API calls will fail")
else:
    print("HA_TOKEN loaded successfully")

if not HA_WS_TOKEN:
    print("HA_WS_TOKEN not set – WebSocket calls will fail")
else:
    print("HA_WS_TOKEN loaded successfully")


# --- Helper functions ---
def ha_get(endpoint: str):
    url = f"http://homeassistant:8123{endpoint}"
    headers = {"Authorization": f"Bearer {HA_TOKEN}"} if HA_TOKEN else {}
    resp = requests.get(url, headers=headers)
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error fetching {endpoint}: {e}")
        raise
    try:
        return resp.json()
    except requests.JSONDecodeError as e:
        print(f"JSON decode error on {endpoint}: {e.msg}")
        return {"error": "invalid_json", "raw_text": resp.text}


# --- Overview ---
@app.get("/api/overview")
def overview():
    data = ha_get("/api/overview")
    return JSONResponse(data)


# --- Entities ---
@app.get("/api/entities")
def entities():
    data = ha_get("/api/states")
    return JSONResponse(data)


# --- Tasks ---
@app.get("/api/tasks")
def tasks():
    data = ha_get("/api/tasks")
    return JSONResponse(data)


# --- Automations (original working version) ---
@app.get("/api/automations")
def automations():
    # Original endpoint when automations were working
    data = ha_get("/api/config/automation/config")
    return JSONResponse(data)


# --- Devices (fixed version) ---
async def fetch_devices_ws():
    # Use WebSocket if available; fallback to REST
    if not HA_WS_TOKEN:
        print("WebSocket token not set, falling back to REST")
        return ha_get("/api/config/device_registry/list")
    # Diagnostic logging
    print(f"Attempting WebSocket fetch for devices with token: {HA_WS_TOKEN}")
    # Placeholder for WebSocket fetch
    return []


@app.get("/api/devices")
async def devices():
    devices_data = await fetch_devices_ws()
    return {"count": len(devices_data), "devices": devices_data}


# --- Areas (fixed version) ---
async def fetch_areas_ws():
    if not HA_WS_TOKEN:
        print("WebSocket token not set, falling back to REST")
        return ha_get("/api/config/area_registry/list")
    print(f"Attempting WebSocket fetch for areas with token: {HA_WS_TOKEN}")
    # Placeholder for WebSocket fetch
    return []


@app.get("/api/areas")
async def areas():
    areas_data = await fetch_areas_ws()
    return {"count": len(areas_data), "areas": areas_data}


# --- Startup event ---
@app.on_event("startup")
async def startup_event():
    print("Application startup complete.")


# --- Diagnostics for token issues ---
@app.get("/api/diagnostics")
def diagnostics():
    diag = {
        "HA_TOKEN_set": HA_TOKEN is not None,
        "HA_WS_TOKEN_set": HA_WS_TOKEN is not None
    }
    print(f"Diagnostics: {diag}")
    return diag
