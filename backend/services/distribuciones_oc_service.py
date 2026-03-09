"""
Servicio de distribuciones de OCs para Flujo de Caja.

Permite guardar distribuciones manuales de OCs pendientes de facturar,
distribuyendo el monto total en múltiples fechas para proyecciones más precisas.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from threading import Lock

from backend.config import settings

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = DATA_DIR / "permissions.db"  # Usar misma BD que permisos

_db_lock = Lock()
_schema_initialized = False


def _get_connection() -> sqlite3.Connection:
    """Obtiene conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DB_FILE, timeout=15)
    conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    """Inicializa el schema de la tabla de distribuciones."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS distribuciones_oc (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            oc_id INTEGER NOT NULL UNIQUE,
            oc_name TEXT NOT NULL,
            proveedor TEXT NOT NULL,
            proveedor_id INTEGER,
            monto_total REAL NOT NULL,
            distribuciones TEXT NOT NULL,  -- JSON: [{"fecha": "2026-03-10", "monto": 3000000}, ...]
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,
            estado TEXT DEFAULT 'activa',  -- activa, facturada_parcial, facturada
            fecha_facturacion TEXT,
            monto_facturado REAL DEFAULT 0
        );
        
        CREATE INDEX IF NOT EXISTS idx_distribuciones_oc_id ON distribuciones_oc(oc_id);
        CREATE INDEX IF NOT EXISTS idx_distribuciones_estado ON distribuciones_oc(estado);
        """
    )
    # Añadir columnas si no existen (migraciones para tablas existentes)
    try:
        conn.execute("ALTER TABLE distribuciones_oc ADD COLUMN estado TEXT DEFAULT 'activa'")
    except sqlite3.OperationalError:
        pass  # Columna ya existe
    try:
        conn.execute("ALTER TABLE distribuciones_oc ADD COLUMN fecha_facturacion TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE distribuciones_oc ADD COLUMN monto_facturado REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()


def _ensure_schema() -> None:
    """Asegura que el schema esté inicializado (solo una vez)."""
    global _schema_initialized
    if _schema_initialized:
        return
    
    with _db_lock:
        if _schema_initialized:
            return
        with _get_connection() as conn:
            _init_schema(conn)
        _schema_initialized = True


# ============================================================================
# CRUD Operations
# ============================================================================

def listar_distribuciones(estado: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Lista distribuciones de OCs, opcionalmente filtradas por estado.
    
    Args:
        estado: 'activa', 'facturada_parcial', 'facturada', o None para todas
    
    Returns:
        Lista de distribuciones con sus detalles
    """
    _ensure_schema()
    
    with _get_connection() as conn:
        if estado:
            cursor = conn.execute(
                """
                SELECT id, oc_id, oc_name, proveedor, proveedor_id, 
                       monto_total, distribuciones, created_at, updated_at, created_by,
                       estado, fecha_facturacion, monto_facturado
                FROM distribuciones_oc
                WHERE estado = ?
                ORDER BY created_at DESC
                """,
                (estado,)
            )
        else:
            cursor = conn.execute(
                """
                SELECT id, oc_id, oc_name, proveedor, proveedor_id, 
                       monto_total, distribuciones, created_at, updated_at, created_by,
                       estado, fecha_facturacion, monto_facturado
                FROM distribuciones_oc
                ORDER BY created_at DESC
                """
            )
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "oc_id": row["oc_id"],
                "oc_name": row["oc_name"],
                "proveedor": row["proveedor"],
                "proveedor_id": row["proveedor_id"],
                "monto_total": row["monto_total"],
                "distribuciones": json.loads(row["distribuciones"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "created_by": row["created_by"],
                "estado": row["estado"] or "activa",
                "fecha_facturacion": row["fecha_facturacion"],
                "monto_facturado": row["monto_facturado"] or 0
            })
        
        return result


def obtener_distribucion(oc_id: int) -> Optional[Dict[str, Any]]:
    """
    Obtiene la distribución de una OC específica.
    
    Args:
        oc_id: ID de la OC en Odoo
        
    Returns:
        Distribución si existe, None si no
    """
    _ensure_schema()
    
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, oc_id, oc_name, proveedor, proveedor_id, 
                   monto_total, distribuciones, created_at, updated_at, created_by,
                   estado, fecha_facturacion, monto_facturado
            FROM distribuciones_oc
            WHERE oc_id = ?
            """,
            (oc_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return {
            "id": row["id"],
            "oc_id": row["oc_id"],
            "oc_name": row["oc_name"],
            "proveedor": row["proveedor"],
            "proveedor_id": row["proveedor_id"],
            "monto_total": row["monto_total"],
            "distribuciones": json.loads(row["distribuciones"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "created_by": row["created_by"],
            "estado": row["estado"] or "activa",
            "fecha_facturacion": row["fecha_facturacion"],
            "monto_facturado": row["monto_facturado"] or 0
        }


def crear_o_actualizar_distribucion(
    oc_id: int,
    oc_name: str,
    proveedor: str,
    monto_total: float,
    distribuciones: List[Dict[str, Any]],
    proveedor_id: Optional[int] = None,
    created_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Crea o actualiza la distribución de una OC.
    
    Args:
        oc_id: ID de la OC en Odoo
        oc_name: Nombre/Número de la OC (ej: "PO00123")
        proveedor: Nombre del proveedor
        monto_total: Monto total de la OC
        distribuciones: Lista de distribuciones [{"fecha": "YYYY-MM-DD", "monto": float}, ...]
        proveedor_id: ID del proveedor en Odoo (opcional)
        created_by: Email/nombre del usuario que crea (opcional)
        
    Returns:
        Distribución creada/actualizada
        
    Raises:
        ValueError: Si la suma de distribuciones no coincide con monto_total
    """
    _ensure_schema()
    
    # Validar que la suma de distribuciones sea igual al monto total
    suma_distribuciones = sum(d.get("monto", 0) for d in distribuciones)
    tolerancia = 1.0  # Tolerancia de $1 por redondeos
    
    if abs(suma_distribuciones - monto_total) > tolerancia:
        raise ValueError(
            f"La suma de distribuciones ({suma_distribuciones:,.0f}) "
            f"no coincide con el monto total ({monto_total:,.0f})"
        )
    
    # Validar formato de fechas
    for d in distribuciones:
        try:
            datetime.strptime(d["fecha"], "%Y-%m-%d")
        except (ValueError, KeyError):
            raise ValueError(f"Fecha inválida en distribución: {d}")
    
    distribuciones_json = json.dumps(distribuciones)
    now = datetime.now().isoformat()
    
    with _get_connection() as conn:
        # Intentar actualizar primero
        cursor = conn.execute(
            """
            UPDATE distribuciones_oc
            SET oc_name = ?, proveedor = ?, proveedor_id = ?, 
                monto_total = ?, distribuciones = ?, updated_at = ?
            WHERE oc_id = ?
            """,
            (oc_name, proveedor, proveedor_id, monto_total, 
             distribuciones_json, now, oc_id)
        )
        
        if cursor.rowcount == 0:
            # No existe, crear nuevo
            conn.execute(
                """
                INSERT INTO distribuciones_oc 
                (oc_id, oc_name, proveedor, proveedor_id, monto_total, 
                 distribuciones, created_at, updated_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (oc_id, oc_name, proveedor, proveedor_id, monto_total,
                 distribuciones_json, now, now, created_by)
            )
        
        conn.commit()
    
    return obtener_distribucion(oc_id)


def eliminar_distribucion(oc_id: int) -> bool:
    """
    Elimina la distribución de una OC.
    
    Args:
        oc_id: ID de la OC en Odoo
        
    Returns:
        True si se eliminó, False si no existía
    """
    _ensure_schema()
    
    with _get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM distribuciones_oc WHERE oc_id = ?",
            (oc_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def obtener_distribuciones_por_ids(oc_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    """
    Obtiene las distribuciones para múltiples OCs de una sola vez.
    Optimizado para uso en el cálculo del flujo de caja.
    
    Args:
        oc_ids: Lista de IDs de OCs
        
    Returns:
        Dict mapeando oc_id -> lista de distribuciones
    """
    if not oc_ids:
        return {}
    
    _ensure_schema()
    
    placeholders = ",".join("?" * len(oc_ids))
    
    with _get_connection() as conn:
        cursor = conn.execute(
            f"""
            SELECT oc_id, distribuciones
            FROM distribuciones_oc
            WHERE oc_id IN ({placeholders})
            """,
            oc_ids
        )
        
        result = {}
        for row in cursor.fetchall():
            result[row["oc_id"]] = json.loads(row["distribuciones"])
        
        return result


# ============================================================================
# Plantillas de Distribución
# ============================================================================

def generar_plantilla_distribucion(
    monto_total: float,
    tipo: str,
    num_cuotas: int,
    fecha_inicio: str,
    intervalo_dias: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Genera una distribución automática basada en plantilla.
    
    Args:
        monto_total: Monto total a distribuir
        tipo: Tipo de plantilla:
            - "cuotas_iguales": Divide en N cuotas iguales
            - "semanal": Una cuota por semana
            - "quincenal": Una cuota cada 15 días
            - "mensual": Una cuota por mes
        num_cuotas: Número de cuotas (para cuotas_iguales)
        fecha_inicio: Fecha de la primera cuota (YYYY-MM-DD)
        intervalo_dias: Intervalo personalizado en días (opcional, override)
        
    Returns:
        Lista de distribuciones sugeridas
    """
    try:
        fecha_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Fecha de inicio inválida: {fecha_inicio}")
    
    # Determinar intervalo según tipo
    if intervalo_dias is not None:
        intervalo = intervalo_dias
    elif tipo == "semanal":
        intervalo = 7
        if num_cuotas <= 0:
            num_cuotas = 4  # Default 4 semanas
    elif tipo == "quincenal":
        intervalo = 15
        if num_cuotas <= 0:
            num_cuotas = 2  # Default 2 quincenas
    elif tipo == "mensual":
        intervalo = 30
        if num_cuotas <= 0:
            num_cuotas = 3  # Default 3 meses
    else:  # cuotas_iguales u otro
        intervalo = 30  # Default mensual
    
    if num_cuotas <= 0:
        raise ValueError("Número de cuotas debe ser mayor a 0")
    
    # Calcular montos
    monto_base = int(monto_total / num_cuotas)
    resto = int(monto_total) - (monto_base * num_cuotas)
    
    distribuciones = []
    for i in range(num_cuotas):
        fecha_cuota = fecha_dt + timedelta(days=i * intervalo)
        
        # Agregar el resto a la primera cuota para que sume exacto
        monto_cuota = monto_base + (resto if i == 0 else 0)
        
        distribuciones.append({
            "fecha": fecha_cuota.strftime("%Y-%m-%d"),
            "monto": monto_cuota
        })
    
    return distribuciones


# ============================================================================
# Gestión de Estados
# ============================================================================

def marcar_como_facturada(
    oc_id: int,
    monto_facturado: Optional[float] = None,
    parcial: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Marca una distribución como facturada (total o parcial).
    
    Args:
        oc_id: ID de la OC en Odoo
        monto_facturado: Monto que ya se facturó (para parciales)
        parcial: Si True, es facturación parcial
        
    Returns:
        Distribución actualizada o None si no existe
    """
    _ensure_schema()
    
    now = datetime.now().isoformat()
    estado = "facturada_parcial" if parcial else "facturada"
    
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE distribuciones_oc
            SET estado = ?, fecha_facturacion = ?, monto_facturado = ?, updated_at = ?
            WHERE oc_id = ?
            """,
            (estado, now, monto_facturado or 0, now, oc_id)
        )
        conn.commit()
        
        if cursor.rowcount == 0:
            return None
    
    return obtener_distribucion(oc_id)


def actualizar_estado_distribuciones(ocs_facturadas_ids: List[int]) -> Dict[str, int]:
    """
    Actualiza el estado de múltiples distribuciones basándose en OCs facturadas.
    
    Args:
        ocs_facturadas_ids: Lista de IDs de OCs que ya tienen factura
        
    Returns:
        Dict con contadores de actualizaciones
    """
    if not ocs_facturadas_ids:
        return {"actualizadas": 0}
    
    _ensure_schema()
    
    now = datetime.now().isoformat()
    placeholders = ",".join("?" * len(ocs_facturadas_ids))
    
    with _get_connection() as conn:
        cursor = conn.execute(
            f"""
            UPDATE distribuciones_oc
            SET estado = 'facturada', fecha_facturacion = ?, updated_at = ?
            WHERE oc_id IN ({placeholders}) AND estado = 'activa'
            """,
            [now, now] + ocs_facturadas_ids
        )
        conn.commit()
        return {"actualizadas": cursor.rowcount}


def obtener_historial(limite: int = 50) -> List[Dict[str, Any]]:
    """
    Obtiene historial de distribuciones facturadas.
    
    Args:
        limite: Máximo de registros a retornar
        
    Returns:
        Lista de distribuciones facturadas
    """
    _ensure_schema()
    
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, oc_id, oc_name, proveedor, proveedor_id, 
                   monto_total, distribuciones, created_at, updated_at, created_by,
                   estado, fecha_facturacion, monto_facturado
            FROM distribuciones_oc
            WHERE estado IN ('facturada', 'facturada_parcial')
            ORDER BY fecha_facturacion DESC
            LIMIT ?
            """,
            (limite,)
        )
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "oc_id": row["oc_id"],
                "oc_name": row["oc_name"],
                "proveedor": row["proveedor"],
                "proveedor_id": row["proveedor_id"],
                "monto_total": row["monto_total"],
                "distribuciones": json.loads(row["distribuciones"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "created_by": row["created_by"],
                "estado": row["estado"],
                "fecha_facturacion": row["fecha_facturacion"],
                "monto_facturado": row["monto_facturado"] or 0
            })
        
        return result


def obtener_estadisticas() -> Dict[str, Any]:
    """
    Obtiene estadísticas de las distribuciones.
    
    Returns:
        Dict con estadísticas de distribuciones
    """
    _ensure_schema()
    
    with _get_connection() as conn:
        # Contar por estado
        cursor = conn.execute(
            """
            SELECT 
                estado,
                COUNT(*) as cantidad,
                SUM(monto_total) as monto_total
            FROM distribuciones_oc
            GROUP BY estado
            """
        )
        rows = cursor.fetchall()
        
        por_estado = {}
        for row in rows:
            estado = row["estado"] or "activa"
            por_estado[estado] = {
                "cantidad": row["cantidad"],
                "monto_total": row["monto_total"] or 0
            }
        
        # Total de cuotas activas próximas (30 días)
        from datetime import date
        fecha_limite = (date.today() + timedelta(days=30)).isoformat()
        
        cursor = conn.execute(
            """
            SELECT distribuciones
            FROM distribuciones_oc
            WHERE estado = 'activa' OR estado IS NULL
            """
        )
        
        cuotas_proximas = 0
        monto_proximas = 0
        for row in cursor.fetchall():
            distribuciones = json.loads(row["distribuciones"])
            for d in distribuciones:
                if d.get("fecha") and d["fecha"] <= fecha_limite:
                    cuotas_proximas += 1
                    monto_proximas += d.get("monto", 0)
        
        return {
            "por_estado": por_estado,
            "cuotas_proximas_30d": cuotas_proximas,
            "monto_proximas_30d": monto_proximas,
            "total_activas": por_estado.get("activa", {}).get("cantidad", 0),
            "total_facturadas": por_estado.get("facturada", {}).get("cantidad", 0)
        }


# ============================================================================
# Limpieza Automática (deprecado - ahora usamos estados)
# ============================================================================

def limpiar_distribuciones_facturadas(oc_ids_facturadas: List[int]) -> int:
    """
    Marca distribuciones de OCs facturadas como 'facturada' en lugar de eliminarlas.
    Mantiene el historial.
    
    Args:
        oc_ids_facturadas: Lista de IDs de OCs que ya tienen factura
        
    Returns:
        Número de distribuciones actualizadas
    """
    if not oc_ids_facturadas:
        return 0
    
    result = actualizar_estado_distribuciones(oc_ids_facturadas)
    return result.get("actualizadas", 0)
