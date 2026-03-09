import xmlrpc.client
url='https://riofuturo.server98c6e.oerpondemand.net'
db='riofuturo-master'; user='mvalladares@riofuturo.cl'; pwd='c0766224bec30cac071ffe43a858c9ccbd521ddd'
common=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common',context=None)
uid=common.authenticate(db,user,pwd,{})
models=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object',context=None)
sr=lambda m,d,f: models.execute_kw(db,uid,pwd,m,'search_read',[d],{'fields':f})

categ = sr('product.product',[('categ_id','=',4)],['id','name','product_tag_ids'])
mp_tag = sr('product.product',[('product_tag_ids','in',[18])],['id','name'])
mp_ids = set(p['id'] for p in mp_tag)
categ_ids = set(p['id'] for p in categ)

diff = categ_ids - mp_ids
print(f"Productos en categ MP pero sin tag MP: {len(diff)}")
for p in categ:
    if p['id'] in diff:
        print(f"  ID {p['id']}: {p['name']} (tags: {p['product_tag_ids']})")

# Todos los túneles
tunnel_ids = {15984: 'Estático 1', 15985: 'Estático 2', 15986: 'Estático 3', 15987: 'Continuo', 16446: 'VLK'}

for tid, tname in tunnel_ids.items():
    prods = sr('mrp.production', [('product_id','=',tid),('state','=','done')], ['id','move_raw_ids'])
    all_raw = []
    for p in prods:
        all_raw.extend(p['move_raw_ids'])
    
    if not all_raw:
        print(f"\n{tname}: sin producciones")
        continue
    
    # Buscar moves con productos en diff
    moves = sr('stock.move', [('id','in',all_raw),('product_id','in',list(diff))], ['id','product_id','quantity_done'])
    total = sum(m['quantity_done'] or 0 for m in moves)
    if total > 0:
        print(f"\n{tname}: {len(moves)} moves con productos sin tag MP -> {total:,.2f} kg")
        for m in moves:
            print(f"  {m['product_id'][1]}: {m['quantity_done']:,.2f} kg")
    else:
        print(f"\n{tname}: 0 kg con productos sin tag MP")

# También: productos con tag MP pero SIN categ 4
mp_not_categ = mp_ids - categ_ids
print(f"\n\nProductos con tag MP pero sin categ MP: {len(mp_not_categ)}")
for p in mp_tag:
    if p['id'] in mp_not_categ:
        print(f"  ID {p['id']}: {p['name']}")
