import xmlrpc.client
url='https://riofuturo.server98c6e.oerpondemand.net'
db='riofuturo-master'; user='mvalladares@riofuturo.cl'; pwd='c0766224bec30cac071ffe43a858c9ccbd521ddd'
common=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common',context=None)
uid=common.authenticate(db,user,pwd,{})
models=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object',context=None)
sr=lambda m,d,f,l=0: models.execute_kw(db,uid,pwd,m,'search_read',[d],{'fields':f,'limit':l})

# Productos filtros
mp_tag = sr('product.product',[('product_tag_ids','in',[18])],['id','name'])
mp_tag_ids = set(p['id'] for p in mp_tag)
mp_categ = sr('product.product',[('categ_id','=',4)],['id','name'])
mp_categ_ids = set(p['id'] for p in mp_categ)
mp_all = mp_tag_ids | mp_categ_ids

# VLK producciones
vlk_prods = sr('mrp.production',[('product_id','=',16446),('state','=','done')],['id','move_raw_ids'])
all_raw = []
for p in vlk_prods:
    all_raw.extend(p['move_raw_ids'])
print(f"VLK producciones: {len(vlk_prods)}, raw moves: {len(all_raw)}")

# Leer TODOS los moves sin filtro de producto
total_all = 0
total_mp = 0
total_excluido = 0
excluidos = {}

for i in range(0, len(all_raw), 200):
    batch = all_raw[i:i+200]
    moves = sr('stock.move',[('id','in',batch)],['id','product_id','quantity_done'])
    for m in moves:
        qty = m['quantity_done'] or 0
        if qty <= 0:
            continue
        pid = m['product_id'][0]
        pname = m['product_id'][1]
        total_all += qty
        if pid in mp_all:
            total_mp += qty
        else:
            total_excluido += qty
            if pname not in excluidos:
                excluidos[pname] = {'kg': 0, 'count': 0, 'pid': pid}
            excluidos[pname]['kg'] += qty
            excluidos[pname]['count'] += 1

print(f"\nVLK - TOTAL SIN FILTRO: {total_all:,.2f} kg")
print(f"VLK - Con filtro MP (tag+categ): {total_mp:,.2f} kg")
print(f"VLK - Excluidos: {total_excluido:,.2f} kg")
print(f"\nDiferencia: {total_all - total_mp:,.2f} kg")

print(f"\nProductos EXCLUIDOS ({len(excluidos)}):")
for name, info in sorted(excluidos.items(), key=lambda x: -x[1]['kg']):
    # Buscar tags del producto
    ptags = sr('product.product',[('id','=',info['pid'])],['product_tag_ids','categ_id'])
    tags = ptags[0]['product_tag_ids'] if ptags else []
    categ = ptags[0]['categ_id'] if ptags else []
    print(f"  {name} (ID {info['pid']}): {info['kg']:,.2f} kg ({info['count']} moves) | tags={tags} categ={categ}")
