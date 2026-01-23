#!/usr/bin/env python3
"""
Script para investigar ventas reales en diciembre 2025.
Solo cuenta pickings outgoing con origin que empieza con "S".
"""
import sys
sys.path.insert(0, '/home/feli/proyectos')

from shared.odoo_client import OdooClient
from datetime import datetime
import os

# Configuración
username = os.getenv("ODOO_USERNAME", "apiuser@riofuturo.cl")
password = os.getenv("ODOO_API_KEY", "")

if not password:
    print("Error: Define ODOO_API_KEY en el entorno")
    sys.exit(1)

client = OdooClient(username=username, password=password)

# Buscar pickings de diciembre 2025
print("=" * 80)
print("INVESTIGACIÓN: Ventas en Diciembre 2025")
print("=" * 80)

# Buscar todos los pickings outgoing de diciembre
all_outgoing = client.search_read(
    "stock.picking",
    [
        ("picking_type_id.code", "=", "outgoing"),
        ("state", "=", "done"),
        ("date_done", ">=", "2025-12-01 00:00:00"),
        ("date_done", "<=", "2025-12-31 23:59:59"),
    ],
    ["id", "name", "origin", "date_done", "partner_id"],
    limit=200
)

print(f"\nTotal pickings outgoing: {len(all_outgoing)}")

# Filtrar solo los que tienen origin empezando con "S"
ventas_reales = [p for p in all_outgoing if p.get("origin") and p["origin"].startswith("S")]

print(f"Ventas reales (origin empieza con S): {len(ventas_reales)}")
print("\n" + "=" * 80)
print("VENTAS ENCONTRADAS:")
print("=" * 80)

# Agrupar por origin
ventas_por_origin = {}
for v in ventas_reales:
    origin = v.get("origin", "")
    if origin not in ventas_por_origin:
        ventas_por_origin[origin] = []
    ventas_por_origin[origin].append(v)

print(f"\nTotal códigos de venta únicos: {len(ventas_por_origin)}")
print("\nDetalle por código de venta:")
print("-" * 80)

for origin in sorted(ventas_por_origin.keys()):
    pickings = ventas_por_origin[origin]
    print(f"\n{origin}:")
    for p in pickings:
        partner = p.get("partner_id", [False, ""])[1] if p.get("partner_id") else "Sin partner"
        print(f"  - {p['name']} | {p.get('date_done', '')[:10]} | {partner}")
    
    # Contar pallets de esta venta
    picking_ids = [p["id"] for p in pickings]
    move_lines = client.search_read(
        "stock.move.line",
        [
            ("picking_id", "in", picking_ids),
            ("package_id", "!=", False),
            ("qty_done", ">", 0),
            ("state", "=", "done"),
        ],
        ["package_id"],
        limit=500
    )
    
    package_ids = set()
    for ml in move_lines:
        pkg_rel = ml.get("package_id")
        if pkg_rel:
            pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) else pkg_rel
            if pkg_id:
                package_ids.add(pkg_id)
    
    print(f"  Total pallets: {len(package_ids)}")

print("\n" + "=" * 80)
print("RESUMEN:")
print("=" * 80)
print(f"Pickings outgoing totales: {len(all_outgoing)}")
print(f"Ventas reales (con origin S*): {len(ventas_reales)}")
print(f"Códigos de venta únicos: {len(ventas_por_origin)}")

# Contar pallets totales
all_picking_ids = [p["id"] for p in ventas_reales]
all_move_lines = client.search_read(
    "stock.move.line",
    [
        ("picking_id", "in", all_picking_ids),
        ("package_id", "!=", False),
        ("qty_done", ">", 0),
        ("state", "=", "done"),
    ],
    ["package_id"],
    limit=2000
)

total_packages = set()
for ml in all_move_lines:
    pkg_rel = ml.get("package_id")
    if pkg_rel:
        pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) else pkg_rel
        if pkg_id:
            total_packages.add(pkg_id)

print(f"Total pallets en todas las ventas: {len(total_packages)}")
print("=" * 80)
