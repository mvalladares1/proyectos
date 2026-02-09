from shared.odoo_client import OdooClient
from datetime import datetime

odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

hoy = datetime.now().strftime('%Y-%m-%d')
print(f'=== VERIFICANDO CERRADOS HOY ({hoy}) ===\n')

# 1. Buscar TODOS los cerrados hoy por date_finished
print('1. CERRADOS HOY por date_finished:')
domain1 = [
    ['state', '=', 'done'],
    ['date_finished', '>=', hoy],
    ['date_finished', '<', hoy + ' 23:59:59']
]
cerrados_finished = odoo.search_read('mrp.production', domain1, 
    ['name', 'qty_produced', 'date_finished', 'x_studio_termino_de_proceso', 'x_studio_sala_de_proceso'],
    limit=100, order='date_finished desc')
print(f'   Total: {len(cerrados_finished)}')
for p in cerrados_finished[:20]:
    sala = p.get('x_studio_sala_de_proceso', '') or 'N/A'
    print(f"   {p['name']}: qty={p['qty_produced']:.1f}, finished={p['date_finished']}, termino={p.get('x_studio_termino_de_proceso')}, sala={sala}")

# 2. Buscar por x_studio_termino_de_proceso
print('\n2. CERRADOS HOY por x_studio_termino_de_proceso:')
domain2 = [
    ['state', '=', 'done'],
    ['x_studio_termino_de_proceso', '>=', hoy],
    ['x_studio_termino_de_proceso', '<=', hoy + ' 23:59:59']
]
cerrados_termino = odoo.search_read('mrp.production', domain2,
    ['name', 'qty_produced', 'date_finished', 'x_studio_termino_de_proceso', 'x_studio_sala_de_proceso'],
    limit=100, order='x_studio_termino_de_proceso desc')
print(f'   Total: {len(cerrados_termino)}')
for p in cerrados_termino[:20]:
    sala = p.get('x_studio_sala_de_proceso', '') or 'N/A'
    print(f"   {p['name']}: qty={p['qty_produced']:.1f}, finished={p['date_finished']}, termino={p.get('x_studio_termino_de_proceso')}, sala={sala}")

# 3. Ver si hay diferencia (algunos tienen termino pero no finished hoy, o viceversa)
ids_finished = set(p['id'] for p in cerrados_finished)
ids_termino = set(p['id'] for p in cerrados_termino)

print(f'\n3. ANÁLISIS:')
print(f'   Por date_finished: {len(ids_finished)} procesos')
print(f'   Por x_studio_termino_de_proceso: {len(ids_termino)} procesos')
print(f'   En ambos: {len(ids_finished & ids_termino)}')
print(f'   Solo en finished: {len(ids_finished - ids_termino)}')
print(f'   Solo en termino: {len(ids_termino - ids_finished)}')

# 4. Ver el dominio problemático actual
print('\n4. PROBANDO DOMINIO ACTUAL DEL SERVICIO:')
domain_actual = [
    ['state', '=', 'done'],
    '|',
    '&', ['x_studio_termino_de_proceso', '>=', hoy],
         ['x_studio_termino_de_proceso', '<=', hoy + ' 23:59:59'],
    '&', ['x_studio_termino_de_proceso', '=', False],
    '&', ['date_finished', '>=', hoy],
         ['date_finished', '<=', hoy + ' 23:59:59']
]
cerrados_dominio = odoo.search_read('mrp.production', domain_actual,
    ['name', 'qty_produced', 'date_finished', 'x_studio_termino_de_proceso'],
    limit=100)
print(f'   Total con dominio actual: {len(cerrados_dominio)}')
for p in cerrados_dominio[:10]:
    print(f"   {p['name']}: finished={p['date_finished']}, termino={p.get('x_studio_termino_de_proceso')}")
