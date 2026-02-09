# MCP Server v1.3
# Overview endpoint restored with real Home Assistant environment data
# No other functionality changed from v1.2

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
# WS fetchers (devices + areas)
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
    # Fetch core Home Assistant config
    resp = ha_rest_get("/api/config")
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Failed to fetch Home Assistant config"
        )

    config = resp.json()

    # Fetch all states once for counts
    states_resp = ha_rest_get("/api/states")
    if states_resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Failed to fetch entity states for overview"
        )

    states = states_resp.json()

    entity_count = len(states)
    automation_count = len(
        [s for s in states if s.get("entity_id", "").startswith("automation.")]
    )
    script_count = len(
        [s for s in states if s.get("entity_id", "").startswith("script.")]
    )

    return {
        "home_assistant": {
            "version": config.get("version"),
            "location_name": config.get("name"),
            "time_zone": config.get("time_zone"),
            "unit_system": config.get("unit_system"),
            "installation_type": config.get("installation_type", "unknown"),
        },
        "counts": {
            "entities": entity_count,
            "automations": automation_count,
            "scripts": script_count,
            "devices": 0,
            "areas": 0,
            "dashboards": 0,
        },
    }

@app.get("/api/entities")
def entities():
    resp = ha_rest_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch entities")
    return {
        "count": len(resp.json()),
        "entities": resp.json(),
    }

@app.get("/api/automations")
def automations():
    resp = ha_rest_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch automations")
    all_states = resp.json()
    automations_list = [
        state for state in all_states if state.get("entity_id", "").startswith("automation.")
    ]
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
