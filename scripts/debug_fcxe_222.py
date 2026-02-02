"""
DEBUG: Inspeccionar FCXE 222
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(USERNAME, PASSWORD)

print("=" * 70)
print("DEBUG: FCXE 000222 en cuenta 11030101")
print("=" * 70)

# 1. Buscar el asiento
moves = odoo.search_read('account.move', [['name', '=', 'FCXE 000222']], ['id', 'name', 'date'])
if not moves:
    print("No se encontró el asiento FCXE 000222")
    sys.exit()

move_id = moves[0]['id']
print(f"Asiento ID: {move_id} | Name: {moves[0]['name']} | Date: {moves[0]['date']}")

# 2. Buscar líneas en 11030101 que mencionen FCXE 000222
acc = odoo.search_read('account.account', [['code', '=', '11030101']], ['id'])[0]
acc_id = acc['id']
print(f"Cuenta 11030101 ID: {acc_id}")

print(f"\nBuscando líneas en 11030101 con 'FCXE 000222' en nombre o asiento...")

lines = odoo.search_read(
    'account.move.line',
    [
        ['account_id', '=', acc_id],
        '|',
        ['name', 'ilike', 'FCXE 000222'],
        ['move_id', 'ilike', 'FCXE 000222']
    ],
    ['id', 'name', 'debit', 'credit', 'balance', 'move_id', 'date']
)

print(f"\nLíneas encontradas ({len(lines)}):")
total_balance = 0
for l in lines:
    move_id = l['move_id'][0] if isinstance(l['move_id'], (list, tuple)) else l['move_id']
    move_name = l['move_id'][1] if isinstance(l['move_id'], (list, tuple)) else str(l['move_id'])
    
    # Obtener fecha de pago del asiento
    move_info = odoo.search_read('account.move', [['id', '=', move_id]], ['x_studio_fecha_de_pago', 'invoice_date_due'])[0]
    fecha_pago = move_info.get('x_studio_fecha_de_pago')
    fecha_venc = move_info.get('invoice_date_due')
    
    print(f"  ID: {l['id']} | Date: {l['date']} | Move: {move_name}")
    print(f"    Fecha Pago Studio: {fecha_pago} | Vencimiento: {fecha_venc}")
    print(f"    Name: '{l['name']}'")
    print(f"    Debit: ${l['debit']:,.0f} | Credit: ${l['credit']:,.0f} | Balance: ${l['balance']:,.0f}")
    total_balance += l['balance']

print(f"\nTOTAL BALANCE: ${total_balance:,.0f}")
