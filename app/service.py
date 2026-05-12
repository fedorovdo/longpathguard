from __future__ import annotations

SERVICE_NAME = "LongPathGuard"
UVICORN_APP = "app.main:app"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8787


def uvicorn_arguments(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> str:
    return f"-m uvicorn {UVICORN_APP} --host {host} --port {port}"
