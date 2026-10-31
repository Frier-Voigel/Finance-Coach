"""Wispr Flow client-side auth (Person B). The org API key stays here; the browser only gets a short-lived JWT.

WebSocket side verified against https://api-docs.wisprflow.ai/websocket_api (2026-10-31): the browser opens
wss://platform-api.wisprflow.ai/api/v1/dash/client_ws?client_key=Bearer%20<token>, sends {type:"auth"}, then
base64 16 kHz mono int16 wav "append" packets of equal duration, then {type:"commit"}.
NOT verified: the token endpoint below (POST {base}/generate_access_token with Bearer <org key> and body
{client_id, duration_secs, metadata} -> {access_token, expires_in}). That page of the docs was not reachable
when this was written. Check it before relying on it, and keep the text-input fallback working.
"""
from __future__ import annotations

import json
import os
import urllib.request

BASE = "https://platform-api.wisprflow.ai/api/v1/dash"  # docs also mention api.wisprflow.ai; override with WISPR_API_URL


class WisprNotConfigured(RuntimeError):
    """No WISPR_API_KEY: caller should tell the UI to use the text fallback."""


def token_request(api_key: str, client_id: str, duration_secs: int = 3600, base: str = BASE) -> urllib.request.Request:
    body = json.dumps({"client_id": client_id, "duration_secs": duration_secs, "metadata": {}}).encode()
    return urllib.request.Request(
        f"{base}/generate_access_token", data=body, method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )


def client_ws_url(token: str, base: str = BASE) -> str:
    return base.replace("https://", "wss://") + f"/client_ws?client_key=Bearer%20{token}"


def get_client_token(client_id: str, duration_secs: int = 3600, opener=urllib.request.urlopen) -> dict:
    """Body for POST /voice/token."""
    key = os.getenv("WISPR_API_KEY")
    if not key:
        raise WisprNotConfigured("WISPR_API_KEY not set")
    base = os.getenv("WISPR_API_URL", BASE)
    with opener(token_request(key, client_id, duration_secs, base), timeout=10) as r:
        d = json.load(r)
    return {"access_token": d["access_token"], "expires_in": d["expires_in"], "ws_url": client_ws_url(d["access_token"], base)}
