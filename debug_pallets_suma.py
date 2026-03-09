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

grupo1 = [
    'PACK0011254','PACK0011354','PACK0011363','PACK0011333',
    'PACK0011334','PACK0011277','PACK0011362','PACK0011278',
    'PACK0013332','PACK0013297','PACK0013316','PACK0010981',
    'PACK0012532','PACK0013203','PACK0013329','PACK0010723',
    'PACK0011352','PACK0013283','PACK0013204','PACK0013207',
    'PACK0013348','PACK0011357','PACK0013346','PACK0011359',
]

grupo2 = [
    'PACK0014040','PACK0014039','PACK0013229','PACK0012597',
    'PACK0013198','PACK0012598','PACK0013254','PACK0013363',
    'PACK0012635','PACK0012647','PACK0013193','PACK0012626',
    'PACK0013197','PACK0012664','PACK0013282','PACK0013192',
    'PACK0011365','PACK0012652','PACK0013254','PACK0013208',
    'PACK0011364','PACK0013228','PACK0012639','PACK0012653',
]

# Unir y quitar duplicados
todos = list(dict.fromkeys(grupo1 + grupo2))
print(f"Grupo 1: {len(grupo1)} pallets")
print(f"Grupo 2: {len(grupo2)} pallets")
print(f"Total unicos combinados: {len(todos)}")

pkgs = sr('stock.quant.package', [('name', 'in', todos)], ['id', 'name'])
pkg_map = {p['name']: p['id'] for p in pkgs}
print(f"Encontrados en Odoo: {len(pkgs)}")

not_found = [p for p in todos if p not in pkg_map]
if not_found:
    print(f"NO encontrados: {not_found}")

pkg_ids = [p['id'] for p in pkgs]
mls = sr('stock.move.line', [
    ('result_package_id', 'in', pkg_ids),
    ('state', '=', 'done'),
], ['id', 'product_id', 'qty_done', 'picking_id', 'result_package_id'])

pkg_id_to_name = {p['id']: p['name'] for p in pkgs}

# Grupo 1
g1_ids = set(pkg_map[n] for n in dict.fromkeys(grupo1) if n in pkg_map)
g1_kg = sum(ml['qty_done'] or 0 for ml in mls if ml.get('result_package_id') and ml['result_package_id'][0] in g1_ids)

# Grupo 2
g2_ids = set(pkg_map[n] for n in dict.fromkeys(grupo2) if n in pkg_map)
g2_kg = sum(ml['qty_done'] or 0 for ml in mls if ml.get('result_package_id') and ml['result_package_id'][0] in g2_ids)

sj_actual = 392583.83

print(f"\n{'='*50}")
print(f"Grupo 1 (24 pallets):    {g1_kg:>12,.2f} kg")
print(f"Grupo 2 (24 pallets):    {g2_kg:>12,.2f} kg")
print(f"San Jose actual:         {sj_actual:>12,.2f} kg")
print(f"{'='*50}")
print(f"TOTAL:                   {g1_kg + g2_kg + sj_actual:>12,.2f} kg")
