from fastapi import FastAPI, Header, HTTPException
import requests
import os

app = FastAPI()

HA_URL = "http://supervisor/core/api"
HA_TOKEN = os.environ.get("HA_TOKEN")

headers = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Home Assistant MCP running"
    }

@app.get("/api/tasks")
def get_tasks():
    # Placeholder MCP-style endpoint
    return {
        "tasks": [],
        "status": "idle"
    }
