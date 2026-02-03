"""
Debug: Ver qué devuelve get_etiquetas_por_mes para cuentas de FINANCIAMIENTO
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

svc = FlujoCajaService(USERNAME, PASSWORD)

# Obtener asientos del período
fecha_inicio = '2026-01-01'
fecha_fin = '2026-02-03'
cuentas_config = svc._get_cuentas_efectivo_config()
cuentas_efectivo_ids = svc.odoo_manager.get_cuentas_efectivo(cuentas_config)
_, asientos_ids = svc.odoo_manager.get_movimientos_efectivo_periodo(
    fecha_inicio, fecha_fin, cuentas_efectivo_ids, None, incluir_draft=False
)

print(f"Asientos: {len(asientos_ids)}")

# Buscar cuentas problema
cuentas_problema = ['21010102', '21010101', '21030201']
accs = svc.odoo_manager.odoo.search_read('account.account', [['code', 'in', cuentas_problema]], ['id', 'code'])
acc_ids = [a['id'] for a in accs]
print(f"Account IDs: {acc_ids}")

# Llamar get_etiquetas_por_mes directamente
print("\n" + "=" * 80)
print("RESULTADO DE get_etiquetas_por_mes")
print("=" * 80)

etiquetas = svc.odoo_manager.get_etiquetas_por_mes(asientos_ids, acc_ids, 'mensual')
print(f"Etiquetas encontradas: {len(etiquetas)}")

for et in etiquetas[:20]:
    acc = et.get('account_id', [0, ''])
    acc_name = acc[1] if isinstance(acc, (list, tuple)) and len(acc) > 1 else str(acc)
    print(f"  {acc_name[:30]}: {et.get('name', '?')[:40]} = {et.get('balance', 0):,.0f}")

# Buscar directamente en Odoo
print("\n" + "=" * 80)
print("BÚSQUEDA DIRECTA EN ODOO (sin filtro journal_id)")
print("=" * 80)

for a in accs:
    print(f"\nCuenta {a['code']} (ID {a['id']}):")
    
    # Buscar movimientos en los asientos
    lineas = svc.odoo_manager.odoo.search_read(
        'account.move.line',
        [
            ['move_id', 'in', asientos_ids],
            ['account_id', '=', a['id']]
        ],
        ['name', 'balance', 'date', 'journal_id'],
        limit=10
    )
    
    print(f"  Líneas encontradas: {len(lineas)}")
    for l in lineas[:5]:
        journal = l.get('journal_id', [0, ''])
        journal_name = journal[1] if isinstance(journal, (list, tuple)) and len(journal) > 1 else str(journal)
        print(f"    {l['date']}: {l['name'][:40]} | {l['balance']:,.0f} | Journal: {journal_name}")
