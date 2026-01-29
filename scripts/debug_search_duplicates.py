"""
DEBUG: Buscar todas las lineas de 11030101 con nombre 'FAC 000256'
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("DEBUG: BUSCAR LINEAS DUPLICADAS")
print("=" * 70)

odoo = OdooClient(USERNAME, PASSWORD)

# Buscar ID de 11030101
acc_1103 = odoo.search_read('account.account', [['code', '=', '11030101']], ['id'])[0]['id']
print(f"ID 11030101: {acc_1103}")

# Buscar todas las lineas con ese nombre y cuenta
lineas = odoo.search_read(
    'account.move.line',
    [
        ['account_id', '=', acc_1103],
        ['name', '=', 'FAC 000256']
    ],
    ['id', 'move_id', 'date', 'debit', 'credit', 'balance', 'name']
)

print(f"Total lineas encontradas: {len(lineas)}")
for l in lineas:
    print(f"  Line ID: {l['id']} | Date: {l['date']} | Balance: ${l['balance']:,.0f} | Move: {l['move_id'][1]} (ID {l['move_id'][0]})")
