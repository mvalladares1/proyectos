from shared.odoo_client import OdooClient
odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

# Ver warehouses
wh = odoo.search_read('stock.warehouse', [], ['id', 'name', 'code'], limit=50)
print('Warehouses:')
for w in wh:
    print(f"  {w['id']}: {w['name']} ({w.get('code', '')})")

# Ver picking types del warehouse San Jose (7)
print('\nPicking types de San Jose (wh=7):')
pts_sj = odoo.search_read('stock.picking.type', [['warehouse_id', '=', 7]], ['id', 'name', 'sequence_code'], limit=50)
for pt in pts_sj:
    print(f"  {pt['id']}: {pt['name']} (code: {pt.get('sequence_code', '')})")

# Buscar procesos con picking_type de San Jose
print('\nBuscando procesos con picking_type de San Jose...')
pt_ids = [pt['id'] for pt in pts_sj]
if pt_ids:
    procesos_sj = odoo.search_read('mrp.production', [['picking_type_id', 'in', pt_ids]], 
        ['name', 'state', 'product_qty', 'qty_produced'], limit=50)
    print(f'Procesos de San Jose: {len(procesos_sj)}')
    for p in procesos_sj[:20]:
        print(f"  {p['name']}: state={p['state']}, qty={p['product_qty']}")

# Ver VILKUN tambien
print('\nPicking types de VILKUN (wh=48):')
pts_vlk = odoo.search_read('stock.picking.type', [['warehouse_id', '=', 48]], ['id', 'name', 'sequence_code'], limit=50)
for pt in pts_vlk:
    print(f"  {pt['id']}: {pt['name']} (code: {pt.get('sequence_code', '')})")
