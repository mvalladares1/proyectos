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

# Contar productos con tag MP (18) y MPC (60)
mp_prods = sr('product.product', [('product_tag_ids', 'in', [18])], ['id', 'name'])
mpc_prods = sr('product.product', [('product_tag_ids', 'in', [60])], ['id', 'name'])
print(f"Productos con tag MP (18): {len(mp_prods)}")
print(f"Productos con tag MPC (60): {len(mpc_prods)}")
print()
print("--- MP products ---")
for p in sorted(mp_prods, key=lambda x: x['name']):
    print(f"  {p['id']}: {p['name']}")
print()
print("--- MPC products ---")
for p in sorted(mpc_prods, key=lambda x: x['name']):
    print(f"  {p['id']}: {p['name']}")
