"""
Script para debuguear información de pallets para Stock Picking PWA

Uso:
    python scripts/debug_pallet_info.py PACK0026966
    python scripts/debug_pallet_info.py PACK0027645
"""

import sys
import os

# Agregar el directorio raíz al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

# Credenciales
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"


def debug_pallet(pallet_code: str):
    """Investiga toda la información de un pallet."""
    
    print("=" * 80)
    print(f"DEBUG PALLET: {pallet_code}")
    print("=" * 80)
    
    # Conectar a Odoo
    print("\n1. Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("   ✓ Conectado exitosamente")
    
    # 1. Buscar el paquete
    print(f"\n2. Buscando paquete {pallet_code}...")
    packages = odoo.search_read(
        "stock.quant.package",
        [("name", "=", pallet_code)],
        ["id", "name", "location_id", "quant_ids", "pack_date", 
         "x_studio_cantidad_total", "create_date", "write_date"]
    )
    
    if not packages:
        print(f"   ✗ ERROR: Paquete {pallet_code} no encontrado")
        return
    
    package = packages[0]
    print(f"   ✓ Paquete encontrado:")
    print(f"      - ID: {package['id']}")
    print(f"      - Nombre: {package['name']}")
    print(f"      - Location: {package.get('location_id')}")
    print(f"      - Quant IDs: {package.get('quant_ids')}")
    print(f"      - Pack Date: {package.get('pack_date')}")
    print(f"      - x_studio_cantidad_total: {package.get('x_studio_cantidad_total')}")
    
    package_id = package["id"]
    
    # 2. Buscar quants
    print(f"\n3. Buscando stock.quant para package_id={package_id}...")
    quants = odoo.search_read(
        "stock.quant",
        [("package_id", "=", package_id)],
        ["id", "product_id", "lot_id", "quantity", "reserved_quantity",
         "location_id", "in_date", "x_studio_cantbandejas", 
         "x_studio_related_field_mf3qY", "product_uom_id"]
    )
    
    if quants:
        print(f"   ✓ Encontrados {len(quants)} quants:")
        for i, q in enumerate(quants):
            print(f"\n   Quant #{i+1}:")
            print(f"      - ID: {q['id']}")
            print(f"      - Product: {q.get('product_id')}")
            print(f"      - Lot: {q.get('lot_id')}")
            print(f"      - Quantity: {q.get('quantity')}")
            print(f"      - Reserved: {q.get('reserved_quantity')}")
            print(f"      - Location: {q.get('location_id')}")
            print(f"      - x_studio_cantbandejas: {q.get('x_studio_cantbandejas')}")
            print(f"      - Productor: {q.get('x_studio_related_field_mf3qY')}")
            print(f"      - In Date: {q.get('in_date')}")
            print(f"      - UOM: {q.get('product_uom_id')}")
    else:
        print("   ✗ No hay quants para este paquete")
    
    # 3. Buscar en stock.move.line (recepciones abiertas)
    print(f"\n4. Buscando stock.move.line para package_id={package_id} (recepciones abiertas)...")
    move_lines = odoo.search_read(
        "stock.move.line",
        [
            ("result_package_id", "=", package_id),
            ("state", "not in", ["done", "cancel"])
        ],
        ["id", "product_id", "lot_id", "qty_done", "reserved_qty",
         "num_packs", "picking_id", "location_id", 
         "location_dest_id", "product_uom_id", "state"]
    )
    
    if move_lines:
        print(f"   ✓ Encontradas {len(move_lines)} líneas de movimiento pendientes:")
        for i, ml in enumerate(move_lines):
            print(f"\n   Move Line #{i+1}:")
            print(f"      - ID: {ml['id']}")
            print(f"      - Product: {ml.get('product_id')}")
            print(f"      - Lot: {ml.get('lot_id')}")
            print(f"      - Quantity: {ml.get('quantity')}")
            print(f"      - Qty Done: {ml.get('qty_done')}")
            print(f"      - Reserved: {ml.get('reserved_qty')}")
            print(f"      - num_packs (Bandejas): {ml.get('num_packs')}")
            print(f"      - Picking: {ml.get('picking_id')}")
            print(f"      - Location: {ml.get('location_id')}")
            print(f"      - Location Dest: {ml.get('location_dest_id')}")
            print(f"      - State: {ml.get('state')}")
    else:
        print("   ✗ No hay move lines pendientes para este paquete")
    
    # 4. Buscar en stock.move.line TODAS las líneas (históricas)
    print(f"\n5. Buscando TODAS las stock.move.line históricas para package_id={package_id}...")
    all_move_lines = odoo.search_read(
        "stock.move.line",
        [("result_package_id", "=", package_id)],
        ["id", "product_id", "lot_id", "qty_done",
         "num_packs", "picking_id", "state", "date"],
        order="id asc",
        limit=10
    )
    
    if all_move_lines:
        print(f"   ✓ Encontradas {len(all_move_lines)} líneas históricas:")
        for i, ml in enumerate(all_move_lines):
            print(f"\n   Move Line #{i+1}:")
            print(f"      - ID: {ml['id']}")
            print(f"      - Product: {ml.get('product_id')}")
            print(f"      - Lot: {ml.get('lot_id')}")
            print(f"      - Qty Done: {ml.get('qty_done')}")
            print(f"      - num_packs (Bandejas): {ml.get('num_packs')}")
            print(f"      - Picking: {ml.get('picking_id')}")
            print(f"      - State: {ml.get('state')}")
            print(f"      - Date: {ml.get('date')}")
    else:
        print("   ✗ No hay move lines históricas para este paquete")
    
    # 5. También buscar por package_id (el campo antiguo)
    print(f"\n6. Buscando stock.move.line por package_id (campo antiguo)...")
    old_move_lines = odoo.search_read(
        "stock.move.line",
        [("package_id", "=", package_id)],
        ["id", "product_id", "lot_id", "qty_done", "num_packs", 
         "picking_id", "state"],
        limit=5
    )
    
    if old_move_lines:
        print(f"   ✓ Encontradas {len(old_move_lines)} líneas (package_id antiguo):")
        for ml in old_move_lines:
            print(f"      - ID: {ml['id']}, Picking: {ml.get('picking_id')}, "
                  f"Bandejas: {ml.get('num_packs')}, State: {ml.get('state')}")
    else:
        print("   ✗ No hay move lines con package_id")
    
    print("\n" + "=" * 80)
    print("FIN DEBUG")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/debug_pallet_info.py PACK0026966")
        sys.exit(1)
    
    pallet_code = sys.argv[1]
    debug_pallet(pallet_code)
