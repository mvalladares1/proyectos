"""
Debug focalizado por proveedor para "Facturas Proyectadas (Modulo Compras)".

Valida montos semanales de un proveedor comparando:
- Cálculo directo Odoo (misma lógica backend)
- API semanal 1.2.1 > proyectadas_compras > categoría > proveedor
"""

import argparse
import os
import sys
import xmlrpc.client
from collections import defaultdict
from datetime import datetime, timedelta

import requests

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.services.currency_service import CurrencyService


def week_period(fecha):
    iso = fecha.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def normalize(text):
    return " ".join(str(text or "").strip().upper().split())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fecha-inicio", required=True)
    parser.add_argument("--fecha-fin", required=True)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--odoo-url", required=True)
    parser.add_argument("--odoo-db", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--proveedor", required=True, help="Texto del proveedor a buscar (contains)")
    args = parser.parse_args()

    fi = datetime.strptime(args.fecha_inicio, "%Y-%m-%d").date()
    ff = datetime.strptime(args.fecha_fin, "%Y-%m-%d").date()
    proveedor_target = normalize(args.proveedor)

    api_resp = requests.get(
        f"{args.api_url.rstrip('/')}/api/v1/flujo-caja/semanal",
        params={
            "fecha_inicio": args.fecha_inicio,
            "fecha_fin": args.fecha_fin,
            "username": args.username,
            "password": args.password,
            "incluir_proyecciones": True,
        },
        timeout=120,
    )
    api_resp.raise_for_status()
    data = api_resp.json()
    conceptos = data.get("actividades", {}).get("OPERACION", {}).get("conceptos", [])
    c121 = next((c for c in conceptos if c.get("id") == "1.2.1"), {})
    cuenta = next((x for x in c121.get("cuentas", []) if x.get("codigo") == "proyectadas_compras"), {})

    api_supplier_week = defaultdict(float)
    api_supplier_name = None
    api_cat_name = None

    for cat in cuenta.get("etiquetas", []) or []:
        cat_name = str(cat.get("nombre", "")).replace("📁 ", "").strip()
        for sub in cat.get("sub_etiquetas", []) or []:
            sup_name = str(sub.get("nombre", "")).replace("↳", "").strip()
            if proveedor_target in normalize(sup_name):
                api_supplier_name = sup_name
                api_cat_name = cat_name
                for week, val in (sub.get("montos_por_mes", {}) or {}).items():
                    api_supplier_week[week] += float(val or 0.0)

    common = xmlrpc.client.ServerProxy(f"{args.odoo_url.rstrip('/')}/xmlrpc/2/common")
    uid = common.authenticate(args.odoo_db, args.username, args.password, {})
    if not uid:
        raise RuntimeError("No se pudo autenticar en Odoo")
    models = xmlrpc.client.ServerProxy(f"{args.odoo_url.rstrip('/')}/xmlrpc/2/object")

    ocs = models.execute_kw(
        args.odoo_db,
        uid,
        args.password,
        "purchase.order",
        "search_read",
        [[("state", "=", "purchase")]],
        {
            "fields": [
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

    pt_ids = []
    for oc in ocs:
        pt = oc.get("payment_term_id")
        pt_id = pt[0] if isinstance(pt, (list, tuple)) and pt else pt
        if pt_id:
            pt_ids.append(pt_id)

    term_days = {}
    if pt_ids:
        lines = models.execute_kw(
            args.odoo_db,
            uid,
            args.password,
            "account.payment.term.line",
            "search_read",
            [[("payment_id", "in", list(set(pt_ids)))]],
            {"fields": ["payment_id", "days"], "limit": 10000},
        )
        for ln in lines:
            pd = ln.get("payment_id")
            pid = pd[0] if isinstance(pd, (list, tuple)) and pd else pd
            if not pid:
                continue
            d = int(ln.get("days") or 0)
            if pid not in term_days or d > term_days[pid]:
                term_days[pid] = d

    odoo_supplier_week = defaultdict(float)
    odoo_detail = []
    matched_provider_name = None

    for oc in ocs:
        if (oc.get("invoice_ids") or []) or str(oc.get("invoice_status") or "") == "invoiced":
            continue

        date_approve = str(oc.get("date_approve") or "")[:10]
        if not date_approve:
            continue

        try:
            base = datetime.strptime(date_approve, "%Y-%m-%d").date()
        except Exception:
            continue

        pt = oc.get("payment_term_id")
        pt_id = pt[0] if isinstance(pt, (list, tuple)) and pt else pt
        days = int(term_days.get(pt_id, 0) or 0)
        proj = base + timedelta(days=days) if days > 0 else base
        if not (fi <= proj <= ff):
            continue

        partner = oc.get("partner_id")
        provider_name = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else "Sin proveedor"
        if proveedor_target not in normalize(provider_name):
            continue

        matched_provider_name = provider_name
        period = week_period(proj)
        amount = float(oc.get("amount_total") or 0.0)
        currency = oc.get("currency_id")
        currency_name = currency[1] if isinstance(currency, (list, tuple)) and len(currency) > 1 else ""
        if "USD" in normalize(currency_name):
            amount = CurrencyService.convert_usd_to_clp(amount)

        monto = -amount
        odoo_supplier_week[period] += monto
        odoo_detail.append(
            {
                "oc": oc.get("name", ""),
                "period": period,
                "monto": monto,
                "date_approve": base.strftime("%Y-%m-%d"),
                "days": days,
                "fecha_proyectada": proj.strftime("%Y-%m-%d"),
            }
        )

    print("=" * 100)
    print(f"PROVEEDOR BUSCADO: {args.proveedor}")
    print(f"API match  : {api_supplier_name or 'NO ENCONTRADO'}")
    print(f"Odoo match : {matched_provider_name or 'NO ENCONTRADO'}")
    print(f"Categoria API: {api_cat_name or 'N/A'}")
    print("=" * 100)

    all_weeks = sorted(set(odoo_supplier_week.keys()) | set(api_supplier_week.keys()))
    print("\nComparación por semana (API proveedor vs Odoo proveedor):")
    for wk in all_weeks:
        a = float(api_supplier_week.get(wk, 0.0) or 0.0)
        b = float(odoo_supplier_week.get(wk, 0.0) or 0.0)
        d = a - b
        print(f"- {wk}: API={a:>15,.2f} | ODOO={b:>15,.2f} | DELTA={d:>15,.2f}")

    print("\nDetalle OCs Odoo del proveedor:")
    odoo_detail.sort(key=lambda x: (x["period"], -abs(x["monto"])))
    for row in odoo_detail:
        print(
            f"- {row['period']} | {row['oc']:12s} | {row['monto']:>15,.2f} | "
            f"approve={row['date_approve']} +{row['days']}d => {row['fecha_proyectada']}"
        )


if __name__ == "__main__":
    main()
