"""Signed, browser-held run context for stateless serverless instances."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from contextvars import ContextVar

from fastapi import HTTPException

run_context: ContextVar[str | None] = ContextVar("run_context", default=None)


def enabled() -> bool:
    return os.environ.get("CORNERSCOUT_STATELESS_RUNS") == "1"


def _key() -> bytes:
    key = os.environ.get("CORNERSCOUT_SESSION_SECRET", "")
    if len(key) < 32:
        raise HTTPException(503, "Secreto de sesiones no configurado")
    return key.encode()


def sign(payload: dict[str, object]) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()
    return body + "." + signature


def verify(token: str) -> dict[str, object]:
    if len(token) > 4096:
        raise HTTPException(404, "Analisis desconocido")
    try:
        body, signature = token.split(".")
        expected = hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if not isinstance(payload, dict):
            raise ValueError("payload")
        return payload
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(404, "Analisis desconocido") from exc
