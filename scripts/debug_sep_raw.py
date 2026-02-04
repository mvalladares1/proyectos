"""
DEBUG: Listar pagos reales (BANK entries) de Septiembre 2025
Comparar con lo que Odoo muestra en la lista de facturas
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("DEBUG: Movimientos de Efectivo SEP 2025")
print("=" * 70)

odoo = OdooClient(USERNAME, PASSWORD)

# Buscar cuentas de banco (1101)
bank_accs = odoo.search_read(
    'account.account',
    [['code', '=like', '1101%']],
    ['id', 'code', 'name']
)
bank_ids = [a['id'] for a in bank_accs]
print(f"Cuentas Banco: {[a['code'] for a in bank_accs]}")

# Buscar movimientos de banco en Septiembre 2025
movs = odoo.search_read(
    'account.move.line',
    [
        ['account_id', 'in', bank_ids],
        ['parent_state', '=', 'posted'],
        ['date', '>=', '2025-09-01'],
        ['date', '<=', '2025-09-30']
    ],
    ['id', 'move_id', 'date', 'name', 'debit', 'credit', 'balance'],
    limit=500
)

print(f"\nTotal líneas banco SEP 2025: {len(movs)}")

# Sumar solo entradas (débitos - dinero que entra)
total_entradas = sum(m['debit'] for m in movs)
total_salidas = sum(m['credit'] for m in movs)
neto = total_entradas - total_salidas

print(f"Total Débitos (Entradas): ${total_entradas:,.0f}")
print(f"Total Créditos (Salidas): ${total_salidas:,.0f}")
print(f"Neto: ${neto:,.0f}")

# Ahora buscar líneas de 11030101 (CxC) en SEP 2025
print("\n" + "=" * 70)
print("DEBUG: Movimientos CxC (11030101) SEP 2025")
print("=" * 70)

cxc_acc = odoo.search_read('account.account', [['code', '=', '11030101']], ['id'])[0]['id']

cxc_movs = odoo.search_read(
    'account.move.line',
    [
        ['account_id', '=', cxc_acc],
        ['parent_state', '=', 'posted'],
        ['date', '>=', '2025-09-01'],
        ['date', '<=', '2025-09-30']
    ],
    ['id', 'move_id', 'date', 'name', 'debit', 'credit', 'balance'],
    limit=500
)

print(f"Total líneas CxC SEP 2025: {len(cxc_movs)}")

total_deb = sum(m['debit'] for m in cxc_movs)
total_cred = sum(m['credit'] for m in cxc_movs)
print(f"Débitos (Nuevas cuentas): ${total_deb:,.0f}")
print(f"Créditos (Cobros): ${total_cred:,.0f}")
print(f"Neto CxC: ${total_deb - total_cred:,.0f}")

# Desglose por tipo de asiento
print("\nDesglose por Journal:")
journals = {}
for m in cxc_movs:
    move_name = m['move_id'][1] if isinstance(m['move_id'], (list, tuple)) else str(m['move_id'])
    prefix = move_name.split('/')[0] if '/' in move_name else move_name[:4]
    if prefix not in journals:
        journals[prefix] = {'debit': 0, 'credit': 0, 'count': 0}
    journals[prefix]['debit'] += m['debit']
    journals[prefix]['credit'] += m['credit']
    journals[prefix]['count'] += 1

for j, data in sorted(journals.items()):
    print(f"  {j}: {data['count']} lines | D: ${data['debit']:,.0f} | C: ${data['credit']:,.0f}")
