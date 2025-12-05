"""Servicio de permisos para dashboards."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from backend.config import settings
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PERMISSIONS_FILE = DATA_DIR / "permissions.json"

DEFAULT_PERMISSIONS: Dict[str, Any] = {
    "dashboards": {
        "estado_resultado": ["jvidaurre@riofuturo.cl"],
        "permisos": ["mvalladares@riofuturo.cl"]
    },
    "admins": ["mvalladares@riofuturo.cl"]
}


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_dashboard(slug: str) -> str:
    return slug.strip().lower()


def _ensure_file() -> None:
    if not PERMISSIONS_FILE.exists():
        _write_permissions(DEFAULT_PERMISSIONS)


def _read_permissions() -> Dict[str, Any]:
    _ensure_file()
    try:
        with PERMISSIONS_FILE.open("r", encoding="utf-8") as handler:
            data: Dict[str, Any] = json.load(handler)
    except json.JSONDecodeError:
        data = DEFAULT_PERMISSIONS.copy()
    data.setdefault("dashboards", {})
    data.setdefault("admins", [])
    return data


def _write_permissions(data: Dict[str, Any]) -> None:
    with PERMISSIONS_FILE.open("w", encoding="utf-8") as handler:
        json.dump(data, handler, ensure_ascii=False, indent=2)


def get_permissions_map() -> Dict[str, List[str]]:
    return _read_permissions()["dashboards"].copy()


def get_admins() -> List[str]:
    return _read_permissions().get("admins", [])


def is_admin(email: str) -> bool:
    normalized = _normalize_email(email)
    allowed = { _normalize_email(item) for item in settings.PERMISSION_ADMINS }
    allowed.update(_normalize_email(item) for item in get_admins())
    return normalized in allowed


def get_allowed_dashboards(email: str) -> List[str]:
    """
    Retorna los dashboards que el usuario puede ver.
    - Si un dashboard tiene lista vacía [] → es público (todos pueden ver)
    - Si tiene correos específicos → solo esos correos pueden ver
    - Admins pueden ver todo
    """
    normalized = _normalize_email(email)
    dashboards = get_permissions_map()
    
    # Admins pueden ver todo
    if is_admin(email):
        return list(dashboards.keys())
    
    allowed: List[str] = []
    for slug, emails in dashboards.items():
        # Lista vacía = público
        if not emails:
            allowed.append(slug)
        # Lista con correos = restringido
        elif normalized in {_normalize_email(addr) for addr in emails}:
            allowed.append(slug)
    return allowed


def assign_dashboard(slug: str, email: str) -> Dict[str, List[str]]:
    data = _read_permissions()
    slug_key = _normalize_dashboard(slug)
    dashboards = data.setdefault("dashboards", {})
    bucket = dashboards.setdefault(slug_key, [])
    normalized_email = _normalize_email(email)
    if normalized_email not in {_normalize_email(addr) for addr in bucket}:
        bucket.append(email.strip())
    _write_permissions(data)
    return dashboards.copy()


def remove_dashboard(slug: str, email: str) -> Dict[str, List[str]]:
    data = _read_permissions()
    slug_key = _normalize_dashboard(slug)
    dashboards = data.setdefault("dashboards", {})
    bucket = dashboards.get(slug_key, [])
    normalized_email = _normalize_email(email)
    dashboards[slug_key] = [addr for addr in bucket if _normalize_email(addr) != normalized_email]
    _write_permissions(data)
    return dashboards.copy()


def get_full_permissions() -> Dict[str, Any]:
    return _read_permissions()
