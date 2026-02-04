from shared.odoo_client import OdooClient
odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

# Buscar procesos de SAN JOSE usando picking_type_id = 222
print('=== PROCESOS SAN JOSE (picking_type_id = 222) ===')
domain_sj = [
    ['state', '!=', 'done'],
    ['state', '!=', 'cancel'],
    ['picking_type_id', '=', 222]
]
procesos_sj = odoo.search_read('mrp.production', domain_sj, 
    ['name', 'state', 'product_qty', 'qty_produced', 'x_studio_inicio_de_proceso', 'x_studio_termino_de_proceso'], 
    limit=50)
print(f'Procesos activos SAN JOSE: {len(procesos_sj)}')
for p in procesos_sj[:20]:
    print(f"  {p['name']}: state={p['state']}, qty={p['product_qty']}, inicio={p.get('x_studio_inicio_de_proceso')}")

# Procesos cerrados SAN JOSE
print('\n=== PROCESOS CERRADOS SAN JOSE ===')
domain_sj_cerrados = [
    ['state', '=', 'done'],
    ['picking_type_id', '=', 222]
]
cerrados_sj = odoo.search_read('mrp.production', domain_sj_cerrados,
    ['name', 'state', 'qty_produced', 'x_studio_inicio_de_proceso', 'x_studio_termino_de_proceso', 'date_finished'],
    limit=50, order='date_finished desc')
print(f'Procesos cerrados SAN JOSE: {len(cerrados_sj)}')
for p in cerrados_sj[:20]:
    print(f"  {p['name']}: qty_produced={p['qty_produced']}, termino={p.get('x_studio_termino_de_proceso')}, finished={p.get('date_finished')}")

# Procesos VILKUN (picking_type_id = 219)
print('\n=== PROCESOS VILKUN (picking_type_id = 219) ===')
domain_vlk = [
    ['state', '!=', 'done'],
    ['state', '!=', 'cancel'],
    ['picking_type_id', '=', 219]
]
procesos_vlk = odoo.search_read('mrp.production', domain_vlk,
    ['name', 'state', 'product_qty', 'qty_produced', 'x_studio_inicio_de_proceso'],
    limit=50)
print(f'Procesos activos VILKUN: {len(procesos_vlk)}')
for p in procesos_vlk[:10]:
    print(f"  {p['name']}: state={p['state']}, qty={p['product_qty']}")

# Ver todos los picking types con sus IDs para cada warehouse
print('\n=== MAPPING COMPLETO PICKING_TYPE -> WAREHOUSE ===')
warehouses = {
    'VILKUN': 48,
    'SAN JOSE': 7,
    'RIO FUTURO': 1
}

for wh_name, wh_id in warehouses.items():
    pts = odoo.search_read('stock.picking.type', [['warehouse_id', '=', wh_id]], ['id', 'name'], limit=50)
    print(f'\n{wh_name} (wh_id={wh_id}):')
    for pt in pts:
        # Contar procesos activos con este picking type
        activos = len(odoo.search_read('mrp.production', [
            ['state', '!=', 'done'],
            ['state', '!=', 'cancel'],
            ['picking_type_id', '=', pt['id']]
        ], ['id'], limit=200))
        cerrados = len(odoo.search_read('mrp.production', [
            ['state', '=', 'done'],
            ['picking_type_id', '=', pt['id']]
        ], ['id'], limit=200))
        if activos > 0 or cerrados > 0:
            print(f"  PT {pt['id']}: {pt['name']} -> {activos} activos, {cerrados} cerrados")
