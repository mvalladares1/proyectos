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
username = os.getenv("ODOO_USERNAME", "frios@riofuturo.cl")
password = os.getenv("ODOO_API_KEY", "413c17f8c0a0ebe211cda26c094c2bbb47fce5c6")

if not password:
    print("Error: Define ODOO_API_KEY en el entorno")
    sys.exit(1)

client = OdooClient(username=username, password=password)

# Buscar pickings de diciembre 2025
print("=" * 80)
print("INVESTIGACIÓN: Ventas en Diciembre 2025")
print("=" * 80)

# Estrategia correcta: buscar sale.order por date_order
print("\nBuscando órdenes de venta por date_order...")
sale_orders = client.search_read(
    "sale.order",
    [
        ("state", "in", ["sale", "done"]),
        ("date_order", ">=", "2025-12-01 00:00:00"),
        ("date_order", "<=", "2025-12-31 23:59:59"),
    ],
    ["id", "name", "date_order", "partner_id"],
    limit=100
)

print(f"Órdenes de venta encontradas: {len(sale_orders)}")

# Mostrar las órdenes encontradas
print("\n" + "=" * 80)
print("ÓRDENES DE VENTA (sale.order):")
print("=" * 80)
for so in sale_orders:
    partner = so.get("partner_id", [False, ""])[1] if so.get("partner_id") else "Sin partner"
    date = so.get("date_order", "")[:10] if so.get("date_order") else "Sin fecha"
    print(f"{so['name']:15} | {date} | {partner}")

if not sale_orders:
    print("No se encontraron órdenes de venta en diciembre")
    sys.exit(0)

# Obtener los códigos de venta
sale_order_names = [so["name"] for so in sale_orders]

# Buscar pickings outgoing relacionados
print("\n" + "=" * 80)
print(f"Buscando pickings outgoing con origins: {', '.join(sale_order_names[:5])}{'...' if len(sale_order_names) > 5 else ''}")
print("=" * 80)
all_outgoing = client.search_read(
    "stock.picking",
    [
        ("picking_type_id.code", "=", "outgoing"),
        ("state", "=", "done"),
        ("origin", "in", sale_order_names)
    ],
    ["id", "name", "origin", "date_done", "scheduled_date"],
    limit=300
)

print(f"Pickings outgoing encontrados: {len(all_outgoing)}")

# Mostrar los pickings encontrados
print("\n" + "=" * 80)
print("PICKINGS OUTGOING RELACIONADOS:")
print("=" * 80)
for p in all_outgoing[:30]:  # Mostrar primeros 30
    origin = p.get("origin", "Sin origin")
    date_done = p.get("date_done", "")[:10] if p.get("date_done") else "Sin fecha"
    print(f"{p['name']:20} | Origin: {origin:15} | Done: {date_done}")

if len(all_outgoing) > 30:
    print(f"... y {len(all_outgoing) - 30} más")

print(f"\nTotal pickings outgoing: {len(all_outgoing)}")

# Filtrar solo los que tienen origin (debería ser todos en este caso)
ventas_reales = [p for p in all_outgoing if p.get("origin")]

print(f"Pickings con origin: {len(ventas_reales)}")
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
print(f"Órdenes de venta (sale.order) en diciembre: {len(sale_orders)}")
print(f"Pickings outgoing relacionados: {len(all_outgoing)}")
print(f"Códigos de venta únicos (origins): {len(ventas_por_origin)}")

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
