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

# Buscar paquetes (stock.quant.package) con RF2026M
print("=== Buscando paquetes RF2026M en stock.quant.package ===")
packages = search_read('stock.quant.package', [('name', '=like', 'RF2026M%')], ['id', 'name'], limit=20)
print(f"Encontrados: {len(packages)}")
for p in packages[:10]:
    print(f"  {p['name']} (ID: {p['id']})")

# Contar total
total = models.execute_kw(db, uid, password, 'stock.quant.package', 'search_count', [[('name', '=like', 'RF2026M%')]])
print(f"\nTotal paquetes RF2026M: {total}")

if packages:
    pkg_ids = [p['id'] for p in packages[:5]]
    
    # Buscar move lines donde result_package_id sea uno de estos paquetes
    print("\n=== Move lines con result_package_id en muestra ===")
    mls = search_read('stock.move.line', [
        ('result_package_id', 'in', pkg_ids),
    ], ['id', 'lot_id', 'product_id', 'qty_done', 'picking_id', 'result_package_id', 'state'], limit=10)
    print(f"Encontrados: {len(mls)}")
    for ml in mls[:5]:
        print(f"  Pkg: {ml['result_package_id']} | Prod: {ml['product_id']} | Qty: {ml['qty_done']} | Pick: {ml.get('picking_id','')} | State: {ml['state']}")

    # Ver los pickings
    if mls:
        pick_ids = list(set(ml['picking_id'][0] for ml in mls if ml.get('picking_id')))
        picks = search_read('stock.picking', [('id', 'in', pick_ids)], ['id', 'name', 'picking_type_id', 'state', 'date_done'])
        for p in picks:
            print(f"  Pick: {p['name']} | Tipo: {p['picking_type_id']} | Estado: {p['state']} | Fecha: {p.get('date_done','')}")
