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

# Buscar cuentas analíticas con PROCESO CONGELADO o TUNEL
print("=== Cuentas Analíticas ===")
analytics = search_read('account.analytic.account', [('name', 'ilike', 'PROCESO CONGELADO')], ['id', 'name', 'code'])
if not analytics:
    analytics = search_read('account.analytic.account', [('name', 'ilike', 'TUNEL')], ['id', 'name', 'code'])
if not analytics:
    analytics = search_read('account.analytic.account', [('name', 'ilike', 'CONGELADO')], ['id', 'name', 'code'])
for a in analytics:
    print(f"  {a.get('code', '')} - {a['name']} (ID: {a['id']})")

if not analytics:
    print("  No encontradas. Listando todas...")
    all_an = search_read('account.analytic.account', [], ['id', 'name', 'code'], limit=100)
    for a in all_an:
        print(f"  {a.get('code', '')} - {a['name']} (ID: {a['id']})")

# Buscar en mrp.routing.workcenter (operaciones de ruta)
print("\n=== Operaciones de ruta (mrp.routing.workcenter) ===")
try:
    ops = search_read('mrp.routing.workcenter', [('name', 'ilike', 'PROCESO CONGELADO')], ['id', 'name', 'workcenter_id'])
    if not ops:
        ops = search_read('mrp.routing.workcenter', [('name', 'ilike', 'TUNEL')], ['id', 'name', 'workcenter_id'])
    for op in ops:
        print(f"  {op['name']} - WC: {op.get('workcenter_id', '')} (ID: {op['id']})")
    if not ops:
        print("  No encontradas")
except Exception as e:
    print(f"  Modelo no disponible: {e}")

# Check mrp.production fields
print("\n=== Campos de mrp.production ===")
fields = models.execute_kw(db, uid, password, 'mrp.production', 'fields_get', [], {'attributes': ['string', 'type']})
relevant = {k: v for k, v in fields.items() if any(word in v.get('string', '').lower() for word in ['analytic', 'analít', 'route', 'ruta', 'workcenter', 'centro'])}
for fname, fdata in relevant.items():
    print(f"  {fname}: {fdata['string']} ({fdata['type']})")

# Check if analytic_account_id or similar exists
for key in ['analytic_account_id', 'analytic_tag_ids', 'workcenter_id', 'routing_id']:
    if key in fields:
        print(f"\n  >> {key} exists: {fields[key]['string']} ({fields[key]['type']})")

# Check workorder fields
print("\n=== Muestra de workorders de Túnel 1 (ID=1) ===")
sample_wo = search_read('mrp.workorder', [('workcenter_id', '=', 1), ('state', '=', 'done')], 
    ['id', 'name', 'workcenter_id', 'production_id', 'qty_produced'], limit=5)
for wo in sample_wo:
    print(f"  WO: {wo['name']} | Prod: {wo['production_id']} | Qty: {wo['qty_produced']}")

# Check sample production
if sample_wo:
    pid = sample_wo[0]['production_id'][0]
    prod = search_read('mrp.production', [('id', '=', pid)], [])
    if prod:
        print(f"\n=== Muestra producción ID {pid} ===")
        for k, v in prod[0].items():
            if v and v != False:
                print(f"  {k}: {v}")
