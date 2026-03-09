import xmlrpc.client
url='https://riofuturo.server98c6e.oerpondemand.net'
db='riofuturo-master'; user='mvalladares@riofuturo.cl'; pwd='c0766224bec30cac071ffe43a858c9ccbd521ddd'
common=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common',context=None)
uid=common.authenticate(db,user,pwd,{})
models=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object',context=None)
sr=lambda m,d,f,l=0: models.execute_kw(db,uid,pwd,m,'search_read',[d],{'fields':f,'limit':l})

# Todos los productos MP (tag + categ)
mp_tag = sr('product.product',[('product_tag_ids','in',[18])],['id','name','default_code'])
mp_categ = sr('product.product',[('categ_id','=',4)],['id','name','default_code'])
all_ids = set()
all_prods = []
for p in mp_tag + mp_categ:
    if p['id'] not in all_ids:
        all_ids.add(p['id'])
        all_prods.append(p)

print(f"Total productos MP: {len(all_prods)}\n")
for p in sorted(all_prods, key=lambda x: x['name']):
    code = p.get('default_code', '') or ''
    name = p['name']
    # Extraer prefijo de familia
    prefix = name.split(' ')[0] if name.startswith('[') else name[:2]
    print(f"  {name}  (code={code})")
