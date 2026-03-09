import xmlrpc.client
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=None)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=None)

def sr(model, domain, fields, limit=0):
    return models.execute_kw(db, uid, password, model, 'search_read', [domain], {'fields': fields, 'limit': limit})

CONTINUO_ID = 15987
MP_TAG_ID = 18

mp_prods = sr('product.product', [('product_tag_ids', 'in', [MP_TAG_ID])], ['id', 'name'])
mp_ids = set(p['id'] for p in mp_prods)

# Tomar las primeras producciones que tienen 0 en debug
prods = sr('mrp.production', [('product_id', '=', CONTINUO_ID), ('state', '=', 'done')], 
           ['id', 'name', 'move_raw_ids', 'date_finished'], limit=20)

print("Producciones con qty_done=0 pero product_uom_qty > 0:")
print(f"{'Producción':<25} {'Producto':<40} {'qty_done':>12} {'uom_qty':>12}")
print("-" * 95)

total_phantom = 0
for prod in sorted(prods, key=lambda x: x.get('date_finished', '')):
    moves = sr('stock.move', [('id', 'in', prod['move_raw_ids'])], 
               ['id', 'product_id', 'quantity_done', 'product_uom_qty'])
    for m in moves:
        pid = m['product_id'][0] if m['product_id'] else 0
        if pid not in mp_ids:
            continue
        pname = m['product_id'][1]
        qd = m['quantity_done'] or 0
        uq = m['product_uom_qty'] or 0
        if qd == 0 and uq > 0:
            print(f"{prod['name']:<25} {pname:<40} {qd:>12,.2f} {uq:>12,.2f}")
            total_phantom += uq

print(f"\nTotal KG fantasma (qty_done=0, uom_qty>0): {total_phantom:,.2f}")
