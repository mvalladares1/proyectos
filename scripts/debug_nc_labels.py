"""
DEBUG: Investigar notas de crédito en cuenta 11030101
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("DEBUG: Notas de Crédito en cuenta 11030101")
print("=" * 70)

odoo = OdooClient(USERNAME, PASSWORD)

# Buscar cuenta 11030101
acc = odoo.search_read('account.account', [['code', '=', '11030101']], ['id'])[0]
acc_id = acc['id']

# Buscar líneas de NCXE (notas de crédito exportación) en Sep 2025
print("\nBuscando líneas con 'NCXE' en move_id.name (Sep 2025)...")

# Primero buscar los asientos de tipo NC
nc_moves = odoo.search_read(
    'account.move',
    [
        ['name', '=like', 'NCXE%'],
        ['date', '>=', '2025-09-01'],
        ['date', '<=', '2025-09-30'],
        ['state', '=', 'posted']
    ],
    ['id', 'name', 'amount_total', 'date', 'journal_id']
)

print(f"\nAsientos NCXE encontrados: {len(nc_moves)}")
for nc in nc_moves:
    print(f"  {nc['name']}: ${nc['amount_total']:,.0f} | Journal: {nc['journal_id']}")

# Ahora buscar las líneas en cuenta 11030101 de estos asientos
nc_move_ids = [nc['id'] for nc in nc_moves]
if nc_move_ids:
    lines = odoo.search_read(
        'account.move.line',
        [
            ['move_id', 'in', nc_move_ids],
            ['account_id', '=', acc_id]
        ],
        ['id', 'move_id', 'name', 'debit', 'credit', 'balance']
    )
    
    print(f"\nLíneas en 11030101 de NC: {len(lines)}")
    for l in lines:
        move_name = l['move_id'][1] if isinstance(l['move_id'], (list, tuple)) else str(l['move_id'])
        print(f"  {move_name} | name='{l['name']}' | D: ${l['debit']:,.0f} | C: ${l['credit']:,.0f} | Bal: ${l['balance']:,.0f}")

# También ver qué campo name tienen las líneas normales
print("\n" + "=" * 70)
print("Verificando campo 'name' en líneas de 11030101 (Sep 2025)")
print("=" * 70)

all_lines = odoo.search_read(
    'account.move.line',
    [
        ['account_id', '=', acc_id],
        ['date', '>=', '2025-09-01'],
        ['date', '<=', '2025-09-30'],
        ['parent_state', '=', 'posted']
    ],
    ['id', 'move_id', 'name', 'balance'],
    limit=30
)

print(f"\nPrimeras 30 líneas:")
for l in all_lines[:30]:
    move_name = l['move_id'][1] if isinstance(l['move_id'], (list, tuple)) else str(l['move_id'])
    line_name = l['name'] if l['name'] else "(vacío)"
    print(f"  {move_name[:20]:20} | name='{line_name[:30]}' | ${l['balance']:,.0f}")
