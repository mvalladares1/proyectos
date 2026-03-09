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

# Buscar categorías de producto con "MP"
print("=== Categorías de producto con MP ===")
cats = search_read('product.category', [('name', 'ilike', 'MP')], ['id', 'name', 'complete_name', 'parent_id'])
for c in cats:
    print(f"  ID: {c['id']} | {c.get('complete_name', c['name'])} | Parent: {c.get('parent_id','')}")

print("\n=== Todas las categorías (para contexto) ===")
all_cats = search_read('product.category', [], ['id', 'name', 'complete_name', 'parent_id'])
for c in all_cats:
    print(f"  ID: {c['id']} | {c.get('complete_name', c['name'])}")
