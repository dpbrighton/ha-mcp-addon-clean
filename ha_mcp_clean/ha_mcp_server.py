import os
import json
import asyncio
import logging
import websockets
import requests
from fastapi import FastAPI

app = FastAPI()
LOG = logging.getLogger("ha-mcp")

# -----------------------------
# Tokens
# -----------------------------
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN")
HA_WS_TOKEN = os.getenv("HA_WS_TOKEN")  # <-- LONG-LIVED TOKEN

if not SUPERVISOR_TOKEN:
    raise RuntimeError("SUPERVISOR_TOKEN not set")

if not HA_WS_TOKEN:
    LOG.warning("HA_WS_TOKEN not set – WebSocket calls will fail")

# -----------------------------
# REST helper (Supervisor)
# -----------------------------
def ha_rest(path: str):
    url = f"http://supervisor/core/api/{path}"
    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json",
    }
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()

# -----------------------------
# WebSocket helpers
# -----------------------------
HA_WS_URL = "ws://homeassistant:8123/api/websocket"

async def ha_ws_call(message: dict):
    async with websockets.connect(HA_WS_URL) as ws:
        # 1. Receive auth_required
        await ws.recv()

        # 2. Send auth (NO 'Bearer')
        await ws.send(json.dumps({
            "type": "auth",
            "access_token": HA_WS_TOKEN
        }))

        auth_resp = json.loads(await ws.recv())
        if auth_resp.get("type") != "auth_ok":
            LOG.error(f"WebSocket auth failed: {auth_resp}")
            return []

        # 3. Send request
        await ws.send(json.dumps(message))

        # 4. Collect result
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("type") == "result":
                return msg.get("result", [])
            if msg.get("type") == "auth_invalid":
                LOG.error(f"WebSocket auth invalid: {msg}")
                return []

# -----------------------------
# API endpoints
# -----------------------------
@app.get("/api/devices")
async def devices():
    devices = await ha_ws_call({
        "id": 1,
        "type": "config/device_registry/list"
    })
    return {
        "count": len(devices),
        "devices": devices
    }

@app.get("/api/areas")
async def areas():
    areas = await ha_ws_call({
        "id": 2,
        "type": "config/area_registry/list"
    })
    return {
        "count": len(areas),
        "areas": areas
    }

@app.get("/api/entities")
def entities():
    data = ha_rest("states")
    return {
        "count": len(data),
        "entities": data
    }
