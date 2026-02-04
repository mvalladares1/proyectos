"""
Debug: Ver movimientos de cuentas sin etiquetas
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

svc = FlujoCajaService(USERNAME, PASSWORD)

# Buscar IDs de las cuentas sin etiquetas
cuentas_sin_etiq = ['21010102', '21010101', '21030201']
accs = svc.odoo_manager.odoo.search_read('account.account', [['code', 'in', cuentas_sin_etiq]], ['id', 'code', 'name'])

for a in accs:
    print(f"\n{a['code']}: ID={a['id']} - {a['name'][:40]}")
    
    # Buscar movimientos con etiquetas para esta cuenta
    movs = svc.odoo_manager.odoo.search_read(
        'account.move.line',
        [['account_id', '=', a['id']], ['date', '>=', '2026-01-01'], ['date', '<=', '2026-02-03'], ['parent_state', '=', 'posted']],
        ['id', 'name', 'debit', 'credit', 'date'],
        limit=10
    )
    print(f"  Movimientos: {len(movs)}")
    for m in movs:
        print(f"    {m['date']}: {m['name'][:50]} D:{m['debit']:,.0f} C:{m['credit']:,.0f}")
