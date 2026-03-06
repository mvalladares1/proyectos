#!/usr/bin/env python3
"""Debug: Movimientos de cuenta 11060108"""
import xmlrpc.client

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

# Buscar la cuenta 11060108
cuentas = models.execute_kw(DB, uid, PASSWORD,
    'account.account', 'search_read',
    [[('code', '=', '11060108')]],
    {'fields': ['id', 'code', 'name']}
)
print('CUENTA 11060108:')
for c in cuentas:
    print(f"  ID: {c['id']} - {c['code']} - {c['name']}")

if cuentas:
    cuenta_id = cuentas[0]['id']
    
    # Buscar movimientos de marzo 2026
    movimientos = models.execute_kw(DB, uid, PASSWORD,
        'account.move.line', 'search_read',
        [[
            ('account_id', '=', cuenta_id),
            ('date', '>=', '2026-03-01'),
            ('date', '<=', '2026-03-31'),
            ('parent_state', '=', 'posted')
        ]],
        {
            'fields': ['id', 'date', 'debit', 'credit', 'balance', 'partner_id', 'move_id', 'journal_id'],
            'limit': 50
        }
    )
    
    print(f'\nMOVIMIENTOS EN MARZO 2026: {len(movimientos)}')
    for m in movimientos:
        partner = m.get('partner_id')
        partner_name = partner[1][:30] if isinstance(partner, (list, tuple)) and len(partner) > 1 else 'N/A'
        journal = m.get('journal_id')
        journal_name = journal[1] if isinstance(journal, (list, tuple)) and len(journal) > 1 else 'N/A'
        move = m.get('move_id')
        move_name = move[1] if isinstance(move, (list, tuple)) and len(move) > 1 else 'N/A'
        print(f"  {m['date']} | D:{m['debit']:>12,.0f} C:{m['credit']:>12,.0f} | {partner_name:30} | {journal_name} | {move_name}")
    
    # Buscar movimientos de todo 2026
    movimientos_2026 = models.execute_kw(DB, uid, PASSWORD,
        'account.move.line', 'search_read',
        [[
            ('account_id', '=', cuenta_id),
            ('date', '>=', '2026-01-01'),
            ('date', '<=', '2026-12-31'),
            ('parent_state', '=', 'posted')
        ]],
        {
            'fields': ['id', 'date', 'debit', 'credit', 'balance', 'partner_id'],
            'limit': 100
        }
    )
    
    print(f'\nMOVIMIENTOS EN 2026: {len(movimientos_2026)}')
    total_debit = sum(m.get('debit', 0) for m in movimientos_2026)
    total_credit = sum(m.get('credit', 0) for m in movimientos_2026)
    print(f'  Total Debitos: {total_debit:,.0f}')
    print(f'  Total Creditos: {total_credit:,.0f}')
    print(f'  Balance neto: {total_debit - total_credit:,.0f}')
