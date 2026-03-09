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

# Buscar TODOS los paquetes RF2026M
print("=== Todos los paquetes RF2026M ===")
all_pkgs = search_read('stock.quant.package', [('name', '=like', 'RF2026M%')], ['id', 'name'])
print(f"Total: {len(all_pkgs)}")
pkg_ids = [p['id'] for p in all_pkgs]

# Buscar move lines con estos paquetes como destino
print("\nBuscando move lines...")
all_mls = []
batch = 200
for i in range(0, len(pkg_ids), batch):
    b = pkg_ids[i:i+batch]
    mls = search_read('stock.move.line', [
        ('result_package_id', 'in', b),
        ('state', '=', 'done'),
    ], ['id', 'picking_id', 'result_package_id', 'qty_done', 'product_id'])
    all_mls.extend(mls)

print(f"Total move lines: {len(all_mls)}")

# Obtener pickings únicos
pick_ids = list(set(ml['picking_id'][0] for ml in all_mls if ml.get('picking_id')))
print(f"Pickings únicos: {len(pick_ids)}")

picks = {}
for i in range(0, len(pick_ids), batch):
    b = pick_ids[i:i+batch]
    ps = search_read('stock.picking', [('id', 'in', b)], ['id', 'name', 'picking_type_id', 'date_done'])
    for p in ps:
        picks[p['id']] = p

# Agrupar por picking_type_id
from collections import defaultdict
by_type = defaultdict(list)
for ml in all_mls:
    pid = ml['picking_id'][0] if ml['picking_id'] else 0
    p = picks.get(pid, {})
    pt = p.get('picking_type_id', [0, 'Desconocido'])
    by_type[(pt[0], pt[1])].append(ml)

print("\n=== Recepciones con RF2026M por tipo de operación ===")
for (pt_id, pt_name), mls in sorted(by_type.items(), key=lambda x: x[0][0]):
    total_kg = sum(ml['qty_done'] for ml in mls)
    pick_names = set()
    for ml in mls:
        pid = ml['picking_id'][0] if ml['picking_id'] else 0
        p = picks.get(pid, {})
        pick_names.add(p.get('name', ''))
    print(f"\n  Tipo: {pt_name} (ID: {pt_id})")
    print(f"  Move lines: {len(mls)} | KG: {total_kg:,.2f}")
    print(f"  Pickings ({len(pick_names)}):")
    for pn in sorted(pick_names):
        print(f"    - {pn}")
