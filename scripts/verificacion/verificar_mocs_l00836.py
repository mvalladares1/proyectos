#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/feli/proyectos')
from shared.odoo_client import OdooClient

client = OdooClient(username='frios@riofuturo.cl', password='413c17f8c0a0ebe211cda26c094c2bbb47fce5c6')

print("=" * 80)
print("¿HAY CONEXIÓN ENTRE MOCS/L00836 Y S00531?")
print("=" * 80)

# Pallets en MOCS/L00836
mocs_moves = client.search_read(
    'stock.move.line',
    [
        ('reference', '=', 'MOCS/L00836'),
        ('state', '=', 'done'),
        ('package_id', '!=', False)
    ],
    ['package_id'],
    limit=200
)

mocs_pallets = {m['package_id'][1] for m in mocs_moves if m.get('package_id')}
print(f'\nPallets en MOCS/L00836: {len(mocs_pallets)}')
if len(mocs_pallets) <= 50:
    print(f'Lista completa: {", ".join(sorted(mocs_pallets))}')
else:
    print(f'Primeros 30: {", ".join(sorted(list(mocs_pallets))[:30])}')

# Pallets en S00531
picking = client.search_read(
    'stock.picking',
    [
        ('origin', '=', 'S00531'),
        ('picking_type_id.code', '=', 'outgoing'),
        ('state', '=', 'done')
    ],
    ['id']
)[0]

sale_moves = client.search_read(
    'stock.move.line',
    [
        ('picking_id', '=', picking['id']),
        ('package_id', '!=', False),
        ('state', '=', 'done')
    ],
    ['package_id'],
    limit=100
)

sale_pallets = {m['package_id'][1] for m in sale_moves if m.get('package_id')}
print(f'\nPallets en S00531: {len(sale_pallets)}')

# Intersección
common = mocs_pallets & sale_pallets
if common:
    print(f'\n✓ ENCONTRADO: {len(common)} pallets en común entre MOCS/L00836 y S00531:')
    for p in sorted(common):
        print(f'  - {p}')
    print('\nEsto explica la conexión: MOCS/L00836 está en la cadena de S00531')
else:
    print('\n✗ No hay pallets en común entre MOCS/L00836 y S00531')
    print('\nPero 039351 está en MOCS/L00836...')
    print('Entonces, ¿cómo entra 039351 a la trazabilidad?')
    print('\nPosibilidades:')
    print('  1. include_siblings está expandiendo hermanos del proceso')
    print('  2. Hay otra conexión indirecta')
    print('  3. Error en el algoritmo de trazabilidad')

print("\n" + "=" * 80)
