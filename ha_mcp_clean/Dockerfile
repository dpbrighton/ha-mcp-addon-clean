ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install system Python + deps
RUN apk add --no-cache python3 py3-requests

# Create virtualenv (avoids PEP 668 error)
RUN python3 -m venv /opt/venv

RUN /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir fastapi uvicorn starlette

ENV PATH="/opt/venv/bin:$PATH"

COPY ha_mcp_server.py /ha_mcp_server.py
COPY rootfs/ /
