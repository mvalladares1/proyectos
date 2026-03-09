import xmlrpc.client
from collections import defaultdict

url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", context=None)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", context=None)

def search_read(model, domain, fields, limit=0):
    return models.execute_kw(db, uid, password, model, 'search_read', [domain], {'fields': fields, 'limit': limit})

# Recepciones MP de Rio Futuro: picking_type_id 1 y 151
print("Buscando recepciones MP de Rio Futuro (picking_type_id=1 y 151)...")
pick_ids = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[
    ('picking_type_id', 'in', [1, 151]),
    ('state', '=', 'done'),
]])
print(f"Total recepciones done: {len(pick_ids)}")

# Buscar move lines por batches y filtrar RF2026M
print(f"\nBuscando move lines...")
rf2026m_lines = []
lot_prefixes = defaultdict(int)
batch_size = 200
total_ml = 0

for i in range(0, len(pick_ids), batch_size):
    batch = pick_ids[i:i+batch_size]
    mls = search_read('stock.move.line', [
        ('picking_id', 'in', batch),
        ('state', '=', 'done'),
    ], ['lot_id', 'lot_name', 'product_id', 'qty_done', 'picking_id'])
    total_ml += len(mls)
    
    for ml in mls:
        lot_name = ''
        if ml.get('lot_id') and ml['lot_id']:
            lot_name = ml['lot_id'][1] if isinstance(ml['lot_id'], list) else str(ml['lot_id'])
        elif ml.get('lot_name'):
            lot_name = ml['lot_name']
        
        if lot_name:
            prefix = lot_name[:7] if len(lot_name) >= 7 else lot_name
            lot_prefixes[prefix] += 1
        
        if lot_name.upper().startswith('RF2026M'):
            rf2026m_lines.append({
                'lot': lot_name,
                'product': ml['product_id'][1] if ml['product_id'] else 'Desconocido',
                'qty': ml['qty_done'],
                'picking': ml['picking_id'][1] if ml['picking_id'] else '',
            })
    
    print(f"  Batch {i//batch_size + 1}/{(len(pick_ids)-1)//batch_size + 1}: {len(mls)} líneas | RF2026M: {len(rf2026m_lines)} | Total: {total_ml}")

print(f"\nTotal move lines: {total_ml}")
print(f"Líneas con pallet RF2026M: {len(rf2026m_lines)}")

if rf2026m_lines:
    kg_por_fruta = defaultdict(float)
    for line in rf2026m_lines:
        kg_por_fruta[line['product']] += line['qty']
    
    print(f"\n=== KG por tipo de fruta ===")
    total = 0
    for fruta in sorted(kg_por_fruta.keys(), key=lambda x: kg_por_fruta[x], reverse=True):
        print(f"  {fruta}: {kg_por_fruta[fruta]:,.2f} kg")
        total += kg_por_fruta[fruta]
    print(f"\n  TOTAL CONGELADOS: {total:,.2f} kg")
else:
    print("\n=== Top prefijos de lotes ===")
    for prefix, count in sorted(lot_prefixes.items(), key=lambda x: -x[1])[:30]:
        print(f"  '{prefix}': {count}")
    
    # Buscar específicamente RF2026
    print("\n=== Buscar RF2026 en cualquier parte ===")
    rf_lots = search_read('stock.lot', [('name', 'ilike', 'RF2026')], ['name'], limit=20)
    print(f"stock.lot con RF2026: {len(rf_lots)}")
    for l in rf_lots[:10]:
        print(f"  {l['name']}")
    
    # Buscar en move lines directamente
    print("\n=== Buscar move.line con lot RF2026M ===")
    direct = search_read('stock.move.line', [
        ('lot_id.name', '=like', 'RF2026M%'),
        ('state', '=', 'done'),
    ], ['lot_id', 'product_id', 'qty_done', 'picking_id'], limit=10)
    print(f"Directas: {len(direct)}")
    for d in direct:
        print(f"  {d['lot_id']} | {d['product_id']} | {d['qty_done']}")
