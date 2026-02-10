# MCP Server v1.9.1
# Baseline: Overview, Entities, Devices, Areas, Services, Scripts, Automations, Events, Timers
# Dashboards endpoint now uses WebSocket (full Lovelace configs, read-only)
# No other endpoints altered

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
# WS fetchers
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

async def fetch_events_ws():
    result = await ha_ws_call({
        "id": 3,
        "type": "get_event_types",
    })
    return result.get("result", [])

async def fetch_dashboards_ws():
    """
    Fetch all dashboards via WebSocket. Handles:
      - main Lovelace dashboard
      - additional dashboards if present
      - full config for views, cards, custom cards
    """
    dashboards_out = []

    # Fetch main dashboard (default "lovelace")
    try:
        main_config = await ha_ws_call({"id": 100, "type": "lovelace/config"})
        dashboards_out.append({
            "id": "lovelace",
            "title": main_config.get("title", "Home"),
            "mode": "storage",
            "config": main_config
        })
    except Exception as e:
        log.warning("Failed to fetch main Lovelace dashboard via WS: %s", e)

    # Attempt to fetch additional dashboards if they exist
    dashboards_meta = main_config.get("dashboards", {}) if main_config else {}
    for dashboard_id, meta in dashboards_meta.items():
        try:
            dash_config = await ha_ws_call({
                "id": 101,
                "type": "lovelace/config",
                "dashboard_id": dashboard_id
            })
            dashboards_out.append({
                "id": dashboard_id,
                "title": meta.get("title", dashboard_id),
                "mode": meta.get("mode", "storage"),
                "config": dash_config
            })
        except Exception as e:
            log.warning("Failed to fetch dashboard %s via WS: %s", dashboard_id, e)

    return dashboards_out

# -----------------------------------------------------------------------------
# API endpoints
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
# Dashboards endpoint (v1.9.1, WS)
# -----------------------------------------------------------------------------
@app.get("/api/dashboards")
async def dashboards():
    try:
        dashboards_list = await fetch_dashboards_ws()
        return {"count": len(dashboards_list), "dashboards": dashboards_list}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch dashboards via WS: {e}")
