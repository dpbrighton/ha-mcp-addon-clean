# MCP Server v1.9.6
# Baseline: Overview, Entities, Devices, Areas, Services, Scripts, Automations, Events, Timers
# Dashboards endpoint: WS fetch + .storage fallback
# Version: 1.9.6

import os
import json
import logging
import requests
import websockets
import asyncio
from pathlib import Path

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
# Global state
# -----------------------------------------------------------------------------
HA_TOKEN: str | None = None
HA_HTTP_BASE = "http://homeassistant:8123"
HA_WS_URL = "ws://homeassistant:8123/api/websocket"

# v1.9.6 CHANGE: make storage path configurable, default to add-on mount
CONFIG_STORAGE_PATH = os.getenv(
    "HA_STORAGE_PATH",
    "/config/.storage"
)

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
    log.info("Using HA storage path: %s", CONFIG_STORAGE_PATH)
    log.info("=== MCP STARTUP COMPLETE ===")

# -----------------------------------------------------------------------------
# REST helper
# -----------------------------------------------------------------------------
def ha_rest_get(path: str):
    assert HA_TOKEN, "HA_TOKEN not initialised"
    resp = requests.get(
        f"{HA_HTTP_BASE}{path}",
        headers={"Authorization": f"Bearer {HA_TOKEN}"},
        timeout=15,
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
        await ws.send(json.dumps({"type": "auth", "access_token": HA_TOKEN}))
        auth_reply = json.loads(await ws.recv())
        if auth_reply.get("type") != "auth_ok":
            raise RuntimeError(f"WebSocket auth failed: {auth_reply}")
        await ws.send(json.dumps(command))
        while True:
            reply = json.loads(await ws.recv())
            if reply.get("type") == "result":
                return reply

# -----------------------------------------------------------------------------
# WS fetchers
# -----------------------------------------------------------------------------
async def fetch_devices_ws():
    result = await ha_ws_call({"id": 1, "type": "config/device_registry/list"})
    return result.get("result", [])

async def fetch_areas_ws():
    result = await ha_ws_call({"id": 2, "type": "config/area_registry/list"})
    return result.get("result", [])

async def fetch_events_ws():
    result = await ha_ws_call({"id": 3, "type": "get_event_types"})
    return result.get("result", [])

async def fetch_dashboards_ws():
    """
    Fetch all dashboards via WS with correct dashboard IDs.
    Returns list of dashboards or empty if WS fails.
    """
    dashboards_out = []
    try:
        meta_resp = await ha_ws_call({"id": 200, "type": "lovelace/dashboards"})
        dashboards_meta = meta_resp.get("result", {})
    except Exception as e:
        log.warning("WS fetch of dashboard metadata failed: %s", e)
        dashboards_meta = {}

    for dashboard_id, meta in dashboards_meta.items():
        try:
            dash_resp = await ha_ws_call(
                {"id": 201, "type": "lovelace/config", "dashboard_id": dashboard_id}
            )
            dashboards_out.append({
                "id": dashboard_id,
                "title": meta.get("title", dashboard_id),
                "mode": meta.get("mode", "storage"),
                "config": dash_resp
            })
        except Exception as e:
            log.warning("Failed to fetch dashboard %s via WS: %s", dashboard_id, e)

    return dashboards_out

def fetch_dashboards_from_storage():
    """
    Fallback: read all Lovelace dashboard files from configured .storage path
    """
    dashboards_out = []
    path = Path(CONFIG_STORAGE_PATH)
    if not path.exists():
        log.warning(".storage path does not exist: %s", CONFIG_STORAGE_PATH)
        return dashboards_out

    for file in path.glob("lovelace*"):
        try:
            with file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            dashboards_out.append({
                "id": data.get("id", file.stem),
                "title": data.get("title", file.stem),
                "mode": data.get("mode", "storage"),
                "config": data
            })
        except Exception as e:
            log.warning("Failed to read dashboard file %s: %s", file, e)
    return dashboards_out

# -----------------------------------------------------------------------------
# Core API endpoints
# -----------------------------------------------------------------------------
@app.get("/api/overview")
def overview():
    resp = ha_rest_get("/api/config")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch overview data")
    config = resp.json()
    return {
        "home_assistant": {
            "version": config.get("version"),
            "location_name": config.get("name"),
            "time_zone": config.get("time_zone"),
            "unit_system": config.get("unit_system"),
            "installation_type": config.get("installation_type"),
        }
    }

@app.get("/api/entities")
def entities():
    resp = ha_rest_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch entities")
    return {"count": len(resp.json()), "entities": resp.json()}

@app.get("/api/automations")
def automations():
    resp = ha_rest_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch automations")
    return [s for s in resp.json() if s.get("entity_id", "").startswith("automation.")]

@app.get("/api/scripts")
def scripts():
    resp = ha_rest_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch scripts")
    return [s for s in resp.json() if s.get("entity_id", "").startswith("script.")]

@app.get("/api/services")
def services():
    resp = ha_rest_get("/api/services")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch services")
    return resp.json()

@app.get("/api/devices")
async def devices():
    devices = await fetch_devices_ws()
    return {"count": len(devices), "devices": devices}

@app.get("/api/areas")
async def areas():
    areas = await fetch_areas_ws()
    return {"count": len(areas), "areas": areas}

@app.get("/api/events")
async def events():
    events = await fetch_events_ws()
    return {"count": len(events), "events": sorted(events)}

@app.get("/api/timers")
def timers():
    resp = ha_rest_get("/api/states")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch timers")
    timers = [s for s in resp.json() if s.get("entity_id", "").startswith("timer.")]
    return {"count": len(timers), "timers": timers}

# -----------------------------------------------------------------------------
# Dashboards endpoint (v1.9.6)
# -----------------------------------------------------------------------------
@app.get("/api/dashboards")
async def dashboards():
    try:
        dashboards_list = await fetch_dashboards_ws()
        if not dashboards_list:
            dashboards_list = fetch_dashboards_from_storage()
        return {"count": len(dashboards_list), "dashboards": dashboards_list}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch dashboards: {e}")
