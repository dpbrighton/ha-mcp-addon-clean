import os
import json
import asyncio
import logging
import requests
import websockets

from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ha-mcp")

app = FastAPI()

# -----------------------------------------------------------------------------
# Global token store (ONE token, reused everywhere)
# -----------------------------------------------------------------------------

HA_TOKEN: str | None = None

HA_HTTP_BASE = "http://homeassistant:8123"
HA_WS_URL = "ws://homeassistant:8123/api/websocket"


# -----------------------------------------------------------------------------
# Startup: load token once and verify it
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

    log.info("✅ Home Assistant token loaded and stored internally")

    # Verify token via REST
    resp = requests.get(
        f"{HA_HTTP_BASE}/api/",
        headers={"Authorization": f"Bearer {HA_TOKEN}"},
        timeout=10,
    )

    log.info("HA connectivity check status: %s", resp.status_code)

    if resp.status_code != 200:
        raise RuntimeError("Home Assistant token failed REST validation")

    log.info("✅ Home Assistant connectivity confirmed")
    log.info("=== MCP STARTUP COMPLETE ===")


# -----------------------------------------------------------------------------
# Helper: WebSocket call wrapper
# -----------------------------------------------------------------------------

async def ha_ws_call(command: dict) -> dict:
    """
    Perform a single authenticated Home Assistant WebSocket call
    """
    assert HA_TOKEN, "HA_TOKEN not initialised"

    async with websockets.connect(HA_WS_URL) as ws:
        # Wait for auth_required
        msg = json.loads(await ws.recv())
        if msg.get("type") != "auth_required":
            raise RuntimeError(f"Unexpected WS message: {msg}")

        # Send auth (THIS WAS THE BUG BEFORE)
        await ws.send(json.dumps({
            "type": "auth",
            "access_token": HA_TOKEN
        }))

        auth_reply = json.loads(await ws.recv())
        if auth_reply.get("type") != "auth_ok":
            raise RuntimeError(f"WebSocket auth failed: {auth_reply}")

        # Send command
        await ws.send(json.dumps(command))

        while True:
            reply = json.loads(await ws.recv())
            if reply.get("type") == "result":
                return reply


# -----------------------------------------------------------------------------
# Device + Area fetchers (WS)
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


@app.get("/api/entities")
def entities():
    resp = requests.get(
        f"{HA_HTTP_BASE}/api/states",
        headers={"Authorization": f"Bearer {HA_TOKEN}"},
        timeout=10,
    )
    return resp.json()


@app.get("/api/automations")
def automations():
    resp = requests.get(
        f"{HA_HTTP_BASE}/api/config/automation/config",
        headers={"Authorization": f"Bearer {HA_TOKEN}"},
        timeout=10,
    )
    return resp.json()


@app.get("/api/tasks")
def tasks():
    return []


@app.get("/api/overview")
def overview():
    return {
        "status": "ok",
        "token_loaded": HA_TOKEN is not None,
    }
