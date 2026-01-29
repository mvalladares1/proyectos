"""
DEBUG: Trace FAC 000256 logic flow
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from services.flujo_caja_service import FlujoCajaService
from services.flujo_caja.odoo_queries import OdooQueryManager
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("DEBUG: TRACE FAC 000256")
print("=" * 70)

svc = FlujoCajaService(USERNAME, PASSWORD)
mgr = svc.odoo_manager

# 1. Verificar si 11030101 es efectivo (NO DEBERIA)
print("\n[1. CHECK CUENTAS EFECTIVO]")
cuentas_config = svc._get_cuentas_efectivo_config()
efectivo_ids = mgr.get_cuentas_efectivo(cuentas_config)
print(f"Total cuentas efectivo: {len(efectivo_ids)}")

# Buscar ID de 11030101
acc_1103 = svc.odoo_manager.odoo.search_read('account.account', [['code', '=', '11030101']], ['id', 'code', 'name'])
if acc_1103:
    acc_id = acc_1103[0]['id']
    if acc_id in efectivo_ids:
        print(f"❌ ERROR CRITICO: 11030101 es considerado EFECTIVO (ID {acc_id}). El pago será ignorado.")
    else:
        print(f"✅ OK: 11030101 NO es efectivo (ID {acc_id}).")
else:
    print("⚠️ Cuenta 11030101 no encontrada en Odoo")

# 2. Buscar Pago de FAC 000256
print("\n[2. BUSCAR PAGO FAC 000256]")
facturas = svc.odoo_manager.odoo.search_read('account.move', [['name', '=', 'FAC 000256']], ['id', 'name'])
if not facturas:
    print("Factura no encontrada")
    sys.exit()

fac_id = facturas[0]['id']
# Buscar linea 1103 de la factura
lineas = svc.odoo_manager.odoo.search_read('account.move.line', [['move_id', '=', fac_id], ['account_id.code', '=like', '1103%']], ['id'])
pago_id = None
if lineas:
    l_id = lineas[0]['id']
    partials = svc.odoo_manager.odoo.search_read('account.partial.reconcile', [['debit_move_id', '=', l_id]], ['credit_move_id', 'amount'])
    if partials:
        pago_line_id = partials[0]['credit_move_id'][0]
        pago_amount = partials[0]['amount']
        pago_line = svc.odoo_manager.odoo.search_read('account.move.line', [['id', '=', pago_line_id]], ['move_id'])[0]
        pago_id = pago_line['move_id'][0]
        print(f"Pago encontrado: ID {pago_id} - Monto ${pago_amount:,.0f}")
    else:
        print("No tiene pagos conciliados")

# 3. Verificar si el pago entra en el flujo
if pago_id:
    print("\n[3. VERIFICAR SI ENTRA EN FLUJO]")
    # Simulamos lo que hace get_movimientos_efectivo_periodo
    # Verifica si el asiento tiene linea en cuentas_efectivo_ids
    lineas_pago = svc.odoo_manager.odoo.search_read('account.move.line', [['move_id', '=', pago_id], ['account_id', 'in', efectivo_ids]], ['id', 'balance', 'account_id'])
    if lineas_pago:
        print(f"✅ OK: El asiento tiene líneas de efectivo: {[l['account_id'][1] for l in lineas_pago]}")
    else:
        print(f"❌ ERROR: El asiento NO toca cuentas de efectivo configuradas.")

    # 4. Verificar contrapartida
    print("\n[4. CLASIFICACION CONTRAPARTIDA]")
    lineas_contra = svc.odoo_manager.odoo.search_read('account.move.line', [['move_id', '=', pago_id], ['account_id', 'not in', efectivo_ids]], ['account_id', 'balance'])
    for l in lineas_contra:
        code = l['account_id'][1].split(' ')[0]
        balance = l['balance']
        clasif = svc._clasificar_cuenta(code)
        print(f"   Contrapartida: {l['account_id'][1]} | Balance: ${balance:,.0f} | Clasif: {clasif}")
        
        # Verificar mapeo en monitoreo
        monitoreadas = svc.cuentas_monitoreadas.get("cuentas_contrapartida", {}).get("codigos", [])
        if code in monitoreadas:
             print(f"   ✅ Cuenta {code} está MONITOREADA")
        else:
             print(f"   ❌ Cuenta {code} NO está en monitoreadas (será filtrada)")

print("\n" + "=" * 70)
