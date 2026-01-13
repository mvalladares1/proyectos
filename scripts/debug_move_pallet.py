"""
Script de DEBUG para investigar movimiento de pallets
NO ejecuta movimientos reales, solo analiza la estructura de datos
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient
import json

# Configuración
PALLET_CODE = "HPACK0015412"
LOCATION_DEST_ID = 8536  # RF/Stock/Camara 8 0°C (Cam80C)

def debug_pallet_structure(odoo: OdooClient, pallet_code: str):
    """Analiza la estructura completa de un pallet"""
    print(f"\n{'='*80}")
    print(f"DEBUG: Analizando pallet {pallet_code}")
    print(f"{'='*80}\n")
    
    # 1. Buscar el paquete
    print("1️⃣ BUSCANDO PAQUETE...")
    packages = odoo.search_read(
        "stock.quant.package",
        [("name", "=", pallet_code)],
        ["id", "name", "location_id", "package_use"]
    )
    
    if not packages:
        print(f"❌ Paquete {pallet_code} NO encontrado")
        return
    
    package = packages[0]
    print(f"✅ Paquete encontrado:")
    print(json.dumps(package, indent=2, default=str))
    package_id = package["id"]
    
    # 2. Buscar quants asociados (TODOS, incluso negativos)
    print(f"\n2️⃣ BUSCANDO QUANTS DEL PAQUETE (ID: {package_id})...")
    quants = odoo.search_read(
        "stock.quant",
        [("package_id", "=", package_id)],  # SIN filtro de quantity > 0
        ["id", "location_id", "product_id", "quantity", "product_uom_id", "lot_id", "reserved_quantity"]
    )
    
    print(f"\n📦 Total de quants encontrados: {len(quants)}")
    quants_positivos = [q for q in quants if q['quantity'] > 0]
    quants_negativos = [q for q in quants if q['quantity'] <= 0]
    
    print(f"   ✅ Quants positivos: {len(quants_positivos)}")
    print(f"   ⚠️  Quants negativos/cero: {len(quants_negativos)}")
    
    for i, q in enumerate(quants, 1):
        prefix = "✅" if q['quantity'] > 0 else "❌"
        print(f"\n   {prefix} Quant #{i}:")
        print(f"   - ID: {q['id']}")
        print(f"   - Producto: {q['product_id'][1] if q.get('product_id') else 'N/A'}")
        print(f"   - Ubicación: {q['location_id'][1] if q.get('location_id') else 'N/A'}")
        print(f"   - Cantidad: {q['quantity']}")
        print(f"   - Cantidad reservada: {q.get('reserved_quantity', 0)}")
        print(f"   - Lote: {q['lot_id'][1] if q.get('lot_id') else 'N/A'} (ID: {q['lot_id'][0] if q.get('lot_id') else 'N/A'})")
    
    # 3. Buscar movimientos pendientes
    print(f"\n3️⃣ BUSCANDO MOVIMIENTOS PENDIENTES...")
    pending_moves = odoo.search_read(
        "stock.move",
        [
            ("product_id", "in", [q["product_id"][0] for q in quants if q.get("product_id")]),
            ("state", "in", ["draft", "waiting", "confirmed", "assigned"]),
        ],
        ["id", "name", "picking_id", "product_id", "state", "product_uom_qty", "reserved_availability"]
    )
    
    print(f"\n📋 Movimientos pendientes encontrados: {len(pending_moves)}")
    for i, move in enumerate(pending_moves, 1):
        print(f"\n   Move #{i}:")
        print(f"   - ID: {move['id']}")
        print(f"   - Nombre: {move['name']}")
        print(f"   - Picking: {move['picking_id'][1] if move.get('picking_id') else 'N/A'}")
        print(f"   - Estado: {move['state']}")
        print(f"   - Cantidad: {move['product_uom_qty']}")
        
        # Buscar move lines asociadas a este move que usen nuestro paquete
        move_lines = odoo.search_read(
            "stock.move.line",
            [
                ("move_id", "=", move["id"]),
                "|",
                ("package_id", "=", package_id),
                ("result_package_id", "=", package_id)
            ],
            ["id", "package_id", "result_package_id", "qty_done", "reserved_uom_qty", "state"]
        )
        
        if move_lines:
            print(f"   ⚠️  ESTE MOVIMIENTO USA NUESTRO PAQUETE:")
            for ml in move_lines:
                print(f"      - Move Line ID: {ml['id']}")
                print(f"      - Package ID: {ml.get('package_id')}")
                print(f"      - Result Package ID: {ml.get('result_package_id')}")
                print(f"      - Qty Done: {ml.get('qty_done', 0)}")
                print(f"      - Reserved: {ml.get('reserved_uom_qty', 0)}")
                print(f"      - Estado: {ml.get('state', 'N/A')}")
    
    # 4. Buscar en recepciones pendientes
    print(f"\n4️⃣ BUSCANDO EN RECEPCIONES PENDIENTES...")
    move_lines_reception = odoo.search_read(
        "stock.move.line",
        [
            ("result_package_id", "=", package_id),
            ("state", "not in", ["done", "cancel"]),
            ("picking_id.picking_type_code", "=", "incoming")
        ],
        ["id", "picking_id", "location_dest_id", "product_id", "qty_done", "state"]
    )
    
    print(f"\n📥 Move lines de recepción encontradas: {len(move_lines_reception)}")
    for i, ml in enumerate(move_lines_reception, 1):
        print(f"\n   Move Line #{i}:")
        print(f"   - ID: {ml['id']}")
        print(f"   - Picking: {ml['picking_id'][1] if ml.get('picking_id') else 'N/A'}")
        print(f"   - Destino: {ml['location_dest_id'][1] if ml.get('location_dest_id') else 'N/A'}")
        print(f"   - Estado: {ml['state']}")
    
    # 5. Simular creación de transferencia
    print(f"\n5️⃣ SIMULACIÓN DE CREACIÓN DE TRANSFERENCIA...")
    print(f"\n   Ubicación origen (de los quants):")
    locations_found = set(q["location_id"][0] for q in quants)
    for loc_id in locations_found:
        loc = odoo.search_read("stock.location", [("id", "=", loc_id)], ["name", "usage", "active"])
        if loc:
            print(f"   - {loc[0]['name']} (ID: {loc_id}, Tipo: {loc[0]['usage']}, Activo: {loc[0]['active']})")
    
    print(f"\n   Ubicación destino solicitada: {LOCATION_DEST_ID}")
    dest_loc = odoo.search_read("stock.location", [("id", "=", LOCATION_DEST_ID)], ["name", "usage", "active"])
    if dest_loc:
        print(f"   - {dest_loc[0]['name']} (Tipo: {dest_loc[0]['usage']}, Activo: {dest_loc[0]['active']})")
    
    # Validar si ya está en destino
    if len(locations_found) == 1 and list(locations_found)[0] == LOCATION_DEST_ID:
        print("\n   ⚠️  EL PALLET YA ESTÁ EN LA UBICACIÓN DESTINO")
        return
    
    # 6. Buscar picking type
    print(f"\n6️⃣ BUSCANDO PICKING TYPE INTERNO...")
    picking_types = odoo.search_read(
        "stock.picking.type",
        [("code", "=", "internal"), ("warehouse_id", "!=", False)],
        ["id", "name", "warehouse_id"],
        limit=5
    )
    
    print(f"\n   Picking types disponibles: {len(picking_types)}")
    for pt in picking_types:
        print(f"   - ID: {pt['id']}, Nombre: {pt['name']}, Warehouse: {pt.get('warehouse_id')}")
    
    # 7. Analizar la estructura que se crearía
    print(f"\n7️⃣ ESTRUCTURA QUE SE CREARÍA:")
    print(f"\n   📋 PICKING:")
    print(f"   - Tipo: {picking_types[0]['id'] if picking_types else 'N/A'}")
    print(f"   - Origen: {quants[0]['location_id'][1] if quants else 'N/A'}")
    print(f"   - Destino: {dest_loc[0]['name'] if dest_loc else 'N/A'}")
    print(f"   - Origen: Dashboard Move Multi: {pallet_code}")
    
    print(f"\n   📦 STOCK MOVES A CREAR: {len(quants)}")
    for i, q in enumerate(quants, 1):
        print(f"\n   Move #{i}:")
        print(f"   - Producto: {q['product_id'][1] if q.get('product_id') else 'N/A'}")
        print(f"   - Cantidad: {q['quantity']}")
        print(f"   - Origen: {q['location_id'][1] if q.get('location_id') else 'N/A'}")
        print(f"   - Destino: {dest_loc[0]['name'] if dest_loc else 'N/A'}")
        print(f"   - Package ID (origen y destino): {package_id}")
    
    # 8. Verificar si hay problema de múltiples moves con mismo paquete
    print(f"\n8️⃣ ANÁLISIS DE POTENCIALES CONFLICTOS:")
    
    if quants_negativos:
        print(f"\n   🚨 PROBLEMA CRÍTICO: HAY {len(quants_negativos)} QUANTS NEGATIVOS/CERO")
        print(f"   - Esto indica un problema de inventario en Odoo")
        print(f"   - El paquete tiene stock negativo de algunos productos")
        print(f"   - Esto puede causar errores en validación de transferencias")
    
    if len(quants_positivos) > 1:
        print(f"\n   ⚠️  SE CREARÍAN {len(quants_positivos)} STOCK MOVES DIFERENTES")
        print(f"   ⚠️  TODOS CON EL MISMO package_id = {package_id}")
        print(f"\n   🔍 POSIBLE PROBLEMA:")
        print(f"   - Odoo puede interpretar esto como intentar mover el mismo paquete")
        print(f"     múltiples veces en la misma operación")
        print(f"   - Error esperado: 'No puede mover el mismo contenido del paquete'")
        print(f"                     'más de una vez en la misma transferencia'")
        print(f"\n   💡 SOLUCIÓN POSIBLE:")
        print(f"   - Crear UN SOLO stock.move para todo el paquete")
        print(f"   - O no asignar package_id a los moves individuales")
        print(f"   - Solo asignar package_id a las move_lines finales")
    elif len(quants_positivos) == 1:
        print(f"\n   ✅ Solo hay 1 quant positivo, no debería haber conflicto de paquetes")
    else:
        print(f"\n   ❌ No hay quants positivos - no se puede mover nada")
    
    print(f"\n{'='*80}")
    print(f"FIN DEL DEBUG")
    print(f"{'='*80}\n")


def main():
    # Credenciales
    username = input("Usuario Odoo: ").strip()
    password = input("API Key: ").strip()
    
    # Conectar a Odoo
    print("\n🔌 Conectando a Odoo...")
    odoo = OdooClient(username=username, password=password)
    
    try:
        # Ejecutar debug
        debug_pallet_structure(odoo, PALLET_CODE)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
