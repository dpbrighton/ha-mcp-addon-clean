import os
import json
import logging
import requests
import websockets
import asyncio

from fastapi import FastAPI, HTTPException

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ha-mcp")

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(title="Home Assistant MCP Server")

# -----------------------------------------------------------------------------
# Global state (single source of truth)
# -----------------------------------------------------------------------------
HA_TOKEN: str | None = None
HA_HTTP_BASE = "http://homeassistant:8123"
HA_WS_URL = "ws://homeassistant:8123/api/websocket"

# -----------------------------------------------------------------------------
# Startup: capture token ONCE
# -----------------------------------------------------------------------------
@app.on_event("startup")
def startup():
    global HA_TOKEN
    log.info("=== MCP STARTUP BEGIN ===")
    log.info("Environment keys visible: %s", list(os.environ.keys()))

    HA_TOKEN = (
        os.getenv("HA_TOKEN")
        or os.getenv("HASSIO_TOKEN")
        or os.getenv("SUPERVISOR_TOKEN")
    )

    if not HA_TOKEN:
        raise RuntimeError("No Home Assistant token found in environment")

    log.info("✅ Home Assistant token captured and stored")
    log.info("=== MCP STARTUP COMPLETE ===")

# -----------------------------------------------------------------------------
# REST helper (uses stored token only)
# -----------------------------------------------------------------------------
def ha_rest_get(path: str):
    assert HA_TOKEN, "HA_TOKEN not initialised"
    resp = requests.get(
        f"{HA_HTTP_BASE}{path}",
        headers={"Authorization": f"Bearer {HA_TOKEN}"},
        timeout=10,
    )
    return resp

# -----------------------------------------------------------------------------
# WebSocket helper
# -----------------------------------------------------------------------------
async def ha_ws_call(command: dict) -> dict:
    assert HA_TOKEN, "HA_TOKEN not initialised"
    async with websockets.connect(HA_WS_URL) as ws:
        msg = json.loads(await ws.recv())
        if msg.get("type") != "auth_required":
            raise RuntimeError(f"Unexpected WS message: {msg}")

        await ws.send(json.dumps({
            "type": "auth",
            "access_token": HA_TOKEN
        }))

        auth_reply = json.loads(await ws.recv())
        if auth_reply.get("type") != "auth_ok":
            raise RuntimeError(f"WebSocket auth failed: {auth_reply}")

        await ws.send(json.dumps(command))

        while True:
            reply = json.loads(await ws.recv())
            if reply.get("type") == "result":
                return reply

# -----------------------------------------------------------------------------
# WS fetchers (areas + devices)
# -----------------------------------------------------------------------------
async def fetch_devices_ws():
    result = await ha_ws_call({
        "id": 1,
        "type": "config/device_registry/list",
    })
    return result.get("result", [])

async def fetch_areas_ws():
    result = await ha_ws_call({
        "id": 2,
        "type": "config/area_registry/list",
    })
    return result.get("result", [])

# -----------------------------------------------------------------------------
# API endpoints
# -----------------------------------------------------------------------------
@app.get("/api/overview")
def overview():
    try:
        resp = ha_rest_get("/api/config")
        resp.raise_for_status()
        config = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch overview: {e}")

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

@app.get("/api/entities")
def entities():
    resp = ha_rest_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch entities")
    data = resp.json()
    return {
        "count": len(data),
        "entities": data,
    }

@app.get("/api/automations")
def automations():
    """Fetch all entities and return only automations (working previous method)"""
    resp = ha_rest_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch automations")
    all_states = resp.json()
    automations_list = [s for s in all_states if s.get("entity_id", "").startswith("automation.")]
    return automations_list

@app.get("/api/devices")
async def devices():
    devices = await fetch_devices_ws()
    return {
        "count": len(devices),
        "devices": devices,
    }

@app.get("/api/areas")
async def areas():
    areas = await fetch_areas_ws()
    return {
        "count": len(areas),
        "areas": areas,
    }

@app.get("/api/tasks")
def tasks():
    return []
