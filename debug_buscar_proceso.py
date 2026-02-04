"""Debug: Buscar WH/Transf/00959 en Odoo"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.odoo_client import OdooClient

username = "mjaramillo@riofuturo.cl"
password = "rioFuturo-20"

odoo = OdooClient(username=username, password=password)

print("=" * 70)
print("Buscando WH/Transf/00959 en diferentes modelos...")
print("=" * 70)

# Buscar en mrp.production
print("\n1. Buscando en mrp.production:")
try:
    result = odoo.search_read(
        'mrp.production',
        [['name', 'ilike', 'WH/Transf/00959']],
        ['name', 'state', 'date_finished', 'x_studio_termino_de_proceso', 'product_id'],
        limit=10
    )
    if result:
        for r in result:
            print(f"   Encontrado: {r}")
    else:
        print("   No encontrado en mrp.production")
except Exception as e:
    print(f"   Error: {e}")

# Buscar en stock.picking
print("\n2. Buscando en stock.picking:")
try:
    result = odoo.search_read(
        'stock.picking',
        [['name', 'ilike', 'WH/Transf/00959']],
        ['name', 'state', 'date_done', 'scheduled_date', 'origin', 'picking_type_id'],
        limit=10
    )
    if result:
        for r in result:
            print(f"   Encontrado: {r}")
    else:
        print("   No encontrado en stock.picking")
except Exception as e:
    print(f"   Error: {e}")

# Buscar procesos cerrados hoy (4 febrero)
print("\n3. Procesos mrp.production cerrados hoy (4 febrero):")
try:
    result = odoo.search_read(
        'mrp.production',
        [
            ['state', '=', 'done'],
            '|',
            ['x_studio_termino_de_proceso', '>=', '2026-02-04'],
            ['date_finished', '>=', '2026-02-04']
        ],
        ['name', 'state', 'date_finished', 'x_studio_termino_de_proceso', 'qty_produced'],
        limit=20
    )
    print(f"   Encontrados: {len(result)}")
    for r in result:
        print(f"   - {r.get('name')}: termino={r.get('x_studio_termino_de_proceso')}, finished={r.get('date_finished')}")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 70)
