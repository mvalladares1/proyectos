#!/usr/bin/env python3
"""
¿Está WH/RF/MO/00615 conectado a la cadena de trazabilidad de S00531?
"""
import sys
sys.path.insert(0, '/home/feli/proyectos')

from shared.odoo_client import OdooClient
import os

client = OdooClient(username='frios@riofuturo.cl', password='413c17f8c0a0ebe211cda26c094c2bbb47fce5c6')

print("=" * 80)
print("¿WH/RF/MO/00615 ESTÁ CONECTADO A S00531?")
print("=" * 80)

# 1. Obtener inputs del proceso WH/RF/MO/00615
print("\nInputs de WH/RF/MO/00615:")
mo_inputs = client.search_read(
    "stock.move.line",
    [
        ("reference", "=", "WH/RF/MO/00615"),
        ("state", "=", "done"),
        ("qty_done", ">", 0),
        ("package_id", "!=", False)
    ],
    ["id", "package_id", "result_package_id", "product_id"],
    limit=50
)

input_pallets = set()
for m in mo_inputs:
    pkg = m.get("package_id")
    if pkg:
        input_pallets.add((pkg[0], pkg[1]))

print(f"Total pallets input: {len(input_pallets)}")
for pkg_id, pkg_name in sorted(input_pallets, key=lambda x: x[1]):
    print(f"  - {pkg_name} (ID: {pkg_id})")

# 2. Verificar si alguno de estos inputs está en la venta S00531
if input_pallets:
    print("\n" + "=" * 80)
    print("¿ALGÚN INPUT ESTÁ EN S00531?")
    print("=" * 80)
    
    # Obtener pallets de S00531
    picking = client.search_read(
        "stock.picking",
        [
            ("origin", "=", "S00531"),
            ("picking_type_id.code", "=", "outgoing"),
            ("state", "=", "done")
        ],
        ["id"]
    )[0]
    
    sale_moves = client.search_read(
        "stock.move.line",
        [
            ("picking_id", "=", picking["id"]),
            ("package_id", "!=", False),
            ("qty_done", ">", 0),
            ("state", "=", "done")
        ],
        ["package_id"]
    )
    
    sale_pallets = {m["package_id"][1] for m in sale_moves if m.get("package_id")}
    
    print(f"Pallets en S00531: {len(sale_pallets)}")
    
    # Verificar intersección
    common_pallets = {pkg_name for _, pkg_name in input_pallets if pkg_name in sale_pallets}
    
    if common_pallets:
        print(f"\n✓ CONEXIÓN DIRECTA: {len(common_pallets)} pallets en común:")
        for pkg in sorted(common_pallets):
            print(f"  - {pkg}")
    else:
        print("\n✗ No hay pallets en común entre MO/00615 inputs y S00531")
        print("\nPor lo tanto, 039351 NO DEBERÍA estar en la trazabilidad de S00531")
        print("Debe estar entrando por expansión de hermanos o error en el algoritmo")

# 3. Outputs del proceso
print("\n" + "=" * 80)
print("OUTPUTS DE WH/RF/MO/00615:")
print("=" * 80)

mo_outputs = client.search_read(
    "stock.move.line",
    [
        ("reference", "=", "WH/RF/MO/00615"),
        ("state", "=", "done"),
        ("qty_done", ">", 0),
        ("result_package_id", "!=", False)
    ],
    ["id", "result_package_id"],
    limit=50
)

output_pallets = {m["result_package_id"][1] for m in mo_outputs if m.get("result_package_id")}
print(f"Total pallets output: {len(output_pallets)}")
print(f"Pallets: {', '.join(sorted(output_pallets))}")

# Verificar si los outputs se usan en procesos que SÍ están en la cadena de S00531
print("\n" + "=" * 80)
print("¿LOS OUTPUTS SE USAN EN PROCESOS CONECTADOS A S00531?")
print("=" * 80)

# Buscar procesos que usan 039351 como input (excluyendo RF/INT/)
uses_039351 = client.search_read(
    "stock.move.line",
    [
        ("package_id.name", "=", "039351"),
        ("state", "=", "done"),
        ("qty_done", ">", 0),
        ("reference", "not ilike", "RF/INT/"),
        ("reference", "not ilike", "Quantity Updated")
    ],
    ["id", "reference", "result_package_id"],
    limit=10
)

if uses_039351:
    print(f"Procesos que usan 039351 como input: {len(uses_039351)}")
    for m in uses_039351:
        result = m.get("result_package_id")
        result_name = result[1] if result else "None"
        print(f"  - {m['reference']}: 039351 -> {result_name}")
else:
    print("✗ 039351 no se usa como input en ningún proceso (excluyendo RF/INT/)")
    print("\nCONCLUSIÓN: 039351 es un PALLET MUERTO")
    print("  - Se creó en WH/RF/MO/00615")
    print("  - Solo pasó por RF/INT/00590 (inventario)")
    print("  - Nunca se usó en producción real")
    print("  - NO debería estar en la trazabilidad de S00531")

print("\n" + "=" * 80)
