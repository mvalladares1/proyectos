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

# picking_type_id = 164 = San Jose: Recepciones MP
print("Buscando recepciones MP de San José (picking_type_id=164)...")
pick_ids = models.execute_kw(db, uid, password, 'stock.picking', 'search', [[
    ('picking_type_id', '=', 164),
    ('state', '=', 'done'),
]])
print(f"Total recepciones done: {len(pick_ids)}")

# Muestra de nombres
sample = search_read('stock.picking', [('id', 'in', pick_ids[:5])], ['name', 'date_done', 'origin'])
for s in sample:
    print(f"  {s['name']} | {s.get('date_done','')} | {s.get('origin','')}")

# Buscar move lines de estas recepciones
print(f"\nBuscando move lines con lot_name que empiece con RF2026M...")
# Primero buscar en stock.move.line de estos pickings
# Hacerlo por batches
all_move_lines = []
batch_size = 500
for i in range(0, len(pick_ids), batch_size):
    batch = pick_ids[i:i+batch_size]
    mls = search_read('stock.move.line', [
        ('picking_id', 'in', batch),
        ('state', '=', 'done'),
    ], ['lot_id', 'lot_name', 'product_id', 'qty_done', 'picking_id'])
    all_move_lines.extend(mls)
    print(f"  Batch {i//batch_size + 1}: {len(mls)} líneas (acumulado: {len(all_move_lines)})")

print(f"\nTotal move lines: {len(all_move_lines)}")

# Filtrar las que tienen lot RF2026M
rf2026m_lines = []
for ml in all_move_lines:
    lot_name = ''
    if ml.get('lot_id') and ml['lot_id']:
        lot_name = ml['lot_id'][1] if isinstance(ml['lot_id'], list) else str(ml['lot_id'])
    elif ml.get('lot_name'):
        lot_name = ml['lot_name']
    
    if lot_name.startswith('RF2026M'):
        rf2026m_lines.append({
            'lot': lot_name,
            'product': ml['product_id'][1] if ml['product_id'] else 'Desconocido',
            'qty': ml['qty_done'],
            'picking': ml['picking_id'][1] if ml['picking_id'] else '',
        })

print(f"\nLíneas con pallet RF2026M: {len(rf2026m_lines)}")

# Agrupar por producto (tipo de fruta)
kg_por_fruta = defaultdict(float)
for line in rf2026m_lines:
    kg_por_fruta[line['product']] += line['qty']

print(f"\n=== KG por tipo de fruta ===")
total = 0
for fruta in sorted(kg_por_fruta.keys(), key=lambda x: kg_por_fruta[x], reverse=True):
    print(f"  {fruta}: {kg_por_fruta[fruta]:,.2f} kg")
    total += kg_por_fruta[fruta]
print(f"\n  TOTAL CONGELADOS: {total:,.2f} kg")

# Si no encontró nada, mostrar muestras de lot names
if not rf2026m_lines:
    print("\n=== Muestras de lot names para diagnosticar ===")
    lot_names_sample = set()
    for ml in all_move_lines[:500]:
        lot_name = ''
        if ml.get('lot_id') and ml['lot_id']:
            lot_name = ml['lot_id'][1] if isinstance(ml['lot_id'], list) else str(ml['lot_id'])
        elif ml.get('lot_name'):
            lot_name = ml['lot_name']
        if lot_name:
            lot_names_sample.add(lot_name[:15])
    for ln in sorted(lot_names_sample)[:30]:
        print(f"  {ln}")
