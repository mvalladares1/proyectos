"""
Debug: Buscar información adicional de pallets (envase, productor, num_bandejas)
"""
import xmlrpc.client

# Configuración
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 100)
print("DEBUG: INFORMACIÓN DE PALLET - ENVASE, PRODUCTOR, NUM BANDEJAS")
print("=" * 100)

# Buscar el pallet específico
pallet_name = 'PACK0039924'

print(f"\n🔍 Buscando pallet: {pallet_name}")

# Buscar en stock.quant.package
packages = models.execute_kw(db, uid, password,
    'stock.quant.package', 'search_read',
    [[['name', '=', pallet_name]]],
    {'fields': []}
)

if packages:
    pkg = packages[0]
    print(f"\n✅ STOCK.QUANT.PACKAGE encontrado (ID: {pkg['id']})")
    print("-" * 80)
    for field, value in sorted(pkg.items()):
        if value not in [False, None, '', [], 0, 0.0]:
            print(f"  {field:50} = {value}")
else:
    print("❌ No encontrado en stock.quant.package")

# Buscar en stock.move.line donde result_package_id sea este pallet
print("\n" + "=" * 80)
print("📦 STOCK.MOVE.LINE (donde se creó el pallet)")
print("=" * 80)

move_lines = models.execute_kw(db, uid, password,
    'stock.move.line', 'search_read',
    [[['result_package_id.name', '=', pallet_name]]],
    {'fields': [], 'limit': 5}
)

if move_lines:
    print(f"\n✅ Encontradas {len(move_lines)} move lines")
    for ml in move_lines[:2]:
        print(f"\n--- Move Line ID: {ml['id']} ---")
        # Mostrar campos que contengan pack, prod, num, bandeja
        campos_interes = ['num_packs', 'product_pack_id', 'productor', 'producer', 
                         'x_studio_num_packs', 'x_studio_productor', 'x_studio_envase',
                         'pack', 'bandeja', 'num_bandeja', 'bandejas']
        
        for field, value in sorted(ml.items()):
            if value in [False, None, '', [], 0, 0.0]:
                continue
            # Mostrar campos que puedan ser relevantes
            field_lower = field.lower()
            if any(k in field_lower for k in ['pack', 'prod', 'num', 'bandej', 'envase', 'studio']):
                print(f"  {field:50} = {value}")
        
        print("\n  === TODOS LOS CAMPOS CON VALOR ===")
        for field, value in sorted(ml.items()):
            if value in [False, None, '', [], 0, 0.0]:
                continue
            if isinstance(value, str) and len(value) > 100:
                continue
            print(f"  {field:50} = {value}")
else:
    print("❌ No encontrado en stock.move.line")

# Buscar en stock.quant
print("\n" + "=" * 80)
print("📊 STOCK.QUANT (cantidad actual del pallet)")
print("=" * 80)

quants = models.execute_kw(db, uid, password,
    'stock.quant', 'search_read',
    [[['package_id.name', '=', pallet_name]]],
    {'fields': [], 'limit': 3}
)

if quants:
    print(f"\n✅ Encontrados {len(quants)} quants")
    for q in quants[:1]:
        print(f"\n--- Quant ID: {q['id']} ---")
        for field, value in sorted(q.items()):
            if value in [False, None, '', [], 0, 0.0]:
                continue
            if isinstance(value, str) and len(value) > 100:
                continue
            print(f"  {field:50} = {value}")

# Buscar en mrp.production si el pallet viene de una orden de manufactura
print("\n" + "=" * 80)
print("🏭 MRP - Buscar origen del pallet")
print("=" * 80)

# Buscar move lines de receipt/manufactura
receipt_lines = models.execute_kw(db, uid, password,
    'stock.move.line', 'search_read',
    [[['result_package_id.name', '=', pallet_name], ['picking_id', '!=', False]]],
    {'fields': ['picking_id', 'move_id', 'product_id', 'qty_done', 'lot_id'], 'limit': 5}
)

if receipt_lines:
    print(f"\n✅ Move lines con picking: {len(receipt_lines)}")
    for rl in receipt_lines:
        print(f"  Picking: {rl.get('picking_id')} | Move: {rl.get('move_id')} | Product: {rl.get('product_id')}")
        
        # Obtener detalles del move
        if rl.get('move_id'):
            move_id = rl['move_id'][0] if isinstance(rl['move_id'], (list, tuple)) else rl['move_id']
            move = models.execute_kw(db, uid, password,
                'stock.move', 'read',
                [move_id],
                {'fields': []}
            )
            if move:
                move = move[0]
                print(f"\n  --- STOCK.MOVE ID: {move_id} ---")
                for field, value in sorted(move.items()):
                    if value in [False, None, '', [], 0, 0.0]:
                        continue
                    field_lower = field.lower()
                    if any(k in field_lower for k in ['pack', 'prod', 'num', 'bandej', 'envase', 'studio', 'origin']):
                        print(f"    {field:48} = {value}")

print("\n" + "=" * 100)
print("FIN DEBUG")
print("=" * 100)
