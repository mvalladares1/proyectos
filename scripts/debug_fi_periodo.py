"""
Debug: Ver qué período devuelve get_etiquetas_por_mes
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.flujo_caja_service import FlujoCajaService

svc = FlujoCajaService('mvalladares@riofuturo.cl', 'c0766224bec30cac071ffe43a858c9ccbd521ddd')

# Obtener asientos
cuentas_config = svc._get_cuentas_efectivo_config()
cuentas_efectivo_ids = svc.odoo_manager.get_cuentas_efectivo(cuentas_config)
_, asientos_ids = svc.odoo_manager.get_movimientos_efectivo_periodo('2026-01-01', '2026-02-03', cuentas_efectivo_ids, None, incluir_draft=False)

# Buscar etiquetas
acc_ids = [1332, 1333, 1374]  # 21010101, 21010102, 21030201
etiquetas = svc.odoo_manager.get_etiquetas_por_mes(asientos_ids, acc_ids, 'mensual')

print('Primeras 10 etiquetas:')
for e in etiquetas[:10]:
    date_month = e.get('date:month')
    date_week = e.get('date:week')
    name = e.get('name', '')[:30]
    print(f"  date:month='{date_month}' | date:week='{date_week}' | name={name}")

# Probar parseo
print("\nProbando _parse_odoo_month:")
for e in etiquetas[:3]:
    periodo_val = e.get('date:month') or e.get('date:week', '')
    parsed = svc._parse_odoo_month(periodo_val)
    print(f"  '{periodo_val}' -> '{parsed}'")
