#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/feli/proyectos')
from shared.odoo_client import OdooClient
import os

client = OdooClient(username='frios@riofuturo.cl', password='413c17f8c0a0ebe211cda26c094c2bbb47fce5c6')

print("=" * 80)
print("MOVES DONDE 039351 ES OUTPUT (EXCLUYENDO RF/INT/):")
print("=" * 80)

moves = client.search_read(
    'stock.move.line',
    [
        ('result_package_id.name', '=', '039351'),
        ('state', '=', 'done'),
        ('qty_done', '>', 0),
        ('reference', 'not ilike', 'RF/INT/'),
        ('reference', 'not ilike', 'Quantity Updated'),
        ('reference', 'not ilike', 'Cantidad de producto confirmada')
    ],
    ['id', 'reference', 'package_id', 'date'],
    limit=10
)

for m in moves:
    pkg = m.get('package_id')
    pkg_name = pkg[1] if pkg else 'None (creación)'
    print(f'  - {m["reference"]}: {pkg_name} -> 039351 (Move {m["id"]}, {m["date"][:10]})')
print(f'\nTotal: {len(moves)} moves')

if len(moves) == 0:
    print("\n❌ PROBLEMA IDENTIFICADO:")
    print("El pallet 039351 SOLO aparece como output en RF/INT/00590 (que está excluido)")
    print("Por lo tanto, NO DEBERÍA estar en la trazabilidad de S00531")
    print("\nEsto significa que:")
    print("  1. 039351 entra por expansión de hermanos (include_siblings)")
    print("  2. O hay otro proceso no excluido que lo conecta")
