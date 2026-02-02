"""Debug: Buscar líneas sin nombre"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from shared.odoo_client import OdooClient

odoo = OdooClient('mvalladares@riofuturo.cl', 'c0766224bec30cac071ffe43a858c9ccbd521ddd')

# Buscar lineas sin nombre en 11030101 durante sept
acc = odoo.search_read('account.account', [['code', '=', '11030101']], ['id'])[0]
lines = odoo.search_read(
    'account.move.line',
    [
        ['account_id', '=', acc['id']],
        ['date', '>=', '2025-09-01'],
        ['date', '<=', '2025-09-30'],
        '|', ['name', '=', False], ['name', '=', '']
    ],
    ['id', 'name', 'balance', 'move_id', 'date'],
    limit=20
)

print(f'Lineas sin nombre en 11030101 (Sept 2025): {len(lines)}')
total = 0
for l in lines[:10]:
    move = l['move_id'][1] if isinstance(l['move_id'], list) else str(l['move_id'])
    print(f"  ID={l['id']} | Move={move} | Balance={l['balance']:,.0f}")
    total += l['balance']
print(f"\nTotal balance sin nombre: {total:,.0f}")
