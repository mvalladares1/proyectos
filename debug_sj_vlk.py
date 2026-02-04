from shared.odoo_client import OdooClient
odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

# Buscar procesos con SJ o VLK en el nombre
domain_sj = [['name', 'ilike', 'sj']]
sj = odoo.search_read('mrp.production', domain_sj, ['name', 'state'], limit=50)
print(f'Procesos con SJ en nombre: {len(sj)}')
for p in sj[:10]:
    print(f"  {p['name']}: {p['state']}")

domain_vlk = [['name', 'ilike', 'vlk']]
vlk = odoo.search_read('mrp.production', domain_vlk, ['name', 'state'], limit=50)
print(f'\nProcesos con VLK en nombre: {len(vlk)}')
for p in vlk[:10]:
    print(f"  {p['name']}: {p['state']}")

domain_vilk = [['name', 'ilike', 'vilk']]
vilk = odoo.search_read('mrp.production', domain_vilk, ['name', 'state'], limit=50)
print(f'\nProcesos con VILK en nombre: {len(vilk)}')

domain_san = [['name', 'ilike', 'san']]
san = odoo.search_read('mrp.production', domain_san, ['name', 'state'], limit=50)
print(f'\nProcesos con SAN en nombre: {len(san)}')
for p in san[:10]:
    print(f"  {p['name']}: {p['state']}")

# Buscar procesos recientes cerrados (ultimos 7 dias)
from datetime import datetime, timedelta
hace_7_dias = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
print(f'\n=== PROCESOS CERRADOS ULTIMOS 7 DIAS (desde {hace_7_dias}) ===')
domain_recientes = [
    ['state', '=', 'done'],
    ['date_finished', '>=', hace_7_dias]
]
recientes = odoo.search_read('mrp.production', domain_recientes, 
    ['name', 'qty_produced', 'date_finished', 'x_studio_termino_de_proceso', 'picking_type_id'],
    limit=100, order='date_finished desc')
print(f'Total cerrados ultimos 7 dias: {len(recientes)}')
for p in recientes[:30]:
    name = p['name']
    qty = p.get('qty_produced', 0)
    finished = p.get('date_finished', '')
    termino = p.get('x_studio_termino_de_proceso', '')
    pt = p.get('picking_type_id', [None, ''])
    pt_name = pt[1] if pt else ''
    print(f"  {name}: qty={qty} | finished={finished} | termino={termino} | picking={pt_name}")
