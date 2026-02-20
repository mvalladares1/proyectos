"""
Debug/Auditoría de "Facturas Proyectadas (Modulo Compras)" para 1.2.1.

Compara:
1) Lo que devuelve la API de flujo de caja (cuenta proyectadas_compras)
2) Cálculo directo desde Odoo con la misma lógica del backend:
   - purchase.order state = purchase
   - sin factura (invoice_ids vacío y invoice_status != invoiced)
   - fecha proyectada = date_approve + plazo de pago (account.payment.term.line.days máximo)
   - si no hay plazo, usar solo date_approve
   - conversión USD -> CLP con CurrencyService

Uso ejemplo:
python scripts/analisis/debug_proyectadas_compras.py \
  --fecha-inicio 2026-01-01 \
  --fecha-fin 2026-09-30 \
  --modo semanal \
  --api-url http://167.114.114.51:8002 \
  --odoo-url https://riofuturo.server98c6e.oerpondemand.net \
  --odoo-db riofuturo-master \
  --username tu_usuario \
  --password tu_password
"""

from __future__ import annotations

import argparse
import os
import sys
import xmlrpc.client
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import requests

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.services.currency_service import CurrencyService


def periodo_desde_fecha(fecha_yyyy_mm_dd: str, modo: str) -> str:
    if modo == "semanal":
        fecha_dt = datetime.strptime(fecha_yyyy_mm_dd, "%Y-%m-%d")
        iso = fecha_dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    return fecha_yyyy_mm_dd[:7]


def obtener_api_proyectadas(
    api_url: str,
    fecha_inicio: str,
    fecha_fin: str,
    username: str,
    password: str,
    modo: str,
) -> Dict:
    endpoint = "semanal" if modo == "semanal" else "mensual"
    url = f"{api_url.rstrip('/')}/api/v1/flujo-caja/{endpoint}"
    params = {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "username": username,
        "password": password,
        "incluir_proyecciones": True,
    }

    resp = requests.get(url, params=params, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    conceptos = data.get("actividades", {}).get("OPERACION", {}).get("conceptos", [])
    concepto_121 = next((c for c in conceptos if c.get("id") == "1.2.1"), None)
    if not concepto_121:
        return {
            "total": 0.0,
            "montos_por_periodo": {},
            "categorias": {},
            "proveedores": {},
            "encontrado": False,
        }

    cuenta = next((x for x in concepto_121.get("cuentas", []) if x.get("codigo") == "proyectadas_compras"), None)
    if not cuenta:
        return {
            "total": 0.0,
            "montos_por_periodo": {},
            "categorias": {},
            "proveedores": {},
            "encontrado": True,
        }

    categorias = {}
    proveedores = defaultdict(float)

    for etiqueta in cuenta.get("etiquetas", []):
        nombre_categoria = str(etiqueta.get("nombre", "")).replace("📁 ", "").strip() or "Sin Categoría"
        monto_categoria = float(etiqueta.get("monto", 0.0) or 0.0)
        categorias[nombre_categoria] = monto_categoria

        for sub in etiqueta.get("sub_etiquetas", []) or []:
            nombre_proveedor = str(sub.get("nombre", "")).replace("↳", "").strip()
            if nombre_proveedor:
                proveedores[nombre_proveedor] += float(sub.get("monto", 0.0) or 0.0)

    return {
        "total": float(cuenta.get("monto", 0.0) or 0.0),
        "montos_por_periodo": dict(cuenta.get("montos_por_mes", {}) or {}),
        "categorias": categorias,
        "proveedores": dict(proveedores),
        "encontrado": True,
    }


def obtener_calculo_odoo(
    odoo_url: str,
    odoo_db: str,
    username: str,
    password: str,
    fecha_inicio: str,
    fecha_fin: str,
    modo: str,
) -> Dict:
    common = xmlrpc.client.ServerProxy(f"{odoo_url.rstrip('/')}/xmlrpc/2/common")
    uid = common.authenticate(odoo_db, username, password, {})
    if not uid:
        raise RuntimeError("No se pudo autenticar en Odoo")

    models = xmlrpc.client.ServerProxy(f"{odoo_url.rstrip('/')}/xmlrpc/2/object")

    ocs = models.execute_kw(
        odoo_db,
        uid,
        password,
        "purchase.order",
        "search_read",
        [[("state", "=", "purchase")]],
        {
            "fields": [
                "id",
                "name",
                "partner_id",
                "amount_total",
                "currency_id",
                "date_approve",
                "payment_term_id",
                "invoice_ids",
                "invoice_status",
            ],
            "limit": 10000,
        },
    )

    payment_term_ids = []
    partner_ids = []
    for oc in ocs:
        payment_term = oc.get("payment_term_id")
        payment_term_id = payment_term[0] if isinstance(payment_term, (list, tuple)) and payment_term else payment_term
        if payment_term_id:
            payment_term_ids.append(payment_term_id)

        partner = oc.get("partner_id")
        partner_id = partner[0] if isinstance(partner, (list, tuple)) and partner else partner
        if partner_id:
            partner_ids.append(partner_id)

    term_days: Dict[int, int] = {}
    if payment_term_ids:
        term_lines = models.execute_kw(
            odoo_db,
            uid,
            password,
            "account.payment.term.line",
            "search_read",
            [[("payment_id", "in", list(set(payment_term_ids)))]],
            {"fields": ["payment_id", "days"], "limit": 10000},
        )
        for line in term_lines:
            payment_data = line.get("payment_id")
            payment_id = payment_data[0] if isinstance(payment_data, (list, tuple)) and payment_data else payment_data
            if not payment_id:
                continue
            days = int(line.get("days") or 0)
            if payment_id not in term_days or days > term_days[payment_id]:
                term_days[payment_id] = days

    partners_info: Dict[int, Dict[str, str]] = {}
    if partner_ids:
        partners = models.execute_kw(
            odoo_db,
            uid,
            password,
            "res.partner",
            "search_read",
            [[("id", "in", list(set(partner_ids)))]],
            {"fields": ["id", "name", "x_studio_categora_de_contacto"], "limit": 10000},
        )
        for p in partners:
            categoria = p.get("x_studio_categora_de_contacto")
            if isinstance(categoria, (list, tuple)) and categoria:
                categoria = categoria[1]
            if not categoria or categoria == "False":
                categoria = "Sin Categoría"
            partners_info[p["id"]] = {
                "name": p.get("name", "Sin nombre"),
                "categoria": categoria,
            }

    fi = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
    ff = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

    total = 0.0
    por_periodo = defaultdict(float)
    por_categoria = defaultdict(float)
    por_proveedor = defaultdict(float)
    detalle = []

    for oc in ocs:
        invoice_ids = oc.get("invoice_ids") or []
        invoice_status = str(oc.get("invoice_status") or "")
        if invoice_ids or invoice_status == "invoiced":
            continue

        date_approve = str(oc.get("date_approve") or "")[:10]
        if not date_approve:
            continue

        try:
            fecha_base = datetime.strptime(date_approve, "%Y-%m-%d").date()
        except Exception:
            continue

        payment_term = oc.get("payment_term_id")
        payment_term_id = payment_term[0] if isinstance(payment_term, (list, tuple)) and payment_term else payment_term
        days = int(term_days.get(payment_term_id, 0) or 0)
        fecha_proyectada = fecha_base + timedelta(days=days) if days > 0 else fecha_base

        if not (fi <= fecha_proyectada <= ff):
            continue

        period = periodo_desde_fecha(fecha_proyectada.strftime("%Y-%m-%d"), modo)

        amount_total = float(oc.get("amount_total") or 0.0)
        currency_data = oc.get("currency_id")
        currency_name = currency_data[1] if isinstance(currency_data, (list, tuple)) and len(currency_data) > 1 else ""
        if "USD" in str(currency_name).upper():
            amount_total = CurrencyService.convert_usd_to_clp(amount_total)

        monto = -amount_total
        if monto == 0:
            continue

        partner_data = oc.get("partner_id")
        partner_id = partner_data[0] if isinstance(partner_data, (list, tuple)) and partner_data else 0
        partner_name = partner_data[1] if isinstance(partner_data, (list, tuple)) and len(partner_data) > 1 else "Sin proveedor"
        pinfo = partners_info.get(partner_id, {"name": partner_name, "categoria": "Sin Categoría"})

        categoria = pinfo["categoria"]
        total += monto
        por_periodo[period] += monto
        por_categoria[categoria] += monto
        por_proveedor[pinfo["name"]] += monto

        detalle.append(
            {
                "oc": oc.get("name", ""),
                "proveedor": pinfo["name"],
                "categoria": categoria,
                "fecha_base": fecha_base.strftime("%Y-%m-%d"),
                "dias_plazo": days,
                "fecha_proyectada": fecha_proyectada.strftime("%Y-%m-%d"),
                "periodo": period,
                "monto": monto,
            }
        )

    detalle.sort(key=lambda x: abs(x["monto"]), reverse=True)

    return {
        "total": total,
        "montos_por_periodo": dict(por_periodo),
        "categorias": dict(por_categoria),
        "proveedores": dict(por_proveedor),
        "detalle_top": detalle[:30],
    }


def imprimir_diferencias(titulo: str, api_map: Dict[str, float], odoo_map: Dict[str, float], top: int = 20) -> None:
    keys = sorted(set(api_map.keys()) | set(odoo_map.keys()))
    diffs: List[Tuple[str, float, float, float]] = []
    for key in keys:
        a = float(api_map.get(key, 0.0) or 0.0)
        b = float(odoo_map.get(key, 0.0) or 0.0)
        d = a - b
        if abs(d) > 0.5:
            diffs.append((key, a, b, d))

    print(f"\n{'=' * 110}")
    print(titulo)
    print("=" * 110)
    if not diffs:
        print("✅ Sin diferencias relevantes")
        return

    diffs.sort(key=lambda x: abs(x[3]), reverse=True)
    for key, api_v, odoo_v, delta in diffs[:top]:
        print(f"- {key:35s} API={api_v:>18,.2f} | ODOO={odoo_v:>18,.2f} | DELTA={delta:>18,.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Debug de Facturas Proyectadas (Modulo Compras)")
    parser.add_argument("--fecha-inicio", required=True, help="YYYY-MM-DD")
    parser.add_argument("--fecha-fin", required=True, help="YYYY-MM-DD")
    parser.add_argument("--modo", choices=["mensual", "semanal"], default="mensual")
    parser.add_argument("--api-url", default=os.getenv("RF_API_URL", "http://167.114.114.51:8002"))
    parser.add_argument("--odoo-url", default=os.getenv("RF_ODOO_URL", "https://riofuturo.server98c6e.oerpondemand.net"))
    parser.add_argument("--odoo-db", default=os.getenv("RF_ODOO_DB", "riofuturo-master"))
    parser.add_argument("--username", default=os.getenv("RF_USER"), required=os.getenv("RF_USER") is None)
    parser.add_argument("--password", default=os.getenv("RF_PASS"), required=os.getenv("RF_PASS") is None)
    args = parser.parse_args()

    print("=" * 110)
    print("DEBUG FACTURAS PROYECTADAS (MODULO COMPRAS) - 1.2.1")
    print("=" * 110)
    print(f"Rango: {args.fecha_inicio} -> {args.fecha_fin}")
    print(f"Modo : {args.modo}")
    print(f"API  : {args.api_url}")
    print(f"Odoo : {args.odoo_url} | DB: {args.odoo_db}")

    api_data = obtener_api_proyectadas(
        api_url=args.api_url,
        fecha_inicio=args.fecha_inicio,
        fecha_fin=args.fecha_fin,
        username=args.username,
        password=args.password,
        modo=args.modo,
    )

    odoo_data = obtener_calculo_odoo(
        odoo_url=args.odoo_url,
        odoo_db=args.odoo_db,
        username=args.username,
        password=args.password,
        fecha_inicio=args.fecha_inicio,
        fecha_fin=args.fecha_fin,
        modo=args.modo,
    )

    print(f"\nAPI cuenta encontrada: {api_data.get('encontrado', False)}")
    print(f"Total API  : {api_data['total']:,.2f}")
    print(f"Total Odoo : {odoo_data['total']:,.2f}")
    print(f"Delta      : {(api_data['total'] - odoo_data['total']):,.2f}")

    imprimir_diferencias(
        "DIFERENCIAS POR PERIODO",
        api_data.get("montos_por_periodo", {}),
        odoo_data.get("montos_por_periodo", {}),
        top=30,
    )
    imprimir_diferencias(
        "DIFERENCIAS POR CATEGORIA",
        api_data.get("categorias", {}),
        odoo_data.get("categorias", {}),
        top=30,
    )
    imprimir_diferencias(
        "DIFERENCIAS POR PROVEEDOR",
        api_data.get("proveedores", {}),
        odoo_data.get("proveedores", {}),
        top=50,
    )

    print(f"\n{'=' * 110}")
    print("TOP 30 OCs (CÁLCULO ODOO DIRECTO)")
    print("=" * 110)
    for row in odoo_data.get("detalle_top", []):
        print(
            f"- {row['oc']:18s} | {row['proveedor'][:35]:35s} | {row['categoria'][:20]:20s} | "
            f"base={row['fecha_base']} +{row['dias_plazo']:>3d}d => {row['fecha_proyectada']} "
            f"({row['periodo']}) | {row['monto']:>15,.2f}"
        )


if __name__ == "__main__":
    main()
