"""Debug: Verificar procesos cerrados en febrero"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.odoo_client import OdooClient
from backend.utils import clean_record

# Credenciales
username = "mvalladares"
password = "Mv13662612"

odoo = OdooClient(username=username, password=password)

fecha_inicio = "2026-02-01"
fecha_fin = "2026-02-04"

print("=" * 80)
print(f"DEBUG: Procesos cerrados entre {fecha_inicio} y {fecha_fin}")
print("=" * 80)

# Buscar TODOS los procesos done sin filtro de fecha
print("\n1. Todos los procesos en estado 'done' (últimos 100):")
all_done = odoo.search_read(
    'mrp.production',
    [['state', '=', 'done']],
    ['name', 'date_finished', 'x_studio_termino_de_proceso', 'qty_produced'],
    limit=100,
    order='date_finished desc'
)

for p in all_done[:20]:
    print(f"  {p.get('name')}: date_finished={p.get('date_finished')}, x_studio_termino={p.get('x_studio_termino_de_proceso')}, qty={p.get('qty_produced')}")

# Buscar procesos cerrados por x_studio_termino_de_proceso
print(f"\n2. Procesos con x_studio_termino_de_proceso entre {fecha_inicio} y {fecha_fin}:")
por_termino = odoo.search_read(
    'mrp.production',
    [
        ['state', '=', 'done'],
        ['x_studio_termino_de_proceso', '>=', fecha_inicio],
        ['x_studio_termino_de_proceso', '<=', fecha_fin + ' 23:59:59']
    ],
    ['name', 'date_finished', 'x_studio_termino_de_proceso', 'qty_produced'],
    limit=200
)
print(f"  Encontrados: {len(por_termino)}")
for p in por_termino:
    print(f"    {p.get('name')}: termino={p.get('x_studio_termino_de_proceso')}")

# Buscar procesos cerrados por date_finished
print(f"\n3. Procesos con date_finished entre {fecha_inicio} y {fecha_fin}:")
por_finished = odoo.search_read(
    'mrp.production',
    [
        ['state', '=', 'done'],
        ['date_finished', '>=', fecha_inicio],
        ['date_finished', '<=', fecha_fin + ' 23:59:59']
    ],
    ['name', 'date_finished', 'x_studio_termino_de_proceso', 'qty_produced'],
    limit=200
)
print(f"  Encontrados: {len(por_finished)}")
for p in por_finished:
    print(f"    {p.get('name')}: date_finished={p.get('date_finished')}, termino={p.get('x_studio_termino_de_proceso')}")

# Buscar el proceso específico MOCS/L01007
print("\n4. Buscando proceso MOCS/L01007:")
mocs = odoo.search_read(
    'mrp.production',
    [['name', 'ilike', 'MOCS/L01007']],
    ['name', 'state', 'date_finished', 'x_studio_termino_de_proceso', 'qty_produced', 'product_qty'],
    limit=10
)
if mocs:
    for p in mocs:
        print(f"  Encontrado: {p}")
else:
    print("  NO ENCONTRADO")

# Contar por día específico - 3 de febrero
print("\n5. Procesos cerrados específicamente el 3 de febrero:")
feb3 = odoo.search_read(
    'mrp.production',
    [
        ['state', '=', 'done'],
        '|',
        '&', ['x_studio_termino_de_proceso', '>=', '2026-02-03'],
             ['x_studio_termino_de_proceso', '<', '2026-02-04'],
        '&', ['date_finished', '>=', '2026-02-03'],
             ['date_finished', '<', '2026-02-04']
    ],
    ['name', 'date_finished', 'x_studio_termino_de_proceso'],
    limit=200
)
print(f"  Encontrados: {len(feb3)}")
for p in feb3:
    print(f"    {p.get('name')}: date_finished={p.get('date_finished')}, termino={p.get('x_studio_termino_de_proceso')}")

print("\n" + "=" * 80)
