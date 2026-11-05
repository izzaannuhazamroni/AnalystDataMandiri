"""Klien tipis Supabase (REST) memakai httpx dan service-role key.

Hanya dipanggil dari backend; service-role key TIDAK pernah dikirim ke browser.
"""
import time
from typing import Any, Optional
from urllib.parse import quote

import httpx

from . import config

_client = httpx.Client(timeout=60)
_user_cache: dict[str, tuple[float, dict]] = {}
_USER_TTL = 60.0


class SupabaseError(RuntimeError):
    pass


def _headers(extra: Optional[dict] = None) -> dict:
    h = {
        "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
    }
    if extra:
        h.update(extra)
    return h


def _check(resp: httpx.Response) -> None:
    if resp.status_code >= 400:
        raise SupabaseError(f"Supabase {resp.status_code}: {resp.text[:300]}")


def get_user(token: str) -> Optional[dict]:
    """Validasi JWT user lewat Supabase Auth. Mengembalikan {id, email} atau None."""
    now = time.time()
    cached = _user_cache.get(token)
    if cached and now - cached[0] < _USER_TTL:
        return cached[1]
    resp = _client.get(
        f"{config.SUPABASE_URL}/auth/v1/user",
        headers={
            "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {token}",
        },
    )
    if resp.status_code != 200:
        return None
    data = resp.json()
    user = {"id": data.get("id"), "email": data.get("email")}
    if not user["id"]:
        return None
    if len(_user_cache) > 500:
        _user_cache.clear()
    _user_cache[token] = (now, user)
    return user


def download(path: str) -> bytes:
    url = f"{config.SUPABASE_URL}/storage/v1/object/{config.STORAGE_BUCKET}/{quote(path)}"
    resp = _client.get(url, headers=_headers())
    _check(resp)
    return resp.content


def select(table: str, params: dict[str, str]) -> list[dict[str, Any]]:
    resp = _client.get(
        f"{config.SUPABASE_URL}/rest/v1/{table}", headers=_headers(), params=params
    )
    _check(resp)
    return resp.json()


def insert(table: str, rows: list[dict] | dict) -> list[dict[str, Any]]:
    resp = _client.post(
        f"{config.SUPABASE_URL}/rest/v1/{table}",
        headers=_headers({"Prefer": "return=representation"}),
        json=rows,
    )
    _check(resp)
    return resp.json()


def update(table: str, params: dict[str, str], values: dict) -> list[dict[str, Any]]:
    resp = _client.patch(
        f"{config.SUPABASE_URL}/rest/v1/{table}",
        headers=_headers({"Prefer": "return=representation"}),
        params=params,
        json=values,
    )
    _check(resp)
    return resp.json()


def delete(table: str, params: dict[str, str]) -> None:
    resp = _client.delete(
        f"{config.SUPABASE_URL}/rest/v1/{table}", headers=_headers(), params=params
    )
    _check(resp)
