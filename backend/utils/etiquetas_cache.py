import os
import sqlite3
from datetime import datetime
from typing import Optional, Dict

DB_FILENAME = os.path.join(os.path.dirname(__file__), '..', 'data', 'etiquetas_cache.db')


def _ensure_dir(path: str):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)


def _get_conn():
    _ensure_dir(DB_FILENAME)
    conn = sqlite3.connect(DB_FILENAME, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS etiquetas_impresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER,
            package_name TEXT,
            start_carton INTEGER,
            qty INTEGER,
            orden_name TEXT,
            usuario TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def get_last_used_carton(package_id: int) -> int:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT start_carton, qty FROM etiquetas_impresas WHERE package_id = ? ORDER BY id DESC LIMIT 1",
        (package_id,)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return 0
    return int(row['start_carton']) + int(row['qty']) - 1


def reserve_cartones(package_id: int, package_name: str, qty: int, orden_name: str = '', usuario: str = '') -> Dict:
    """
    Reserva de forma atómica un bloque de `qty` cartones para `package_id`.
    Devuelve el `start_carton` reservado y la cantidad.
    """
    if qty <= 0:
        raise ValueError("qty debe ser mayor que 0")

    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute('BEGIN EXCLUSIVE')
        cur.execute(
            "SELECT start_carton, qty FROM etiquetas_impresas WHERE package_id = ? ORDER BY id DESC LIMIT 1",
            (package_id,)
        )
        row = cur.fetchone()
        if not row:
            last = 0
        else:
            last = int(row['start_carton']) + int(row['qty']) - 1
        start = last + 1

        now = datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO etiquetas_impresas (package_id, package_name, start_carton, qty, orden_name, usuario, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (package_id, package_name, start, qty, orden_name or '', usuario or '', now)
        )
        conn.commit()
        return {"start_carton": start, "qty": qty}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Inicializar DB al importar
init_db()
