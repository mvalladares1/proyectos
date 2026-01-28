#!/usr/bin/env python3
"""
Script para entender cómo el pallet 039351 entra en la trazabilidad de S00531
"""
import sys
sys.path.insert(0, '/home/feli/proyectos')

from shared.odoo_client import OdooClient
import os

# Configuración
username = os.getenv("ODOO_USERNAME", "frios@riofuturo.cl")
password = os.getenv("ODOO_API_KEY", "413c17f8c0a0ebe211cda26c094c2bbb47fce5c6")

client = OdooClient(username=username, password=password)

print("=" * 80)
print("¿CÓMO ENTRA 039351 EN LA TRAZABILIDAD DE S00531?")
print("=" * 80)

# 1. Obtener picking de S00531
pickings = client.search_read(
    "stock.picking",
    [
        ("origin", "=", "S00531"),
        ("picking_type_id.code", "=", "outgoing"),
        ("state", "=", "done")
    ],
    ["id", "name", "origin"]
)

if not pickings:
    print("❌ No se encontró el picking de S00531")
    sys.exit(1)

picking_id = pickings[0]["id"]
print(f"\n✓ Picking encontrado: {pickings[0]['name']} (ID: {picking_id})")

# 2. Obtener pallets de la venta
sale_moves = client.search_read(
    "stock.move.line",
    [
        ("picking_id", "=", picking_id),
        ("package_id", "!=", False),
        ("qty_done", ">", 0),
        ("state", "=", "done")
    ],
    ["id", "package_id", "product_id", "qty_done"]
)

sale_pallet_ids = set()
for ml in sale_moves:
    pkg = ml.get("package_id")
    if pkg:
        pkg_id = pkg[0] if isinstance(pkg, (list, tuple)) else pkg
        sale_pallet_ids.add(pkg_id)

sale_pallet_names = client.search_read(
    "stock.quant.package",
    [("id", "in", list(sale_pallet_ids))],
    ["id", "name"]
)

print(f"\n✓ Pallets en la venta S00531: {len(sale_pallet_names)}")
sale_name_to_id = {p["name"]: p["id"] for p in sale_pallet_names}

# Verificar si 039351 está en los pallets de venta
pallet_039351_id = sale_name_to_id.get("039351")
if pallet_039351_id:
    print(f"✓ 039351 está directamente en la venta (ID: {pallet_039351_id})")
else:
    print("✗ 039351 NO está directamente en la venta")
    print("\nPallets de la venta:")
    for name in sorted(sale_name_to_id.keys())[:10]:
        print(f"  - {name}")

# 3. Buscar la cadena de conexión desde S00531 a 039351
print("\n" + "=" * 80)
print("BUSCANDO CADENA DE CONEXIÓN:")
print("=" * 80)

# Buscar qué pallet de la venta tiene 039351 como antecedente
print("\nBuscando procesos que consumen pallets de S00531...")

for pallet_name, pallet_id in sorted(sale_name_to_id.items())[:5]:  # Revisar primeros 5
    print(f"\nAnalizando {pallet_name} (ID: {pallet_id})...")
    
    # Buscar procesos donde este pallet es INPUT
    input_moves = client.search_read(
        "stock.move.line",
        [
            ("package_id", "=", pallet_id),
            ("state", "=", "done"),
            ("qty_done", ">", 0)
        ],
        ["id", "reference", "result_package_id", "date"],
        limit=10
    )
    
    if input_moves:
        print(f"  Usado como input en {len(input_moves)} procesos:")
        for move in input_moves:
            result = move.get("result_package_id")
            result_name = result[1] if result else "None"
            print(f"    - {move['reference']}: {pallet_name} -> {result_name}")
    
    # Buscar de dónde viene este pallet (backward 1 nivel)
    output_moves = client.search_read(
        "stock.move.line",
        [
            ("result_package_id", "=", pallet_id),
            ("state", "=", "done"),
            ("qty_done", ">", 0)
        ],
        ["id", "reference", "package_id", "date"],
        order="date desc",
        limit=10
    )
    
    if output_moves:
        print(f"  Origen (como output) en {len(output_moves)} procesos:")
        for move in output_moves:
            pkg = move.get("package_id")
            pkg_name = pkg[1] if pkg else "None (creación)"
            print(f"    - {move['reference']}: {pkg_name} -> {pallet_name} (fecha: {move.get('date', '')[:10]})")
            
            # Si package_id es diferente, seguir un nivel más atrás
            if pkg and pkg[1] != pallet_name:
                parent_id = pkg[0]
                # Buscar origen del padre
                parent_origin = client.search_read(
                    "stock.move.line",
                    [
                        ("result_package_id", "=", parent_id),
                        ("state", "=", "done"),
                        ("qty_done", ">", 0)
                    ],
                    ["id", "reference", "package_id", "date"],
                    order="date desc",
                    limit=5
                )
                
                if parent_origin:
                    print(f"      Nivel -2 ({pkg[1]}):")
                    for pmove in parent_origin:
                        ppkg = pmove.get("package_id")
                        ppkg_name = ppkg[1] if ppkg else "None (creación)"
                        print(f"        - {pmove['reference']}: {ppkg_name} -> {pkg[1]}")
                        
                        # Verificar si llegamos a 039351
                        if ppkg and ppkg[1] == "039351":
                            print(f"          🎯 CONEXIÓN ENCONTRADA A 039351!")

print("\n" + "=" * 80)
