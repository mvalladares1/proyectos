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

# 1. Buscar en stock.lot con variantes del patron
print("=== Variantes de búsqueda en stock.lot ===")
for pattern in ['RF2026M', 'RF-2026M', 'RF2026-M', 'RF/2026/M', 'RF2026m']:
    count = models.execute_kw(db, uid, password, 'stock.lot', 'search_count', [[('name', 'ilike', pattern)]])
    print(f"  '{pattern}': {count}")

# 2. Buscar en stock.picking (recepciones) con RF2026M
print("\n=== Buscar en stock.picking ===")
for pattern in ['RF2026M', 'RF/2026/M', '2026M']:
    picks = search_read('stock.picking', [('name', 'ilike', pattern)], ['id', 'name', 'picking_type_id', 'state'], limit=5)
    print(f"  '{pattern}': {len(picks)} resultados")
    for p in picks[:3]:
        print(f"    {p['name']} | {p['picking_type_id']} | {p['state']}")

# 3. Buscar en stock.move.line (lot_name)
print("\n=== Buscar en stock.move.line por lot_name ===")
for pattern in ['RF2026M', 'RF-2026M', 'RF/2026/M']:
    count = models.execute_kw(db, uid, password, 'stock.move.line', 'search_count', [[('lot_name', 'ilike', pattern)]])
    print(f"  lot_name '{pattern}': {count}")

# 4. Revisar si hay un modelo custom de pallets
print("\n=== Buscando modelos con 'pallet' ===")
try:
    ir_models = search_read('ir.model', [('name', 'ilike', 'pallet')], ['model', 'name'])
    for m in ir_models:
        print(f"  {m['model']}: {m['name']}")
except:
    pass

try:
    ir_models = search_read('ir.model', [('model', 'ilike', 'pallet')], ['model', 'name'])
    for m in ir_models:
        print(f"  {m['model']}: {m['name']}")
except:
    pass

# 5. Buscar muestra de lots que empiecen con RF
print("\n=== Muestra lots con RF ===")
rf_lots = search_read('stock.lot', [('name', '=like', 'RF%')], ['name', 'product_id'], limit=20)
print(f"Total con RF%: {len(rf_lots)}")
# Agrupar por prefijo
prefixes = set()
for l in rf_lots:
    name = l['name']
    prefixes.add(name[:10] if len(name) >= 10 else name)
for p in sorted(prefixes):
    print(f"  {p}...")

# 6. Buscar lots con 2026
print("\n=== Muestra lots con 2026 ===")
lots_2026 = search_read('stock.lot', [('name', 'ilike', '2026')], ['name', 'product_id'], limit=20)
print(f"Total: {len(lots_2026)}")
for l in lots_2026[:10]:
    print(f"  {l['name']} | {l['product_id']}")

# 7. Buscar en mrp.production con RF2026M
print("\n=== Buscar mrp.production con RF2026M ===")
for pattern in ['RF2026M', 'RF/2026/M', 'CongTE']:
    prods = search_read('mrp.production', [('name', 'ilike', pattern)], ['id', 'name', 'product_id', 'qty_produced'], limit=5)
    print(f"  '{pattern}': {len(prods)}")
    for p in prods[:3]:
        print(f"    {p['name']} | {p['product_id']} | Qty: {p['qty_produced']}")

# 8. Ver nombres de picking recepciones MP
print("\n=== Muestra Recepciones MP recientes ===")
recs = search_read('stock.picking', [
    ('picking_type_id', '=', 1),  # Recepciones MP
    ('state', '=', 'done'),
], ['id', 'name', 'date_done', 'origin'], limit=10)
for r in recs:
    print(f"  {r['name']} | {r.get('date_done', '')} | {r.get('origin', '')}")
