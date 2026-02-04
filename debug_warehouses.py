from shared.odoo_client import OdooClient
odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

# Buscar picking types con SAN JOSE o SJ
picking_types = odoo.search_read('stock.picking.type', [], ['id', 'name', 'warehouse_id'], limit=200)
print('Todos los picking types:')
for pt in picking_types:
    name = pt.get('name', '')
    wh = pt.get('warehouse_id', '')
    pt_id = pt.get('id', '')
    name_lower = name.lower()
    if 'san' in name_lower or 'jose' in name_lower or 'sj' in name_lower or 'vilk' in name_lower or 'vlk' in name_lower:
        print(f'  ***ID={pt_id}: {name} | WH={wh}')
    elif 'manuf' in name_lower or 'produc' in name_lower:
        print(f'  ID={pt_id}: {name} | WH={wh}')

# Ver warehouses
print('\n\nWarehouses:')
warehouses = odoo.search_read('stock.warehouse', [], ['id', 'name', 'code'], limit=50)
for wh in warehouses:
    print(f"  ID={wh['id']}: {wh['name']} ({wh.get('code', '')})")

# Ahora buscar procesos por warehouse
print('\n\nProcesos activos por warehouse:')
for wh in warehouses:
    wh_id = wh['id']
    wh_name = wh['name']
    # Buscar picking types de este warehouse
    pts = odoo.search_read('stock.picking.type', [['warehouse_id', '=', wh_id]], ['id'], limit=50)
    pt_ids = [p['id'] for p in pts]
    if pt_ids:
        domain = [
            ['state', '!=', 'done'],
            ['state', '!=', 'cancel'],
            ['picking_type_id', 'in', pt_ids]
        ]
        count = odoo.search_count('mrp.production', domain)
        print(f"  {wh_name}: {count} procesos activos")
