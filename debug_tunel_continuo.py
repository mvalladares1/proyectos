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

# Buscar producto del túnel continuo
print("=== Buscando producto TÚNEL CONTÍNUO ===")
prods = search_read('product.product', [('name', 'ilike', 'TÚNEL CONTÍNUO')], ['id', 'name'])
if not prods:
    prods = search_read('product.product', [('name', 'ilike', 'TUNEL CONTINUO')], ['id', 'name'])
if not prods:
    prods = search_read('product.product', [('name', 'ilike', 'TÚNEL CONT')], ['id', 'name'])
for p in prods:
    print(f"  {p['name']} (ID: {p['id']})")

# Muestra de producciones
if prods:
    pid = prods[0]['id']
    sample = search_read('mrp.production', [('product_id', '=', pid), ('state', '=', 'done')], 
        ['id', 'name', 'product_id', 'move_raw_ids', 'qty_produced', 'date_finished'], limit=3)
    print(f"\nProducciones encontradas (muestra): {len(sample)}")
    for s in sample:
        print(f"  {s['name']} | Qty: {s['qty_produced']} | Fecha: {s.get('date_finished','')}")
        # Ver materias primas
        raw_moves = search_read('stock.move', [('id', 'in', s['move_raw_ids'])], 
            ['id', 'product_id', 'quantity_done'])
        for m in raw_moves:
            print(f"    -> {m['product_id'][1]}: {m['quantity_done']} kg")
    
    # Contar total
    total = models.execute_kw(db, uid, password, 'mrp.production', 'search_count', 
        [[('product_id', '=', pid), ('state', '=', 'done')]])
    print(f"\nTotal producciones terminadas: {total}")
