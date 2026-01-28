#!/usr/bin/env python3
"""
Simular el domain de exclusión y verificar si RF/INT/ se filtra correctamente
"""
import sys
sys.path.insert(0, '/home/feli/proyectos')

from shared.odoo_client import OdooClient
import os

username = os.getenv("ODOO_USERNAME", "frios@riofuturo.cl")
password = os.getenv("ODOO_API_KEY", "413c17f8c0a0ebe211cda26c094c2bbb47fce5c6")

client = OdooClient(username=username, password=password)

# Simular el domain de exclusión
EXCLUDED_PATTERNS = ["RF/INT/", "Quantity Updated", "Cantidad de producto confirmada"]

exclusion_conditions = []
for pattern in EXCLUDED_PATTERNS:
    exclusion_conditions.append(("reference", "not ilike", pattern))

print("=" * 80)
print("DOMAIN DE EXCLUSIÓN:")
print("=" * 80)
print(exclusion_conditions)

# Buscar moves con pallet de S00531 SIN exclusión
print("\n" + "=" * 80)
print("BÚSQUEDA SIN EXCLUSIÓN:")
print("=" * 80)

moves_no_filter = client.search_read(
    "stock.move.line",
    [
        ("package_id", "=", 22090),  # 037796
        ("state", "=", "done"),
        ("qty_done", ">", 0)
    ],
    ["id", "reference"],
    limit=10
)

print(f"Moves encontrados: {len(moves_no_filter)}")
for m in moves_no_filter:
    print(f"  - Move {m['id']}: {m['reference']}")

# Buscar CON exclusión
print("\n" + "=" * 80)
print("BÚSQUEDA CON EXCLUSIÓN:")
print("=" * 80)

moves_with_filter = client.search_read(
    "stock.move.line",
    [
        ("package_id", "=", 22090),  # 037796
        ("state", "=", "done"),
        ("qty_done", ">", 0)
    ] + exclusion_conditions,
    ["id", "reference"],
    limit=10
)

print(f"Moves encontrados: {len(moves_with_filter)}")
for m in moves_with_filter:
    print(f"  - Move {m['id']}: {m['reference']}")

print("\n" + "=" * 80)
print(f"Sin filtro: {len(moves_no_filter)} moves")
print(f"Con filtro: {len(moves_with_filter)} moves")
print(f"Filtrados: {len(moves_no_filter) - len(moves_with_filter)} moves")
print("=" * 80)
