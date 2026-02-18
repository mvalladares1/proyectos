"""
Genera 3 ejemplos claros para validar "Facturas Proyectadas (Modulo Compras)"
comparando Odoo vs API (vista semanal).
"""

import argparse
import os
import sys
import xmlrpc.client
from datetime import datetime, timedelta

import requests

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.services.currency_service import CurrencyService


def week_period(fecha):
    iso = fecha.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fecha-inicio", required=True)
    parser.add_argument("--fecha-fin", required=True)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--odoo-url", required=True)
    parser.add_argument("--odoo-db", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    fi = datetime.strptime(args.fecha_inicio, "%Y-%m-%d").date()
    ff = datetime.strptime(args.fecha_fin, "%Y-%m-%d").date()

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
    api_data = api_resp.json()
    conceptos = api_data.get("actividades", {}).get("OPERACION", {}).get("conceptos", [])
    c121 = next((x for x in conceptos if x.get("id") == "1.2.1"), {})
    cuenta = next((x for x in c121.get("cuentas", []) if x.get("codigo") == "proyectadas_compras"), {})
    api_period_total = cuenta.get("montos_por_mes", {}) or {}
    api_cat_period = {}
    for cat in cuenta.get("etiquetas", []) or []:
        cat_name = str(cat.get("nombre", "")).replace("📁 ", "").strip() or "Sin Categoría"
        api_cat_period[cat_name] = cat.get("montos_por_mes", {}) or {}

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

    payment_term_ids = []
    partner_ids = []
    for oc in ocs:
        pt = oc.get("payment_term_id")
        pt_id = pt[0] if isinstance(pt, (list, tuple)) and pt else pt
        if pt_id:
            payment_term_ids.append(pt_id)

        partner = oc.get("partner_id")
        partner_id = partner[0] if isinstance(partner, (list, tuple)) and partner else partner
        if partner_id:
            partner_ids.append(partner_id)

    term_days = {}
    if payment_term_ids:
        lines = models.execute_kw(
            args.odoo_db,
            uid,
            args.password,
            "account.payment.term.line",
            "search_read",
            [[("payment_id", "in", list(set(payment_term_ids)))]],
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

    partners_map = {}
    if partner_ids:
        partners = models.execute_kw(
            args.odoo_db,
            uid,
            args.password,
            "res.partner",
            "search_read",
            [[("id", "in", list(set(partner_ids)))]],
            {"fields": ["id", "name", "x_studio_categora_de_contacto"], "limit": 10000},
        )
        for p in partners:
            cat = p.get("x_studio_categora_de_contacto")
            if isinstance(cat, (list, tuple)) and cat:
                cat = cat[1]
            if not cat or cat == "False":
                cat = "Sin Categoría"
            partners_map[p["id"]] = {
                "name": p.get("name", "Sin nombre"),
                "cat": cat,
            }

    rows = []
    for oc in ocs:
        if (oc.get("invoice_ids") or []) or str(oc.get("invoice_status") or "") == "invoiced":
            continue

        date_approve = str(oc.get("date_approve") or "")[:10]
        if not date_approve:
            continue

        try:
            fecha_base = datetime.strptime(date_approve, "%Y-%m-%d").date()
        except Exception:
            continue

        pt = oc.get("payment_term_id")
        pt_id = pt[0] if isinstance(pt, (list, tuple)) and pt else pt
        dias = int(term_days.get(pt_id, 0) or 0)
        fecha_proyectada = fecha_base + timedelta(days=dias) if dias > 0 else fecha_base

        if not (fi <= fecha_proyectada <= ff):
            continue

        period = week_period(fecha_proyectada)

        amount = float(oc.get("amount_total") or 0.0)
        currency = oc.get("currency_id")
        currency_name = currency[1] if isinstance(currency, (list, tuple)) and len(currency) > 1 else ""
        if "USD" in str(currency_name).upper():
            amount = CurrencyService.convert_usd_to_clp(amount)

        monto = -amount
        if monto == 0:
            continue

        partner = oc.get("partner_id")
        partner_id = partner[0] if isinstance(partner, (list, tuple)) and partner else 0
        pinfo = partners_map.get(
            partner_id,
            {
                "name": partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else "Sin proveedor",
                "cat": "Sin Categoría",
            },
        )

        rows.append(
            {
                "oc": oc.get("name", ""),
                "proveedor": pinfo["name"],
                "categoria": pinfo["cat"],
                "base": fecha_base.strftime("%Y-%m-%d"),
                "dias": dias,
                "proyectada": fecha_proyectada.strftime("%Y-%m-%d"),
                "semana": period,
                "monto": monto,
            }
        )

    rows.sort(key=lambda x: abs(x["monto"]), reverse=True)

    selected = []
    seen = set()
    for r in rows:
        key = (r["semana"], r["categoria"])
        if key in seen:
            continue
        selected.append(r)
        seen.add(key)
        if len(selected) == 3:
            break

    print("=" * 100)
    print("3 EJEMPLOS CLAROS PARA VALIDAR EN DASHBOARD VS ODOO")
    print("=" * 100)

    if not selected:
        print("No se encontraron ejemplos en el rango indicado")
        return

    for idx, e in enumerate(selected, 1):
        semana = e["semana"]
        cat = e["categoria"]
        api_total_semana = float(api_period_total.get(semana, 0.0) or 0.0)
        api_categoria_semana = float((api_cat_period.get(cat, {}) or {}).get(semana, 0.0) or 0.0)

        print(f"\nEjemplo {idx}")
        print(f"- OC: {e['oc']}")
        print(f"- Proveedor: {e['proveedor']}")
        print(f"- Categoría: {cat}")
        print(f"- Date approve: {e['base']} | Plazo: {e['dias']} días | Fecha proyectada: {e['proyectada']}")
        print(f"- Semana dashboard: {semana}")
        print(f"- Monto OC (Odoo directo): {e['monto']:,.2f}")
        print(f"- API estado proyectadas_compras en {semana}: {api_total_semana:,.2f}")
        print(f"- API categoría {cat} en {semana}: {api_categoria_semana:,.2f}")


if __name__ == "__main__":
    main()
