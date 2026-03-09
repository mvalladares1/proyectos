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

def fields_get(model, attrs=None):
    if attrs is None:
        attrs = ['string', 'type', 'relation']
    return models.execute_kw(db, uid, password, model, 'fields_get', [], {'attributes': attrs})

# 1. Buscar pallets RF2026M en stock.lot (lotes/series)
print("=== Buscando pallets RF2026M en stock.lot ===")
lots = search_read('stock.lot', [('name', '=like', 'RF2026M%')], ['id', 'name', 'product_id', 'product_qty'], limit=10)
print(f"Encontrados: {len(lots)}")
for l in lots[:5]:
    print(f"  {l['name']} | Producto: {l['product_id']} | Qty: {l.get('product_qty', '')}")

if not lots:
    print("\nBuscando con ilike...")
    lots = search_read('stock.lot', [('name', 'ilike', 'RF2026M')], ['id', 'name', 'product_id', 'product_qty'], limit=10)
    print(f"Encontrados: {len(lots)}")
    for l in lots[:5]:
        print(f"  {l['name']} | Producto: {l['product_id']} | Qty: {l.get('product_qty', '')}")

# 2. Contar total
total_count = models.execute_kw(db, uid, password, 'stock.lot', 'search_count', [[('name', '=like', 'RF2026M%')]])
print(f"\nTotal pallets RF2026M: {total_count}")

# 3. Ver campos de stock.lot relevantes
print("\n=== Campos relevantes de stock.lot ===")
lot_fields = fields_get('stock.lot')
for fname, fdata in lot_fields.items():
    if any(w in fdata.get('string', '').lower() for w in ['picking', 'recepc', 'move', 'quant', 'qty', 'weight', 'kg']):
        print(f"  {fname}: {fdata['string']} ({fdata['type']}) {fdata.get('relation', '')}")

# 4. Buscar move lines asociadas a estos lotes
if lots:
    lot_ids_sample = [l['id'] for l in lots[:5]]
    print(f"\n=== Buscando stock.move.line con lot_id en sample ===")
    move_lines = search_read('stock.move.line', [
        ('lot_id', 'in', lot_ids_sample),
    ], ['id', 'lot_id', 'product_id', 'qty_done', 'picking_id', 'move_id', 'state', 'reference'], limit=10)
    print(f"Encontrados: {len(move_lines)}")
    for ml in move_lines[:5]:
        print(f"  Lot: {ml['lot_id']} | Prod: {ml['product_id']} | Qty: {ml['qty_done']} | Pick: {ml.get('picking_id', '')} | Ref: {ml.get('reference', '')} | State: {ml['state']}")

    # 5. Ver los pickings (recepciones)
    if move_lines:
        pick_ids = list(set(ml['picking_id'][0] for ml in move_lines if ml.get('picking_id')))
        print(f"\n=== Pickings asociados ===")
        pickings = search_read('stock.picking', [('id', 'in', pick_ids[:5])], 
            ['id', 'name', 'picking_type_id', 'state', 'origin', 'date_done'])
        for p in pickings:
            print(f"  {p['name']} | Tipo: {p['picking_type_id']} | Estado: {p['state']} | Origen: {p.get('origin', '')} | Fecha: {p.get('date_done', '')}")

# 6. Verificar si hay picking type de recepciones
print("\n=== Picking types de recepción ===")
pick_types = search_read('stock.picking.type', [('code', '=', 'incoming')], ['id', 'name', 'warehouse_id'])
for pt in pick_types:
    print(f"  {pt['name']} (ID: {pt['id']}) | WH: {pt.get('warehouse_id', '')}")
