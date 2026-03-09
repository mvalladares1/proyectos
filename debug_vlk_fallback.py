import xmlrpc.client
url='https://riofuturo.server98c6e.oerpondemand.net'
db='riofuturo-master'; user='mvalladares@riofuturo.cl'; pwd='c0766224bec30cac071ffe43a858c9ccbd521ddd'
common=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common',context=None)
uid=common.authenticate(db,user,pwd,{})
models=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object',context=None)
sr=lambda m,d,f,l=0: models.execute_kw(db,uid,pwd,m,'search_read',[d],{'fields':f,'limit':l})

mp_tag = sr('product.product',[('product_tag_ids','in',[18])],['id'])
mp_ids = set(p['id'] for p in mp_tag)
mp_categ = sr('product.product',[('categ_id','=',4)],['id'])
categ_ids = set(p['id'] for p in mp_categ)
mp_all = mp_ids | categ_ids

# VLK
vlk_prods = sr('mrp.production',[('product_id','=',16446),('state','=','done')],['id','move_raw_ids'])
all_raw = []
for p in vlk_prods:
    all_raw.extend(p['move_raw_ids'])

total_qty_done = 0
total_fallback = 0  # quantity_done or product_uom_qty (el viejo bug)
diff_moves = []

for i in range(0, len(all_raw), 200):
    batch = all_raw[i:i+200]
    moves = sr('stock.move',[('id','in',batch)],['id','product_id','quantity_done','product_uom_qty'])
    for m in moves:
        pid = m['product_id'][0]
        if pid not in mp_all:
            continue
        qd = m['quantity_done'] or 0
        puq = m['product_uom_qty'] or 0
        fallback = qd if qd else puq  # viejo bug
        
        if qd > 0:
            total_qty_done += qd
        if fallback > 0:
            total_fallback += fallback
        
        if qd == 0 and puq > 0:
            diff_moves.append({
                'id': m['id'],
                'product': m['product_id'][1],
                'qty_done': qd,
                'product_uom_qty': puq,
            })

print(f"VLK - Solo quantity_done (actual): {total_qty_done:,.2f} kg")
print(f"VLK - Con fallback qty_done||uom_qty (viejo): {total_fallback:,.2f} kg")
print(f"Diferencia por fallback: {total_fallback - total_qty_done:,.2f} kg")
print(f"\nMoves con qty_done=0 pero product_uom_qty>0: {len(diff_moves)}")
for m in diff_moves[:20]:
    print(f"  Move {m['id']}: {m['product']} -> done=0, planned={m['product_uom_qty']:,.2f}")
