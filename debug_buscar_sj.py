from shared.odoo_client import OdooClient
odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

# Buscar procesos con "san" o "jose" o "sj" en cualquier campo de texto
print('=== BUSCANDO PROCESOS CON SAN JOSE EN CUALQUIER CAMPO ===')

# En el nombre
domain_name = [['name', 'ilike', 'sj']]
sj_name = odoo.search_read('mrp.production', domain_name, ['name', 'state'], limit=20)
print(f'Con "SJ" en nombre: {len(sj_name)}')
for p in sj_name[:5]:
    print(f"  {p['name']}: {p['state']}")

domain_san = [['name', 'ilike', 'san']]
san_name = odoo.search_read('mrp.production', domain_san, ['name', 'state'], limit=20)
print(f'Con "SAN" en nombre: {len(san_name)}')

# Buscar con picking_type 222 o 221
print('\n=== PROCESOS CON PICKING TYPE 222 o 221 (San Jose) ===')
domain_pt = [['picking_type_id', 'in', [221, 222]]]
sj_pt = odoo.search_read('mrp.production', domain_pt, ['name', 'state', 'picking_type_id'], limit=50)
print(f'Con picking_type San Jose: {len(sj_pt)}')

# Quiza los procesos de San Jose tienen otra estructura de nombre?
# Buscar procesos recientes cerrados hoy para ver si alguno es de San Jose
from datetime import datetime
print('\n=== TODOS LOS PROCESOS CERRADOS HOY ===')
hoy = datetime.now().strftime('%Y-%m-%d')
domain_hoy = [['state', '=', 'done'], ['date_finished', '>=', hoy]]
cerrados_hoy = odoo.search_read('mrp.production', domain_hoy, 
    ['name', 'qty_produced', 'picking_type_id', 'x_studio_sala_de_proceso'], limit=100)
print(f'Total cerrados hoy: {len(cerrados_hoy)}')
for p in cerrados_hoy[:30]:
    pt = p.get('picking_type_id', [None, ''])
    pt_name = pt[1] if pt else 'N/A'
    sala = p.get('x_studio_sala_de_proceso', '') or 'N/A'
    print(f"  {p['name']}: qty={p['qty_produced']:.1f}, pt={pt_name}, sala={sala}")

# Quiza SAN JOSE se refiere a una sala?
print('\n=== PROCESOS CON SALA QUE CONTIENE "SAN" ===')
domain_sala = [['x_studio_sala_de_proceso', 'ilike', 'san']]
san_sala = odoo.search_read('mrp.production', domain_sala, ['name', 'state', 'x_studio_sala_de_proceso'], limit=20)
print(f'Con "SAN" en sala: {len(san_sala)}')

# Ver todas las salas
print('\n=== TODAS LAS SALAS UNICAS ===')
all_procesos = odoo.search_read('mrp.production', [], ['x_studio_sala_de_proceso'], limit=1000)
salas = set()
for p in all_procesos:
    sala = p.get('x_studio_sala_de_proceso')
    if sala and sala != False:
        salas.add(str(sala))
print(f'Salas encontradas: {salas}')
