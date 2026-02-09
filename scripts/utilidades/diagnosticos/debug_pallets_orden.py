"""
Debug script para buscar pallets de una orden específica
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

# Credenciales
username = "mjaramillo@riofuturo.cl"
password = "659e9fd07b2bc2c0aca3539de16a9da50bb263b1"

# Nombre de la orden que quieres buscar
orden_name = input("Nombre de la orden (ej: WH/MO/12345): ")

odoo = OdooClient(username=username, password=password)

print(f"\n1. Buscando orden {orden_name}...")
ordenes = odoo.search_read(
    'mrp.production',
    [('name', '=', orden_name)],
    ['id', 'name', 'product_id', 'lot_producing_id', 'date_finished'],
    limit=1
)

if not ordenes:
    print(f"❌ No se encontró la orden {orden_name}")
    sys.exit(1)

orden = ordenes[0]
print(f"✅ Orden encontrada:")
print(f"   ID: {orden['id']}")
print(f"   Nombre: {orden['name']}")
print(f"   Producto: {orden.get('product_id')}")
print(f"   Lote: {orden.get('lot_producing_id')}")

# Buscar stock.move relacionados
print(f"\n2. Buscando stock.move relacionados a la orden...")
moves = odoo.search_read(
    'stock.move',
    [('raw_material_production_id', '=', orden['id'])],
    ['id', 'name', 'product_id', 'reference', 'origin'],
    limit=50
)

print(f"   Encontrados {len(moves)} stock.move")
for m in moves[:3]:
    print(f"   - {m['name']}: {m.get('reference')} / {m.get('origin')}")

# Buscar stock.move.line con result_package_id
print(f"\n3. Buscando stock.move.line con pallets...")
print(f"   Probando filtro por reference ilike '{orden_name}'...")
move_lines_ref = odoo.search_read(
    'stock.move.line',
    [
        ('result_package_id', '!=', False),
        ('reference', 'ilike', orden_name)
    ],
    ['id', 'result_package_id', 'product_id', 'reference', 'qty_done'],
    limit=100
)
print(f"   Encontrados {len(move_lines_ref)} stock.move.line por reference")

print(f"\n   Probando filtro por origin ilike '{orden_name}'...")
move_lines_origin = odoo.search_read(
    'stock.move.line',
    [
        ('result_package_id', '!=', False),
        ('origin', 'ilike', orden_name)
    ],
    ['id', 'result_package_id', 'product_id', 'origin', 'qty_done'],
    limit=100
)
print(f"   Encontrados {len(move_lines_origin)} stock.move.line por origin")

# Buscar por production_id si existe
print(f"\n   Probando filtro por production_id = {orden['id']}...")
try:
    move_lines_prod = odoo.search_read(
        'stock.move.line',
        [
            ('result_package_id', '!=', False),
            ('production_id', '=', orden['id'])
        ],
        ['id', 'result_package_id', 'product_id', 'qty_done', 'lot_id'],
        limit=100
    )
    print(f"   Encontrados {len(move_lines_prod)} stock.move.line por production_id")
    
    if move_lines_prod:
        print(f"\n✅ ENCONTRADOS PALLETS:")
        pallets = {}
        for line in move_lines_prod:
            pkg = line.get('result_package_id')
            if pkg:
                pkg_name = pkg[1] if isinstance(pkg, list) else str(pkg)
                if pkg_name not in pallets:
                    pallets[pkg_name] = {
                        'product': line.get('product_id'),
                        'qty': 0,
                        'lot': line.get('lot_id')
                    }
                pallets[pkg_name]['qty'] += line.get('qty_done', 0)
        
        for pkg_name, info in pallets.items():
            print(f"   📦 {pkg_name}")
            print(f"      Producto: {info['product']}")
            print(f"      Cantidad: {info['qty']} kg")
            print(f"      Lote: {info['lot']}")
except Exception as e:
    print(f"   ❌ Error probando production_id: {e}")

# Buscar por move_id relacionado
print(f"\n4. Buscando por move_id...")
if moves:
    move_ids = [m['id'] for m in moves]
    print(f"   IDs de moves: {move_ids[:5]}...")
    
    move_lines_by_move = odoo.search_read(
        'stock.move.line',
        [
            ('result_package_id', '!=', False),
            ('move_id', 'in', move_ids)
        ],
        ['id', 'result_package_id', 'product_id', 'qty_done', 'lot_id'],
        limit=100
    )
    print(f"   Encontrados {len(move_lines_by_move)} stock.move.line por move_id")
    
    if move_lines_by_move:
        print(f"\n✅ ENCONTRADOS PALLETS POR MOVE_ID:")
        pallets = {}
        for line in move_lines_by_move:
            pkg = line.get('result_package_id')
            if pkg:
                pkg_name = pkg[1] if isinstance(pkg, list) else str(pkg)
                if pkg_name not in pallets:
                    pallets[pkg_name] = {
                        'product': line.get('product_id'),
                        'qty': 0,
                        'lot': line.get('lot_id')
                    }
                pallets[pkg_name]['qty'] += line.get('qty_done', 0)
        
        for pkg_name, info in pallets.items():
            print(f"   📦 {pkg_name}")
            print(f"      Producto: {info['product']}")
            print(f"      Cantidad: {info['qty']} kg")
            print(f"      Lote: {info['lot']}")

print("\n" + "="*50)
print("Debug completado")
