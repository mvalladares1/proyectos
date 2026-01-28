#!/usr/bin/env python3
"""
Script para investigar por qué el pallet 039351 se marca como SIN_ORIGEN
cuando en realidad tiene origen WH/RF/MO/00615
"""
import sys
sys.path.insert(0, '/home/feli/proyectos')

from shared.odoo_client import OdooClient
import os

# Configuración
username = os.getenv("ODOO_USERNAME", "frios@riofuturo.cl")
password = os.getenv("ODOO_API_KEY", "413c17f8c0a0ebe211cda26c094c2bbb47fce5c6")

client = OdooClient(username=username, password=password)

# Buscar el pallet 039351
print("=" * 80)
print("INVESTIGANDO PALLET: 039351")
print("=" * 80)

# Primero, buscar el paquete
packages = client.search_read(
    "stock.quant.package",
    [("name", "=", "039351")],
    ["id", "name"]
)

if not packages:
    print("❌ No se encontró el pallet 039351")
    sys.exit(1)

pallet_id = packages[0]["id"]
print(f"\n✓ Pallet encontrado: ID={pallet_id}, Name={packages[0]['name']}")

# Buscar TODOS los moves donde este pallet aparece como result_package_id
print("\n" + "=" * 80)
print("MOVES DONDE 039351 ES RESULT_PACKAGE_ID (OUTPUT):")
print("=" * 80)

output_moves = client.search_read(
    "stock.move.line",
    [
        ("result_package_id", "=", pallet_id),
        ("state", "=", "done")
    ],
    ["id", "reference", "package_id", "result_package_id", "date", "product_id", "qty_done"],
    limit=100
)

print(f"\nTotal moves como output: {len(output_moves)}")

if output_moves:
    print("\nDetalles de cada move:")
    print("-" * 80)
    for move in output_moves:
        pkg_input = move.get("package_id")
        pkg_input_name = pkg_input[1] if pkg_input else "None (vacío)"
        product = move.get("product_id", [False, ""])[1] if move.get("product_id") else "Sin producto"
        date = move.get("date", "")[:19] if move.get("date") else "Sin fecha"
        ref = move.get("reference", "Sin referencia")
        
        print(f"\nMove ID: {move['id']}")
        print(f"  Referencia: {ref}")
        print(f"  Package ID (input): {pkg_input_name}")
        print(f"  Result Package ID (output): {move['result_package_id'][1]}")
        print(f"  Fecha: {date}")
        print(f"  Producto: {product}")
        print(f"  Cantidad: {move['qty_done']}")

# Buscar moves donde este pallet aparece como package_id (input)
print("\n" + "=" * 80)
print("MOVES DONDE 039351 ES PACKAGE_ID (INPUT):")
print("=" * 80)

input_moves = client.search_read(
    "stock.move.line",
    [
        ("package_id", "=", pallet_id),
        ("state", "=", "done")
    ],
    ["id", "reference", "package_id", "result_package_id", "date", "product_id", "qty_done"],
    limit=100
)

print(f"\nTotal moves como input: {len(input_moves)}")

if input_moves:
    print("\nDetalles de cada move:")
    print("-" * 80)
    for move in input_moves:
        result_pkg = move.get("result_package_id")
        result_pkg_name = result_pkg[1] if result_pkg else "None"
        product = move.get("product_id", [False, ""])[1] if move.get("product_id") else "Sin producto"
        date = move.get("date", "")[:19] if move.get("date") else "Sin fecha"
        ref = move.get("reference", "Sin referencia")
        
        print(f"\nMove ID: {move['id']}")
        print(f"  Referencia: {ref}")
        print(f"  Package ID (input): {move['package_id'][1]}")
        print(f"  Result Package ID (output): {result_pkg_name}")
        print(f"  Fecha: {date}")
        print(f"  Producto: {product}")
        print(f"  Cantidad: {move['qty_done']}")

# Análisis
print("\n" + "=" * 80)
print("ANÁLISIS:")
print("=" * 80)

if output_moves:
    print(f"\n✓ El pallet 039351 SÍ aparece como output en {len(output_moves)} moves")
    
    # Agrupar por referencia
    refs = {}
    for move in output_moves:
        ref = move.get("reference", "Sin referencia")
        if ref not in refs:
            refs[ref] = []
        refs[ref].append(move)
    
    print(f"\nReferencias únicas donde es output: {len(refs)}")
    for ref, moves in refs.items():
        empty_input = sum(1 for m in moves if not m.get("package_id"))
        with_input = len(moves) - empty_input
        print(f"  - {ref}: {len(moves)} moves ({empty_input} con package_id vacío, {with_input} con package_id)")
    
    # Identificar el proceso de "creación" (package_id vacío)
    creation_moves = [m for m in output_moves if not m.get("package_id")]
    if creation_moves:
        print(f"\n✓ Moves de CREACIÓN (package_id vacío): {len(creation_moves)}")
        for move in creation_moves:
            print(f"  - {move['reference']} (Move ID: {move['id']}) - Fecha: {move.get('date', '')[:19]}")
    
    # Identificar procesos de "modificación" (package_id = result_package_id o diferente)
    modification_moves = [m for m in output_moves if m.get("package_id")]
    if modification_moves:
        print(f"\n✓ Moves de MODIFICACIÓN (package_id presente): {len(modification_moves)}")
        for move in modification_moves:
            pkg_input = move.get("package_id", [False, ""])[1] if move.get("package_id") else ""
            pkg_output = move.get("result_package_id", [False, ""])[1] if move.get("result_package_id") else ""
            if pkg_input == pkg_output:
                tipo = "AUTO-MODIFICACIÓN"
            else:
                tipo = "TRANSFORMACIÓN"
            print(f"  - {move['reference']} ({tipo}) (Move ID: {move['id']}) - Fecha: {move.get('date', '')[:19]}")
else:
    print("\n❌ PROBLEMA: El pallet 039351 NO aparece como output en ningún move")
    print("Esto explica por qué se marca como SIN_ORIGEN")
    print("\nPero según tu búsqueda manual, sí existe en WH/RF/MO/00615")
    print("Posibles causas:")
    print("  1. El move no está en estado 'done'")
    print("  2. El pallet tiene otro ID en la base de datos")
    print("  3. Hay un problema con la búsqueda")

if input_moves:
    print(f"\n✓ El pallet 039351 aparece como input en {len(input_moves)} moves")
else:
    print(f"\n⚠️  El pallet 039351 NO aparece como input en ningún move")

# Buscar el proceso WH/RF/MO/00615 específicamente
print("\n" + "=" * 80)
print("VERIFICANDO PROCESO WH/RF/MO/00615:")
print("=" * 80)

mo_moves = client.search_read(
    "stock.move.line",
    [
        ("reference", "=", "WH/RF/MO/00615"),
        ("state", "=", "done")
    ],
    ["id", "reference", "package_id", "result_package_id", "date", "product_id", "qty_done"],
    limit=200
)

print(f"\nTotal moves en WH/RF/MO/00615: {len(mo_moves)}")

if mo_moves:
    # Buscar específicamente el pallet 039351
    moves_with_039351_output = [m for m in mo_moves if m.get("result_package_id") and m["result_package_id"][1] == "039351"]
    moves_with_039351_input = [m for m in mo_moves if m.get("package_id") and m["package_id"][1] == "039351"]
    
    print(f"\nMoves donde 039351 es output: {len(moves_with_039351_output)}")
    print(f"Moves donde 039351 es input: {len(moves_with_039351_input)}")
    
    if moves_with_039351_output:
        print("\n✓ ENCONTRADO: 039351 es output en WH/RF/MO/00615")
        for move in moves_with_039351_output:
            pkg_input = move.get("package_id")
            pkg_input_name = pkg_input[1] if pkg_input else "None (vacío)"
            print(f"  - Move ID: {move['id']}")
            print(f"    Package ID: {pkg_input_name}")
            print(f"    Result Package ID: {move['result_package_id'][1]}")
            print(f"    Fecha: {move.get('date', '')[:19]}")
    
    # Mostrar todos los pallets output de este MO
    print(f"\nTodos los pallets output en WH/RF/MO/00615:")
    output_pallets = set()
    for move in mo_moves:
        if move.get("result_package_id"):
            output_pallets.add(move["result_package_id"][1])
    
    print(f"Total pallets únicos como output: {len(output_pallets)}")
    sample = sorted(list(output_pallets))[:20]
    print(f"Muestra (primeros 20): {', '.join(sample)}")
    
    if "039351" in output_pallets:
        print("\n✓ 039351 está en la lista de outputs")
    else:
        print("\n❌ 039351 NO está en la lista de outputs")

print("\n" + "=" * 80)
