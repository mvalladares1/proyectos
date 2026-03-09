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

# Paso 1: Buscar lots con distintos patrones
print("=== Búsqueda amplia en stock.lot ===")
# Buscar cualquier lot que contenga "2026" y "M"
lots_sample = search_read('stock.lot', [('name', '=like', 'RF%2026%')], ['name', 'product_id'], limit=20)
print(f"RF%2026%: {len(lots_sample)}")
for l in lots_sample[:10]:
    print(f"  {l['name']} | {l['product_id']}")

if not lots_sample:
    # Buscar los últimos lots creados
    print("\nÚltimos lots creados:")
    recent = search_read('stock.lot', [], ['name', 'product_id', 'create_date'], limit=20)
    # Sort by create_date if available
    for l in recent:
        print(f"  {l['name']} | {l['product_id']} | {l.get('create_date', '')}")
