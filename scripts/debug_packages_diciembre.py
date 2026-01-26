#!/usr/bin/env python3
"""
Script para investigar cuántos paquetes tienen los pickings de diciembre 2025
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

def main():
    # Usar credenciales directas
    client = OdooClient(
        username="frios@riofuturo.cl",
        password="413c17f8c0a0ebe211cda26c094c2bbb47fce5c6"
    )
    
    print("=" * 80)
    print("INVESTIGACIÓN: Paquetes en pickings de diciembre 2025")
    print("=" * 80)
    
    # Los 3 pickings que sabemos que existen
    picking_names = ["RF/OUT/02020", "RF/OUT/02019", "RF/OUT/02024"]
    
    # Buscar los pickings
    pickings = client.search_read(
        "stock.picking",
        [("name", "in", picking_names)],
        ["id", "name", "origin", "date_done"]
    )
    
    print(f"\nPickings encontrados: {len(pickings)}")
    for p in pickings:
        print(f"  - {p['name']} (ID: {p['id']}): origin={p.get('origin')}, done={p.get('date_done')}")
    
    picking_ids = [p["id"] for p in pickings]
    
    # Buscar move_lines con package_id
    print("\n" + "=" * 80)
    print("Buscando stock.move.line con paquetes...")
    print("=" * 80)
    
    move_lines = client.search_read(
        "stock.move.line",
        [
            ("picking_id", "in", picking_ids),
            ("package_id", "!=", False),
            ("qty_done", ">", 0),
            ("state", "=", "done"),
        ],
        ["id", "picking_id", "package_id", "qty_done", "product_id"],
        limit=5000
    )
    
    print(f"\nTotal move_lines encontrados: {len(move_lines)}")
    
    # Agrupar por picking
    by_picking = {}
    all_packages = set()
    
    for ml in move_lines:
        picking_id = ml["picking_id"][0] if isinstance(ml["picking_id"], (list, tuple)) else ml["picking_id"]
        package_id = ml["package_id"][0] if isinstance(ml["package_id"], (list, tuple)) else ml["package_id"]
        
        if picking_id not in by_picking:
            by_picking[picking_id] = {
                "move_lines": [],
                "packages": set()
            }
        
        by_picking[picking_id]["move_lines"].append(ml)
        by_picking[picking_id]["packages"].add(package_id)
        all_packages.add(package_id)
    
    print("\n" + "=" * 80)
    print("RESUMEN POR PICKING:")
    print("=" * 80)
    
    # Mapear IDs a nombres
    picking_map = {p["id"]: p["name"] for p in pickings}
    
    for picking_id, data in by_picking.items():
        picking_name = picking_map.get(picking_id, f"ID:{picking_id}")
        print(f"\n{picking_name}:")
        print(f"  - Move lines: {len(data['move_lines'])}")
        print(f"  - Paquetes únicos: {len(data['packages'])}")
        print(f"  - Primeros 5 package IDs: {list(data['packages'])[:5]}")
    
    print("\n" + "=" * 80)
    print(f"TOTAL PAQUETES ÚNICOS: {len(all_packages)}")
    print("=" * 80)
    
    if len(all_packages) > 100:
        print(f"\n⚠️  ¡PROBLEMA! Se encontraron {len(all_packages)} paquetes.")
        print("Esto explicaría por qué la trazabilidad procesa tantos registros.")
        print("\nVerificando si los move_lines están bien filtrados...")
        
        # Verificar estados
        print("\nEstados de los move_lines:")
        states = {}
        for ml in move_lines:
            state = ml.get("state", "unknown")
            states[state] = states.get(state, 0) + 1
        for state, count in states.items():
            print(f"  - {state}: {count}")

if __name__ == "__main__":
    main()
