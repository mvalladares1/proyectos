"""
DEBUG: Full pipeline for FAC 000256/Payment to inspect double counting
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from services.flujo_caja_service import FlujoCajaService
from services.flujo_caja.agregador import AgregadorFlujo

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("DEBUG: FULL PIPELINE FAC 000256")
print("=" * 70)

svc = FlujoCajaService(USERNAME, PASSWORD)
mgr = svc.odoo_manager

# 1. Obtener ID del pago
facturas = svc.odoo_manager.odoo.search_read('account.move', [['name', '=', 'FAC 000256']], ['id'])
if not facturas:
    print("No FAC 256")
    sys.exit()
fac_id = facturas[0]['id']
lineas = svc.odoo_manager.odoo.search_read('account.move.line', [['move_id', '=', fac_id], ['account_id.code', '=like', '1103%']], ['id'])
pago_id = None
if lineas:
    l_id = lineas[0]['id']
    partials = svc.odoo_manager.odoo.search_read('account.partial.reconcile', [['debit_move_id', '=', l_id]], ['credit_move_id'])
    if partials:
        pago_line_id = partials[0]['credit_move_id'][0]
        pago_line = svc.odoo_manager.odoo.search_read('account.move.line', [['id', '=', pago_line_id]], ['move_id'])[0]
        pago_id = pago_line['move_id'][0]

print(f"Pago ID: {pago_id}")

# 2. Ejecutar get_contrapartidas_agrupadas para este asiento
cuentas_config = svc._get_cuentas_efectivo_config()
efectivo_ids = mgr.get_cuentas_efectivo(cuentas_config)
print(f"Efectivo IDs count: {len(efectivo_ids)}")

contrapartidas = mgr.get_contrapartidas_agrupadas([pago_id], efectivo_ids)
print("\n[CONTRAPARTIDAS]:")
# Convertir a dict para procesar luego
contra_dict = {}
for c in contrapartidas:
    acc_id = c['account_id'][0]
    print(f"  Acc {acc_id}: {c}")
    contra_dict[acc_id] = c

# 3. Ejecutar get_etiquetas_por_mes
print("\n[ETIQUETAS]:")
etiquetas = mgr.get_etiquetas_por_mes([pago_id], [int(k) for k in contra_dict.keys()], 'mensual')
for et in etiquetas:
    print(f"  {et}")

# 4. Agregador
print("\n[AGREGADOR]:")
agregador = AgregadorFlujo(
    svc._clasificar_cuenta,
    svc.catalogo,
    ['2025-10', '2025-11', '2025-12', '2026-01', '2026-02', '2026-03', '2026-04']
)

# Simular proceso
agregador.procesar_grupos_contrapartida(contrapartidas, svc.mapeo_cuentas.get("configuracion", {}))
agregador.procesar_etiquetas(etiquetas)

res, _ = agregador.obtener_resultados()
# Buscar 1.1.1
for c_id, data in res.get('OPERACION', {}).get('conceptos_dict', {}).items():
    if c_id == '1.1.1':
        print(f"Concepto 1.1.1 Total: ${data['total']:,.0f}")
        for cuenta_code, cuenta_data in agregador.cuentas_por_concepto['1.1.1'].items():
             print(f"  Cuenta {cuenta_code}: ${cuenta_data['monto']:,.0f}")
             for tag, tag_data in cuenta_data.get('etiquetas', {}).items():
                 print(f"    Tag {tag}: ${tag_data['monto']:,.0f}")

print("\n" + "=" * 70)
