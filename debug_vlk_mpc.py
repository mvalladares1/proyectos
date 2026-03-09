import xmlrpc.client
url='https://riofuturo.server98c6e.oerpondemand.net'
db='riofuturo-master'; user='mvalladares@riofuturo.cl'; pwd='c0766224bec30cac071ffe43a858c9ccbd521ddd'
common=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common',context=None)
uid=common.authenticate(db,user,pwd,{})
models=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object',context=None)
sr=lambda m,d,f,l=0: models.execute_kw(db,uid,pwd,m,'search_read',[d],{'fields':f,'limit':l})

# Tags
mp_tag = sr('product.product',[('product_tag_ids','in',[18])],['id','name'])
mp_ids = set(p['id'] for p in mp_tag)
mpc_tag = sr('product.product',[('product_tag_ids','in',[60])],['id','name'])
mpc_ids = set(p['id'] for p in mpc_tag)
mp_categ = sr('product.product',[('categ_id','=',4)],['id','name'])
categ_ids = set(p['id'] for p in mp_categ)
mp_all = mp_ids | categ_ids  # lo que usamos ahora
mp_all_mpc = mp_all | mpc_ids  # si agregaramos MPC

tunnel_ids = {15984: 'Estático 1', 15985: 'Estático 2', 15986: 'Estático 3', 15987: 'Continuo', 16446: 'VLK'}

print(f"Tag MP: {len(mp_ids)} | Tag MPC: {len(mpc_ids)} | Categ MP: {len(categ_ids)}")
print(f"MP actual (tag+categ): {len(mp_all)} | Con MPC: {len(mp_all_mpc)}")
print()

for tid, tname in tunnel_ids.items():
    prods = sr('mrp.production',[('product_id','=',tid),('state','=','done')],['id','move_raw_ids'])
    all_raw = []
    for p in prods:
        all_raw.extend(p['move_raw_ids'])
    
    total_mp = 0
    total_mpc = 0
    mpc_detail = {}
    
    for i in range(0, len(all_raw), 200):
        batch = all_raw[i:i+200]
        moves = sr('stock.move',[('id','in',batch)],['id','product_id','quantity_done'])
        for m in moves:
            qty = m['quantity_done'] or 0
            if qty <= 0:
                continue
            pid = m['product_id'][0]
            pname = m['product_id'][1]
            if pid in mp_all:
                total_mp += qty
            elif pid in mpc_ids:
                total_mpc += qty
                if pname not in mpc_detail:
                    mpc_detail[pname] = 0
                mpc_detail[pname] += qty
    
    total = total_mp + total_mpc
    print(f"{tname}: MP={total_mp:,.2f} | MPC={total_mpc:,.2f} | TOTAL={total:,.2f}")
    if mpc_detail:
        for name, kg in sorted(mpc_detail.items(), key=lambda x: -x[1]):
            print(f"  MPC: {name}: {kg:,.2f} kg")
