"""
Servicio de Estado de Resultado
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import re

from shared.odoo_client import OdooClient

# helpers


def _get_odoo_client(username: Optional[str] = None, password: Optional[str] = None) -> OdooClient:
    """Crea cliente Odoo con credenciales del usuario o del .env."""
    return OdooClient(username=username, password=password)


def _build_categoria_template() -> Dict[str, Any]:
    return {
        "1 - INGRESOS": {"total": 0, "subcategorias": {}},
        "2 - COSTOS": {"total": 0, "subcategorias": {}},
        "4 - GASTOS DIRECTOS": {"total": 0, "subcategorias": {}},
        "6 - GAV": {"total": 0, "subcategorias": {}},
        "8 - INTERESES": {"total": 0, "subcategorias": {}},
        "10 - INGRESOS NO OPERACIONALES": {"total": 0, "subcategorias": {}},
        "11 - GASTOS NO OPERACIONALES": {"total": 0, "subcategorias": {}}
    }


def get_cuentas_contables(username: Optional[str] = None, password: Optional[str] = None) -> Any:
    """Consultar accounts de ingresos/egresos y retornarlas."""
    try:
        client = _get_odoo_client(username, password)
        cuentas = client.search_read(
            "account.account",
            [
                ("deprecated", "=", False),
                ("internal_group", "in", ["expense", "income"])
            ],
            [
                "id", "code", "name", "internal_group",
                "x_studio_categora_ifrs", "x_studio_cat_ifrs_2_vf",
                "x_studio_cat_ifrs_3", "x_studio_cat_ifrs_4"
            ]
        )
        return cuentas
    except Exception as exc:
        return {"error": str(exc)}


def get_centros_costo(username: Optional[str] = None, password: Optional[str] = None) -> Any:
    """Retorna los centros de costo (account.analytic.account) activos."""
    try:
        client = _get_odoo_client(username, password)
        centros = client.search_read(
            "account.analytic.account",
            [("plan_id", "=", 41)],
            ["id", "name", "active"]
        )
        return centros
    except Exception as exc:
        return {"error": str(exc)}


def get_movimientos_contables(
    fecha_inicio: str = "2025-01-01",
    fecha_fin: Optional[str] = None,
    limit: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Any:
    try:
        client = _get_odoo_client(username, password)

        cuentas = client.search_read(
            "account.account",
            [
                ("deprecated", "=", False),
                ("internal_group", "in", ["expense", "income"])
            ],
            ["id"]
        )
        cuenta_ids = [c["id"] for c in cuentas]

        domain = [
            ("parent_state", "=", "posted"),
            ("date", ">=", fecha_inicio),
            ("account_id", "in", cuenta_ids)
        ]
        if fecha_fin:
            domain.append(("date", "<=", fecha_fin))

        kwargs: Dict[str, Any] = {
            "fields": ["account_id", "balance:sum", "debit:sum", "credit:sum"],
            "groupby": ["account_id", "date:month"],
            "lazy": False
        }
        if limit:
            kwargs["limit"] = limit

        movimientos = client.models.execute_kw(
            client.db, client.uid, client.password,
            "account.move.line", "read_group",
            [domain], kwargs
        )
        return movimientos
    except Exception as exc:
        return {"error": str(exc)}



def _normalize_account_id(account_id: Any) -> Optional[int]:
    if isinstance(account_id, (list, tuple)) and account_id:
        return account_id[0]
    if isinstance(account_id, int):
        return account_id
    return None


def _mes_from_month_label(label: str) -> Optional[str]:
    meses_es = {
        "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
        "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
        "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
    }
    texto = str(label).lower()
    año = None
    for match in re.finditer(r"(\d{4})", label):
        año = match.group(1)
        break
    for nombre, numero in meses_es.items():
        if nombre in texto:
            if año:
                return f"{año}-{numero}"
            return f"{datetime.now().year}-{numero}"
    return None


def procesar_estado_resultado(movimientos: List[Dict[str, Any]], cuentas: List[Dict[str, Any]]) -> Any:
    estructura = _build_categoria_template()
    datos_mensuales: Dict[str, Dict[str, float]] = {}

    cuentas_dict = {c["id"]: c for c in cuentas}
    cuentas_excluidas = {"52010331", "52060510"}

    for mov in movimientos:
        account_id = _normalize_account_id(mov.get("account_id"))
        if account_id is None:
            continue

        cuenta = cuentas_dict.get(account_id)
        if not cuenta:
            continue

        codigo = str(cuenta.get("code", ""))
        cat_ifrs_1 = (cuenta.get("x_studio_categora_ifrs") or "").strip()
        cat_ifrs_2 = (cuenta.get("x_studio_cat_ifrs_2_vf") or "").strip()
        cat_ifrs_3 = (cuenta.get("x_studio_cat_ifrs_3") or "").strip()

        if not cat_ifrs_2:
            continue
        if codigo in cuentas_excluidas:
            continue

        balance = mov.get("balance", 0) or 0
        primer_digito = codigo[:1]
        monto_eerr = balance * -1 if primer_digito in {"4", "7"} else balance

        categoria_principal = None
        if cat_ifrs_1:
            numero_cat = cat_ifrs_1.split(" ")[0].split("-")[0].strip()
            for key in estructura.keys():
                key_num = key.split(" ")[0].split("-")[0].strip()
                if numero_cat == key_num:
                    categoria_principal = key
                    break
                if cat_ifrs_1 in key or key in cat_ifrs_1:
                    categoria_principal = key
                    break

        if not categoria_principal:
            if codigo.startswith("4"):
                categoria_principal = "1 - INGRESOS"
            elif codigo.startswith("5"):
                categoria_principal = "2 - COSTOS"
            elif codigo.startswith("6"):
                categoria_principal = "6 - GAV"
            elif codigo.startswith("7"):
                categoria_principal = "10 - INGRESOS NO OPERACIONALES"
            elif codigo.startswith("8"):
                categoria_principal = "8 - INTERESES"

        if not categoria_principal or categoria_principal not in estructura:
            continue

        # Mes del movimiento
        fecha_mes = _mes_from_month_label(mov.get("date:month"))

        # --- Nivel 1: Categoría Principal ---
        estructura[categoria_principal]["total"] += monto_eerr
        
        # --- Nivel 2: Subcategoría ---
        subcat = cat_ifrs_2 or "SIN CLASIFICAR"
        nivel2 = estructura[categoria_principal]["subcategorias"].setdefault(subcat, {
            "total": 0,
            "subcategorias": {},
            "montos_por_mes": {}  # NUEVO: Track mensual
        })
        nivel2["total"] += monto_eerr
        
        # Agregar monto mensual a subcategoría
        if fecha_mes:
            nivel2["montos_por_mes"][fecha_mes] = nivel2["montos_por_mes"].get(fecha_mes, 0) + monto_eerr

        # --- Nivel 3: Sub-subcategoría o Cuentas ---
        if cat_ifrs_3:
            nivel3 = nivel2["subcategorias"].setdefault(cat_ifrs_3, {
                "total": 0,
                "cuentas": {},
                "montos_por_mes": {}  # NUEVO: Track mensual
            })
            nivel3["total"] += monto_eerr
            
            # Agregar monto mensual a nivel 3
            if fecha_mes:
                nivel3["montos_por_mes"][fecha_mes] = nivel3["montos_por_mes"].get(fecha_mes, 0) + monto_eerr
            
            # Cuenta individual con tracking mensual
            cuenta_label = f"{codigo} - {cuenta.get('name', '')}"
            if cuenta_label not in nivel3["cuentas"]:
                nivel3["cuentas"][cuenta_label] = {"total": 0, "montos_por_mes": {}}
            nivel3["cuentas"][cuenta_label]["total"] += monto_eerr
            if fecha_mes:
                nivel3["cuentas"][cuenta_label]["montos_por_mes"][fecha_mes] = nivel3["cuentas"][cuenta_label]["montos_por_mes"].get(fecha_mes, 0) + monto_eerr

        # --- Datos mensuales globales (por categoría principal) ---
        if fecha_mes:
            datos_mensuales.setdefault(fecha_mes, {cat: 0 for cat in estructura.keys()})
            datos_mensuales[fecha_mes][categoria_principal] += monto_eerr

    return estructura, datos_mensuales


def calcular_resultados(estructura: Dict[str, Any]) -> Dict[str, float]:
    ingresos = estructura["1 - INGRESOS"]["total"]
    costos = estructura["2 - COSTOS"]["total"]
    gastos_directos = estructura["4 - GASTOS DIRECTOS"]["total"]
    gav = estructura["6 - GAV"]["total"]
    intereses = estructura["8 - INTERESES"]["total"]
    ingresos_no_op = estructura["10 - INGRESOS NO OPERACIONALES"]["total"]
    gastos_no_op = estructura["11 - GASTOS NO OPERACIONALES"]["total"]

    utilidad_bruta = ingresos - costos
    utilidad_operacional = utilidad_bruta - gastos_directos - gav
    resultado_no_operacional = ingresos_no_op - gastos_no_op - intereses
    utilidad_antes_impuestos = utilidad_operacional + resultado_no_operacional

    return {
        "ingresos": ingresos,
        "costos": costos,
        "utilidad_bruta": utilidad_bruta,
        "gastos_directos": gastos_directos,
        "gav": gav,
        "utilidad_operacional": utilidad_operacional,
        "intereses": intereses,
        "ingresos_no_operacionales": ingresos_no_op,
        "gastos_no_operacionales": gastos_no_op,
        "resultado_no_operacional": resultado_no_operacional,
        "utilidad_antes_impuestos": utilidad_antes_impuestos
    }


def get_estado_resultado(
    fecha_inicio: str = "2025-01-01",
    fecha_fin: Optional[str] = None,
    centro_costo: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Dict[str, Any]:
    try:
        cuentas = get_cuentas_contables(username, password)
        if isinstance(cuentas, dict) and "error" in cuentas:
            return cuentas

        centros = get_centros_costo(username, password)
        movimientos = get_movimientos_contables(fecha_inicio, fecha_fin, username=username, password=password)
        if isinstance(movimientos, dict) and "error" in movimientos:
            return movimientos

        estructura, datos_mensuales = procesar_estado_resultado(movimientos, cuentas)
        resultados = calcular_resultados(estructura)

        return {
            "estructura": estructura,
            "resultados": resultados,
            "datos_mensuales": datos_mensuales,
            "centros_costo": centros if not (isinstance(centros, dict) and "error" in centros) else [],
            "total_movimientos": len(movimientos) if isinstance(movimientos, list) else 0,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin or "actual"
        }
    except Exception as exc:
        return {"error": str(exc)}


def get_cuentas_por_categoria() -> Dict[str, Any]:
    return get_cuentas_contables()
