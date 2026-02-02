"""Debug: Verificar facturas de cliente"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from shared.odoo_client import OdooClient

odoo = OdooClient('mvalladares@riofuturo.cl', 'c0766224bec30cac071ffe43a858c9ccbd521ddd')

# Solo facturas cliente publicadas con fecha pago en sept
domain = [
    ['state', '=', 'posted'],
    ['move_type', 'in', ['out_invoice', 'out_refund']],
    '|',
    '&', '&',
        ['x_studio_fecha_de_pago', '!=', False],
        ['x_studio_fecha_de_pago', '>=', '2025-09-01'],
        ['x_studio_fecha_de_pago', '<=', '2025-09-30'],
    '&', '&',
        ['x_studio_fecha_de_pago', '=', False],
        ['date', '>=', '2025-09-01'],
        ['date', '<=', '2025-09-30'],
]

moves = odoo.search_read('account.move', domain, ['id', 'name', 'x_studio_fecha_de_pago', 'date', 'move_type', 'amount_total'])
print(f'Facturas cliente publicadas con pago en Sept: {len(moves)}')

total = sum(m['amount_total'] for m in moves)
print(f'Total amount_total: ${total:,.0f}')

# Buscar lineas en 11030101 de estas facturas
acc = odoo.search_read('account.account', [['code', '=', '11030101']], ['id'])[0]
move_ids = [m['id'] for m in moves]

lines = odoo.search_read(
    'account.move.line',
    [['move_id', 'in', move_ids], ['account_id', '=', acc['id']]],
    ['move_id', 'balance', 'name'],
    limit=100
)
print(f'\nLineas en 11030101: {len(lines)}')
total_balance = sum(l['balance'] for l in lines)
print(f'Total balance en 11030101: ${total_balance:,.0f}')

# Mostrar algunas
print('\nPrimeras 10 facturas:')
for m in moves[:10]:
    fp = m.get('x_studio_fecha_de_pago') or 'N/A'
    print(f"  {m['name']} | tipo={m['move_type']} | fecha_pago={fp} | monto=${m['amount_total']:,.0f}")
