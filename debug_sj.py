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

MP_CATEG_ID = 4

# 1. Cuántas recepciones MP tiene San José en total?
print("=== Recepciones MP San José (picking_type_id=164) ===")
# San Jose: Recepciones MP = ID 164
total_picks = models.execute_kw(db, uid, password, 'stock.picking', 'search_count', 
    [[('picking_type_id', '=', 164), ('state', '=', 'done')]])
print(f"Total recepciones MP San José (done): {total_picks}")

# 2. Ver todas las recepciones MP San José
picks = search_read('stock.picking', [
    ('picking_type_id', '=', 164),
    ('state', '=', 'done'),
], ['id', 'name', 'date_done', 'partner_id'])
print(f"\nRecepciones:")
total_kg_all = 0
for p in picks:
    # Obtener move lines de esta recepción
    mls = search_read('stock.move.line', [
        ('picking_id', '=', p['id']),
        ('state', '=', 'done'),
    ], ['product_id', 'qty_done'])
    
    kg_pick = sum(ml['qty_done'] for ml in mls)
    
    # Filtrar solo MP
    mp_prods = search_read('product.product', [('categ_id', '=', MP_CATEG_ID)], ['id'])
    mp_ids = set(pr['id'] for pr in mp_prods)
    kg_mp = sum(ml['qty_done'] for ml in mls if ml['product_id'] and ml['product_id'][0] in mp_ids)
    
    partner = p.get('partner_id', [0, ''])[1] if p.get('partner_id') else ''
    print(f"  {p['name']} | {str(p.get('date_done',''))[:10]} | {partner} | KG total: {kg_pick:,.2f} | KG MP: {kg_mp:,.2f}")
    total_kg_all += kg_mp

print(f"\nTotal KG MP todas las recepciones SJ: {total_kg_all:,.2f}")

# 3. Cuántos paquetes hay en total en SJ?
print("\n=== Paquetes en recepciones SJ ===")
for p in picks[:3]:
    mls = search_read('stock.move.line', [
        ('picking_id', '=', p['id']),
        ('state', '=', 'done'),
    ], ['result_package_id', 'product_id', 'qty_done'], limit=5)
    for ml in mls:
        pkg = ml.get('result_package_id', '')
        print(f"  {p['name']} | Pkg: {pkg} | Prod: {ml['product_id']} | Qty: {ml['qty_done']}")

# 4. Buscar paquetes RF2026 (sin M específicamente)
print("\n=== Paquetes RF2026 (todos) ===")
for pattern in ['RF2026%', 'RF2026M%', 'RF2026C%', 'RF2026S%']:
    count = models.execute_kw(db, uid, password, 'stock.quant.package', 'search_count', 
        [[('name', '=like', pattern)]])
    print(f"  {pattern}: {count}")
