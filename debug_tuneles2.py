import xmlrpc.client

url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", context=None)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", context=None)

def search_read(model, domain, fields, limit=0):
    return models.execute_kw(db, uid, password, model, 'search_read', [domain], {'fields': fields, 'limit': limit})

# Buscar los 3 productos de túneles estáticos
print("Buscando productos de túneles estáticos...")
products = search_read('product.product', [
    ('name', 'ilike', 'PROCESO CONGELADO TÚNEL ESTÁTICO')
], ['id', 'name'])
if not products:
    products = search_read('product.product', [
        ('name', 'ilike', 'PROCESO CONGELADO TUNEL ESTATICO')
    ], ['id', 'name'])
for p in products:
    print(f"  {p['name']} (ID: {p['id']})")

product_ids = [p['id'] for p in products]
product_names = {p['id']: p['name'] for p in products}

# Buscar las producciones terminadas con estos productos
print(f"\nBuscando producciones terminadas...")
productions = search_read('mrp.production', [
    ('product_id', 'in', product_ids),
    ('state', '=', 'done'),
], ['id', 'name', 'product_id', 'move_raw_ids', 'qty_produced', 'date_finished'])
print(f"Producciones encontradas: {len(productions)}")

# Obtener los move_raw_ids (materias primas consumidas)
all_raw_ids = []
prod_map = {}  # move_id -> tunnel product_name
for prod in productions:
    tunnel = prod['product_id'][1]
    for mid in prod['move_raw_ids']:
        all_raw_ids.append(mid)
        prod_map[mid] = tunnel

print(f"Total movimientos de materia prima: {len(all_raw_ids)}")

# Leer los movimientos de materia prima
print("\nLeyendo movimientos de materia prima...")
from collections import defaultdict

kg_por_fruta_tunel = defaultdict(lambda: defaultdict(float))
kg_por_fruta_total = defaultdict(float)

batch_size = 200
for i in range(0, len(all_raw_ids), batch_size):
    batch = all_raw_ids[i:i+batch_size]
    moves = search_read('stock.move', [('id', 'in', batch)], [
        'id', 'product_id', 'product_uom_qty', 'quantity_done', 'product_uom', 'state'
    ])
    
    for move in moves:
        product_name = move['product_id'][1] if move['product_id'] else 'Desconocido'
        qty = move.get('quantity_done', 0) or move.get('product_uom_qty', 0)
        uom = move.get('product_uom', [0, ''])[1] if move.get('product_uom') else ''
        tunnel = prod_map.get(move['id'], 'Desconocido')
        
        kg_por_fruta_tunel[product_name][tunnel] += qty
        kg_por_fruta_total[product_name] += qty
    
    print(f"  Procesados {min(i+batch_size, len(all_raw_ids))}/{len(all_raw_ids)}")

# Mostrar resumen
print(f"\n=== RESUMEN ===")
print(f"Tipos de fruta/material: {len(kg_por_fruta_total)}")
for fruta in sorted(kg_por_fruta_total.keys(), key=lambda x: kg_por_fruta_total[x], reverse=True):
    print(f"  {fruta}: {kg_por_fruta_total[fruta]:,.2f} kg")
    for tunnel in sorted(kg_por_fruta_tunel[fruta].keys()):
        print(f"    -> {tunnel}: {kg_por_fruta_tunel[fruta][tunnel]:,.2f}")

# Also check: what's in move_finished_ids?
print("\n=== Muestra move_finished ===")
sample = productions[0] if productions else None
if sample:
    fin_moves = search_read('stock.move', [('id', 'in', sample.get('move_finished_ids', []))], 
        ['id', 'product_id', 'quantity_done', 'product_uom'])
    for m in fin_moves:
        print(f"  {m['product_id'][1]}: {m['quantity_done']} {m.get('product_uom', ['',''])[1]}")
