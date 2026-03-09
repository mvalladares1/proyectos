import xmlrpc.client
url='https://riofuturo.server98c6e.oerpondemand.net'
db='riofuturo-master'; user='mvalladares@riofuturo.cl'; pwd='c0766224bec30cac071ffe43a858c9ccbd521ddd'
common=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common',context=None)
uid=common.authenticate(db,user,pwd,{})
models=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object',context=None)
sr=lambda m,d,f,l=0: models.execute_kw(db,uid,pwd,m,'search_read',[d],{'fields':f,'limit':l})

# Productos MP
mp_tag = sr('product.product',[('product_tag_ids','in',[18])],['id','name'])
mp_categ = sr('product.product',[('categ_id','=',4)],['id','name'])
mp_ids = set(p['id'] for p in mp_tag) | set(p['id'] for p in mp_categ)

# VLK producciones en marzo 2026
vlk_prods = sr('mrp.production',[
    ('product_id','=',16446),
    ('state','=','done'),
    ('date_finished','>=','2026-03-01'),
    ('date_finished','<','2026-04-01'),
],['id','name','date_finished','move_raw_ids','qty_produced'])

print(f"VLK producciones marzo 2026: {len(vlk_prods)}")

total_qty_done = 0
total_uom_qty = 0
for prod in vlk_prods:
    print(f"\n  {prod['name']} | fecha: {prod['date_finished']} | qty_produced: {prod['qty_produced']}")
    raw_ids = prod['move_raw_ids']
    moves = sr('stock.move',[('id','in',raw_ids)],['id','product_id','quantity_done','product_uom_qty'])
    for m in moves:
        pid = m['product_id'][0]
        if pid not in mp_ids:
            continue
        qd = m['quantity_done'] or 0
        puq = m['product_uom_qty'] or 0
        qty_used = qd if qd > 0 else puq  # fallback VLK
        total_qty_done += qd
        total_uom_qty += puq
        marker = " *** FALLBACK" if qd == 0 and puq > 0 else ""
        print(f"    {m['product_id'][1]}: qty_done={qd:,.2f} | planned={puq:,.2f} | used={qty_used:,.2f}{marker}")

print(f"\nTOTAL VLK Marzo:")
print(f"  Solo quantity_done: {total_qty_done:,.2f}")
print(f"  Solo product_uom_qty: {total_uom_qty:,.2f}")
print(f"  Con fallback (actual): {total_qty_done + (total_uom_qty - total_qty_done if total_qty_done == 0 else 0):,.2f}")

# Tambien ver todos los meses de VLK
print("\n\n=== VLK POR MES ===")
vlk_all = sr('mrp.production',[('product_id','=',16446),('state','=','done')],['id','date_finished','move_raw_ids'])
from collections import defaultdict
mes_qd = defaultdict(float)
mes_puq = defaultdict(float)
mes_fallback = defaultdict(float)

for prod in vlk_all:
    date_str = str(prod.get('date_finished',''))[:7]
    raw_ids = prod['move_raw_ids']
    moves = sr('stock.move',[('id','in',raw_ids)],['id','product_id','quantity_done','product_uom_qty'])
    for m in moves:
        pid = m['product_id'][0]
        if pid not in mp_ids:
            continue
        qd = m['quantity_done'] or 0
        puq = m['product_uom_qty'] or 0
        mes_qd[date_str] += qd
        mes_puq[date_str] += puq
        mes_fallback[date_str] += qd if qd > 0 else puq

for mes in sorted(mes_qd.keys()):
    diff = mes_fallback[mes] - mes_qd[mes]
    marker = f"  (+{diff:,.2f} fallback)" if diff > 0 else ""
    print(f"  {mes}: qty_done={mes_qd[mes]:,.2f} | con_fallback={mes_fallback[mes]:,.2f}{marker}")
