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

pallets = [
    'PACK0014040', 'PACK0014039', 'PACK0013229', 'PACK0012597',
    'PACK0013198', 'PACK0012598', 'PACK0013254', 'PACK0013363',
    'PACK0012635', 'PACK0012647', 'PACK0013193', 'PACK0012626',
    'PACK0013197', 'PACK0012664', 'PACK0013282', 'PACK0013192',
    'PACK0011365', 'PACK0012652', 'PACK0013254', 'PACK0013208',
    'PACK0011364', 'PACK0013228', 'PACK0012639', 'PACK0012653',
]

# Eliminar duplicados manteniendo orden
seen = set()
unique_pallets = []
for p in pallets:
    if p not in seen:
        seen.add(p)
        unique_pallets.append(p)

print(f"Pallets unicos: {len(unique_pallets)} (de {len(pallets)} listados)")

# Buscar paquetes
pkgs = sr('stock.quant.package', [('name', 'in', unique_pallets)], ['id', 'name'])
pkg_map = {p['name']: p['id'] for p in pkgs}
print(f"Paquetes encontrados en Odoo: {len(pkgs)}")

not_found = [p for p in unique_pallets if p not in pkg_map]
if not_found:
    print(f"NO encontrados: {not_found}")

# Buscar move lines con estos paquetes como result_package_id
pkg_ids = [p['id'] for p in pkgs]
mls = sr('stock.move.line', [
    ('result_package_id', 'in', pkg_ids),
    ('state', '=', 'done'),
], ['id', 'product_id', 'qty_done', 'picking_id', 'result_package_id'])

# Mapear pkg_id -> name
pkg_id_to_name = {p['id']: p['name'] for p in pkgs}

# Obtener picking info
pick_ids = list(set(ml['picking_id'][0] for ml in mls if ml.get('picking_id')))
picks = sr('stock.picking', [('id', 'in', pick_ids)], ['id', 'name', 'picking_type_id', 'date_done'])
pick_map = {p['id']: p for p in picks}

# Obtener picking type names
pt_ids = list(set(p['picking_type_id'][0] for p in picks if p.get('picking_type_id')))
pt_data = sr('stock.picking.type', [('id', 'in', pt_ids)], ['id', 'name'])
pt_map = {p['id']: p['name'] for p in pt_data}

print(f"\nTotal move lines: {len(mls)}")
print(f"\n{'#':<4} {'Pallet':<15} {'Producto':<45} {'KG':>12} {'Recepcion':<25} {'Tipo Op'}")
print("-" * 130)

total_kg = 0
for i, pallet_name in enumerate(unique_pallets, 1):
    pkg_id = pkg_map.get(pallet_name)
    if not pkg_id:
        print(f"{i:<4} {pallet_name:<15} NO ENCONTRADO")
        continue
    pallet_mls = [ml for ml in mls if ml.get('result_package_id') and ml['result_package_id'][0] == pkg_id]
    pallet_kg = 0
    for ml in pallet_mls:
        prod = ml['product_id'][1] if ml['product_id'] else '?'
        qty = ml['qty_done'] or 0
        pick_id = ml['picking_id'][0] if ml['picking_id'] else None
        pick = pick_map.get(pick_id, {})
        pick_name = pick.get('name', 'Sin picking')
        pt_id = pick.get('picking_type_id', [0])[0] if pick.get('picking_type_id') else 0
        pt_name = pt_map.get(pt_id, '?')
        print(f"{i:<4} {pallet_name:<15} {prod:<45} {qty:>12,.2f} {pick_name:<25} {pt_name}")
        pallet_kg += qty
    total_kg += pallet_kg

print(f"\n{'='*130}")
print(f"TOTAL KG: {total_kg:,.2f}")
print(f"Pallets: {len(unique_pallets)} unicos")

# Resumen por tipo de operacion
print(f"\n=== RESUMEN POR TIPO DE OPERACION ===")
by_type = {}
for ml in mls:
    pick_id = ml['picking_id'][0] if ml['picking_id'] else None
    pick = pick_map.get(pick_id, {})
    pt_id = pick.get('picking_type_id', [0])[0] if pick.get('picking_type_id') else 0
    pt_name = pt_map.get(pt_id, 'Sin picking')
    by_type.setdefault(pt_name, 0)
    by_type[pt_name] += ml['qty_done'] or 0

for tp, kg in sorted(by_type.items()):
    print(f"  {tp}: {kg:,.2f} kg")
