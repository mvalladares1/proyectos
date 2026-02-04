from shared.odoo_client import OdooClient
odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

# Buscar procesos con VLK en nombre  
domain = [['name', 'ilike', 'vlk'], ['state', '!=', 'cancel']]
vlk = odoo.search_read('mrp.production', domain, ['name', 'state', 'picking_type_id', 'qty_produced', 'product_qty'], limit=100)
print(f'Procesos VLK: {len(vlk)} total')

# Agrupar por estado
estados = {}
for p in vlk:
    s = p['state']
    estados[s] = estados.get(s, 0) + 1
print(f'Por estado: {estados}')

# Ver ejemplos
activos = [p for p in vlk if p['state'] != 'done']
print(f'\nActivos VLK: {len(activos)}')
for p in activos[:10]:
    print(f"  {p['name']}: state={p['state']}, qty={p['product_qty']}, picking={p.get('picking_type_id')}")

cerrados = [p for p in vlk if p['state'] == 'done']
print(f'\nCerrados VLK (muestra): {len(cerrados)}')
for p in cerrados[:10]:
    print(f"  {p['name']}: qty_produced={p['qty_produced']}")

# Ver procesos CERRADOS hoy
from datetime import datetime
hoy = datetime.now().strftime('%Y-%m-%d')
print(f'\n=== PROCESOS CERRADOS HOY ({hoy}) CON VLK ===')
domain_hoy = [
    ['name', 'ilike', 'vlk'],
    ['state', '=', 'done'],
    ['date_finished', '>=', hoy]
]
vlk_hoy = odoo.search_read('mrp.production', domain_hoy, 
    ['name', 'qty_produced', 'date_finished', 'x_studio_termino_de_proceso'], limit=50)
print(f'VLK cerrados hoy: {len(vlk_hoy)}')
for p in vlk_hoy:
    print(f"  {p['name']}: qty={p['qty_produced']}, finished={p.get('date_finished')}, termino={p.get('x_studio_termino_de_proceso')}")
