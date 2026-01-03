"""UI utilities."""

import os

import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def api_get(endpoint: str):
    """GET API request."""
    try:
        response = httpx.get(f"{API_BASE_URL}{endpoint}", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def api_post(endpoint: str, data: dict):
    """POST API request."""
    try:
        response = httpx.post(f"{API_BASE_URL}{endpoint}", json=data, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}
