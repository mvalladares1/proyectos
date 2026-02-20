"""
Auditoría de cálculo para partner PATAGONFOODS en Facturas Proyectadas.
Muestra OCs por mes, total USD y conversión a CLP con la misma lógica del backend.
"""
from collections import defaultdict
import xmlrpc.client
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.services.currency_service import CurrencyService

URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"


def main():
    common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    if not uid:
        print("❌ No fue posible autenticar en Odoo")
        return

    models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

    # Buscar partner PATAGONFOODS
    partners = models.execute_kw(
        DB,
        uid,
        PASSWORD,
        "res.partner",
        "search_read",
        [[("name", "ilike", "PATAGONFOODS")]],
        {"fields": ["id", "name"], "limit": 20},
    )

    if not partners:
        print("❌ No se encontró partner PATAGONFOODS")
        return

    partner_ids = [p["id"] for p in partners]
    print("Partners encontrados:")
    for p in partners:
        print(f"  - {p['id']}: {p['name']}")

    orders = models.execute_kw(
        DB,
        uid,
        PASSWORD,
        "sale.order",
        "search_read",
        [[
            ("state", "in", ["draft", "sent"]),
            ("partner_id", "in", partner_ids),
            ("commitment_date", "!=", False),
            ("commitment_date", ">=", "2026-01-01"),
            ("commitment_date", "<=", "2026-12-31"),
        ]],
        {
            "fields": ["name", "partner_id", "amount_total", "currency_id", "commitment_date", "state"],
            "limit": 5000,
        },
    )

    if not orders:
        print("❌ No hay presupuestos draft/sent para PATAGONFOODS en 2026")
        return

    rate = CurrencyService.get_usd_to_clp_rate()
    print(f"\n💱 Tasa USD->CLP usada por backend ahora: {rate:.6f}\n")

    por_mes = defaultdict(lambda: {
        "usd_total": 0.0,
        "clp_total": 0.0,
        "orders": [],
    })

    for order in orders:
        fecha = order.get("commitment_date") or ""
        mes = str(fecha)[:7]
        currency_data = order.get("currency_id") or []
        currency_name = currency_data[1] if isinstance(currency_data, (list, tuple)) and len(currency_data) > 1 else "CLP"
        amount = float(order.get("amount_total") or 0)

        if "USD" in currency_name.upper():
            amount_clp = amount * rate
            por_mes[mes]["usd_total"] += amount
        else:
            amount_clp = amount

        por_mes[mes]["clp_total"] += amount_clp
        por_mes[mes]["orders"].append({
            "name": order.get("name"),
            "amount": amount,
            "currency": currency_name,
            "amount_clp": amount_clp,
            "fecha": fecha,
        })

    print("=" * 100)
    print("RESUMEN PATAGONFOODS POR MES")
    print("=" * 100)
    for mes in sorted(por_mes.keys()):
        info = por_mes[mes]
        print(f"\n{mes}")
        print(f"  USD total: {info['usd_total']:,.2f}")
        print(f"  CLP total: {info['clp_total']:,.0f}")
        for o in sorted(info["orders"], key=lambda x: x["name"]):
            print(
                f"    - {o['name']}: {o['currency']} {o['amount']:,.2f} -> CLP {o['amount_clp']:,.0f} ({o['fecha']})"
            )

    print("\n" + "=" * 100)
    print("TOTAL ANUAL")
    print("=" * 100)
    usd_total = sum(v["usd_total"] for v in por_mes.values())
    clp_total = sum(v["clp_total"] for v in por_mes.values())
    print(f"USD: {usd_total:,.2f}")
    print(f"CLP: {clp_total:,.0f}")


if __name__ == "__main__":
    main()
