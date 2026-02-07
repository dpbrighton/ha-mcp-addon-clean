from fastapi import FastAPI, HTTPException
import os
import requests
import uuid
from datetime import datetime
import asyncio
import json
import websockets

# -------------------------------------------------------------------
# App setup
# -------------------------------------------------------------------
app = FastAPI(title="Home Assistant MCP Server")
SESSION_ID = uuid.uuid4().hex[:8]

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[MCP {SESSION_ID}] [{ts}] {msg}", flush=True)

# -------------------------------------------------------------------
# Environment + token handling (baseline-safe)
# -------------------------------------------------------------------
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "").strip()
if not SUPERVISOR_TOKEN:
    raise RuntimeError("SUPERVISOR_TOKEN not set (must run as HA add-on)")

HA_API_BASE = "http://supervisor/core/api"
HEADERS = {
    "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
    "Content-Type": "application/json",
}

# Store token internally for reuse
INTERNAL_TOKEN = SUPERVISOR_TOKEN

# -------------------------------------------------------------------
# Startup diagnostics
# -------------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    log("=== MCP STARTUP BEGIN ===")
    visible_keys = sorted(os.environ.keys())
    log(f"Environment keys visible: {visible_keys}")

    log("✅ SUPERVISOR_TOKEN stored internally")

    try:
        resp = requests.get(f"{HA_API_BASE}/config", headers=HEADERS, timeout=5)
        log(f"HA connectivity check status: {resp.status_code}")
        if resp.status_code != 200:
            log(f"HA response body: {resp.text}")
            raise RuntimeError("Home Assistant API did not return 200 at startup")
        log("✅ Home Assistant connectivity confirmed")
    except Exception as e:
        log(f"❌ Exception during HA connectivity check: {e}")
        raise

    log("=== MCP STARTUP COMPLETE ===")

# -------------------------------------------------------------------
# Health check
# -------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "status": "running",
        "session_id": SESSION_ID,
        "supervisor_token_present": bool(SUPERVISOR_TOKEN),
    }

# -------------------------------------------------------------------
# Overview endpoint
# -------------------------------------------------------------------
@app.get("/api/overview")
def overview():
    try:
        resp = requests.get(f"{HA_API_BASE}/config", headers=HEADERS, timeout=5)
        resp.raise_for_status()
        config = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error contacting Home Assistant API: {e}")

    return {
        "home_assistant": {
            "version": config.get("version"),
            "location_name": config.get("name"),
            "time_zone": config.get("time_zone"),
            "unit_system": config.get("unit_system"),
            "installation_type": "homeassistant_os",
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

# -------------------------------------------------------------------
# Entities endpoint
# -------------------------------------------------------------------
@app.get("/api/entities")
def entities():
    try:
        resp = requests.get(f"{HA_API_BASE}/states", headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error fetching entities: {e}")

    return {
        "count": len(data),
        "entities": [
            {
                "entity_id": e.get("entity_id"),
                "state": e.get("state"),
                "domain": e.get("entity_id", "").split(".")[0],
            }
            for e in data
        ],
    }

# -------------------------------------------------------------------
# Tasks endpoint
# -------------------------------------------------------------------
@app.get("/api/tasks")
def tasks():
    try:
        resp = requests.get(f"{HA_API_BASE}/services/task", headers=HEADERS, timeout=5)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        tasks_data = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error fetching tasks from Home Assistant API: {e}")

    return tasks_data

# -------------------------------------------------------------------
# Automations endpoint
# -------------------------------------------------------------------
@app.get("/api/automations")
def automations():
    try:
        resp = requests.get(f"{HA_API_BASE}/states", headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error fetching automations from Home Assistant API: {e}")

    automations = [e for e in data if e.get("entity_id", "").startswith("automation.")]
    return {"count": len(automations), "automations": automations}

# -------------------------------------------------------------------
# Devices endpoint (WebSocket-backed, uses stored token)
# -------------------------------------------------------------------
async def fetch_devices_ws():
    ws_url = "ws://homeassistant:8123/api/websocket"
    try:
        async with websockets.connect(ws_url) as ws:
            # Step 1: Receive initial auth request
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            msg_json = json.loads(msg)

            # Step 2: Send auth using INTERNAL_TOKEN
            auth_msg = {"type": "auth", "access_token": INTERNAL_TOKEN}
            await ws.send(json.dumps(auth_msg))

            # Step 3: Wait for auth response
            auth_resp = await asyncio.wait_for(ws.recv(), timeout=5)
            auth_resp_json = json.loads(auth_resp)
            if not auth_resp_json.get("success", False):
                log(f"WebSocket auth failed: {auth_resp_json}")
                return []

            # Step 4: Request device registry
            req_id = 1
            req_msg = {"id": req_id, "type": "config/device_registry/list"}
            await ws.send(json.dumps(req_msg))

            # Step 5: Wait for response
            resp_msg = await asyncio.wait_for(ws.recv(), timeout=5)
            resp_json = json.loads(resp_msg)
            if resp_json.get("success", False):
                return resp_json.get("result", [])
            else:
                log(f"Device registry WebSocket failed: {resp_json}")
                return []

    except Exception as e:
        log(f"WebSocket devices error: {e}")
        return []

@app.get("/api/devices")
def devices():
    # Run the async WS fetch in the event loop
    devices_data = asyncio.run(fetch_devices_ws())
    return {"count": len(devices_data), "devices": devices_data}
