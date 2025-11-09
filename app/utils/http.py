import httpx
from app.config import settings


def get_http_client(timeout: float | None = None) -> httpx.Client:
    return httpx.Client(timeout=timeout or settings.REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": "mobility-context-mvp/1.0"})


def get_async_http_client(timeout: float | None = None) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=timeout or settings.REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": "mobility-context-mvp/1.0"})

