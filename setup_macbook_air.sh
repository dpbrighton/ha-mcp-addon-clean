#!/bin/zsh
# Run this on the MacBook Air to match the Mac Mini setup for the HA MCP client.

set -e

echo "=== HA MCP Client Setup for MacBook Air ==="

# 1. Ensure the Claud directory exists
mkdir -p ~/Documents/Claud

# 2. Clone or update the repo
REPO_DIR=~/Documents/Claud/ha-mcp-addon-clean
if [ -d "$REPO_DIR/.git" ]; then
  echo "Repo already exists — pulling latest..."
  git -C "$REPO_DIR" pull
else
  echo "Cloning repo..."
  git clone https://github.com/dpbrighton/ha-mcp-addon-clean.git "$REPO_DIR"
fi

# 3. Install the mcp Python package
echo "Installing mcp Python package..."
pip3 install --break-system-packages mcp 2>/dev/null || pip3 install mcp

# 4. Register the MCP server with Claude Code globally
echo "Registering home-assistant MCP server with Claude Code..."
claude mcp add --scope user home-assistant python3 \
  "$REPO_DIR/ha_mcp_client.py" 2>/dev/null \
  && echo "Registered successfully." \
  || echo "Already registered (or claude CLI not found — install Claude Code first)."

echo ""
echo "=== Done ==="
echo "Restart Claude Code on this machine and the Home Assistant tools will be available."
