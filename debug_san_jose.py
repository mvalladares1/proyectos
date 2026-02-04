from shared.odoo_client import OdooClient

odoo = OdooClient(
    username='mvalladares@riofuturo.cl', 
    password='c0766224bec30cac071ffe43a858c9ccbd521ddd'
)

# Buscar procesos cerrados recientes con sala que contenga SAN JOSE
domain = [
    ['state', '=', 'done'],
    ['x_studio_sala_de_proceso', 'ilike', 'san jose']
]
cerrados_sj = odoo.search_read('mrp.production', domain, 
    ['name', 'state', 'x_studio_sala_de_proceso', 'x_studio_termino_de_proceso', 'date_finished', 'qty_produced'],
    limit=20, order='date_finished desc')

print(f'Procesos cerrados con sala SAN JOSE: {len(cerrados_sj)}')
for p in cerrados_sj[:10]:
    name = p.get('name', '')
    sala = p.get('x_studio_sala_de_proceso', '')
    termino = p.get('x_studio_termino_de_proceso', '')
    finished = p.get('date_finished', '')
    print(f'  {name}: sala={sala} | termino={termino} | finished={finished}')

# Buscar cerrados hoy de SAN JOSE
from datetime import datetime, timedelta
hoy = datetime.now().strftime('%Y-%m-%d')
print(f'\n--- Cerrados HOY ({hoy}) de SAN JOSE ---')

domain_hoy = [
    ['state', '=', 'done'],
    ['x_studio_sala_de_proceso', 'ilike', 'san jose'],
    ['x_studio_termino_de_proceso', '>=', hoy],
    ['x_studio_termino_de_proceso', '<', (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')]
]
cerrados_hoy = odoo.search_read('mrp.production', domain_hoy,
    ['name', 'state', 'x_studio_sala_de_proceso', 'x_studio_termino_de_proceso', 'date_finished', 'qty_produced'],
    limit=50)

print(f'Encontrados: {len(cerrados_hoy)}')
for p in cerrados_hoy[:20]:
    name = p.get('name', '')
    sala = p.get('x_studio_sala_de_proceso', '')
    termino = p.get('x_studio_termino_de_proceso', '')
    finished = p.get('date_finished', '')
    qty = p.get('qty_produced', 0)
    print(f'  {name}: qty={qty} | sala={sala} | termino={termino} | finished={finished}')

# Buscar con date_finished en lugar de x_studio_termino_de_proceso
print(f'\n--- Cerrados HOY ({hoy}) con date_finished ---')
domain_finished = [
    ['state', '=', 'done'],
    ['x_studio_sala_de_proceso', 'ilike', 'san jose'],
    ['date_finished', '>=', hoy],
    ['date_finished', '<', (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')]
]
cerrados_finished = odoo.search_read('mrp.production', domain_finished,
    ['name', 'state', 'x_studio_sala_de_proceso', 'x_studio_termino_de_proceso', 'date_finished', 'qty_produced'],
    limit=50)

print(f'Encontrados: {len(cerrados_finished)}')
for p in cerrados_finished[:20]:
    name = p.get('name', '')
    sala = p.get('x_studio_sala_de_proceso', '')
    termino = p.get('x_studio_termino_de_proceso', '')
    finished = p.get('date_finished', '')
    qty = p.get('qty_produced', 0)
    print(f'  {name}: qty={qty} | termino={termino} | finished={finished}')
