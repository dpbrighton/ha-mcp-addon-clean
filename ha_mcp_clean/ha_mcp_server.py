import os

# Long-term HA token (unchanged)
HA_TOKEN = os.getenv("HA_TOKEN")

# Ollama connection (new)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

# Example function to send a prompt to Ollama
import requests

def ask_llm(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": "You are controlling Home Assistant."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(f"{OLLAMA_BASE_URL}/v1/chat/completions", json=payload)
    return response.json()
