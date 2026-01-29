"""
DEBUG: Analizar Factura FAC 000256 y sus pagos
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("DEBUG: Analisis FAC 000256")
print("=" * 70)

odoo = OdooClient(USERNAME, PASSWORD)

# 1. Buscar la factura
facturas = odoo.search_read(
    'account.move',
    [
        ['name', '=', 'FAC 000256'],
        ['move_type', '=', 'out_invoice']
    ],
    ['id', 'name', 'date', 'invoice_date', 'state', 'payment_state', 'amount_total', 'amount_untaxed', 'partner_id']
)

if not facturas:
    print("NO SE ENCONTRO FAC 000256")
    sys.exit()

fac = facturas[0]
print(f"[FACTURA]: {fac['name']} (ID: {fac['id']})")
print(f"  Cliente: {fac['partner_id'][1]}")
print(f"  Fecha: {fac['invoice_date']}")
print(f"  Estado: {fac['state']} / {fac['payment_state']}")
print(f"  Monto Total: ${fac['amount_total']:,.0f}")
print(f"  Monto Neto: ${fac['amount_untaxed']:,.0f}")

# 2. Ver líneas del asiento de la factura
print("\n[LINEAS ASIENTO FACTURA]:")
lineas_fac = odoo.search_read(
    'account.move.line',
    [['move_id', '=', fac['id']]],
    ['account_id', 'debit', 'credit', 'name', 'date']
)

for l in lineas_fac:
    acc_code = l['account_id'][1].split(' ')[0]
    acc_name = l['account_id'][1]
    debit = l['debit']
    credit = l['credit']
    print(f"  {acc_code} | {acc_name[:40]}: Debe ${debit:,.0f} | Haber ${credit:,.0f}")

# 3. Buscar Pagos (Reconciliaciones)
# En Odoo 14+ se busca en account.partial.reconcile
# O buscando los IDs de pagos asociados
print("\n[PAGOS ASOCIADOS]:")

# Una forma comun es obtener los payment_id vinculados si existen, o widget
# Pero vamos a buscar si hay conciliaciones partiales que involucren las lineas de CXC de esta factura

# Identificar linea CXC (la que tiene debito > 0 y es tipo cobrar)
linea_cxc = None
for l in lineas_fac:
    if l['debit'] > 0 and l['account_id'][1].startswith('1103'):
        linea_cxc = l
        break

if linea_cxc:
    print(f"  Linea CXC ID: {linea_cxc['id']} - {linea_cxc['account_id'][1]}")
    
    # Buscar conciliaciones donde esta linea es debit_move_id
    principales = odoo.search_read(
        'account.partial.reconcile',
        [['debit_move_id', '=', linea_cxc['id']]],
        ['credit_move_id', 'amount', 'max_date']
    )
    
    for p in principales:
        credit_line_id = p['credit_move_id'][0] # Linea del pago (Haber en CxC)
        monto = p['amount']
        fecha = p['max_date']
        
        # Obtener info del asiento de pago
        linea_pago = odoo.search_read(
            'account.move.line',
            [['id', '=', credit_line_id]],
            ['move_id', 'account_id', 'name', 'date', 'journal_id']
        )[0]
        
        move_pago_id = linea_pago['move_id'][0]
        move_pago_name = linea_pago['move_id'][1]
        
        print(f"  -> PAGO IDENTIFICADO: {move_pago_name} (ID: {move_pago_id})")
        print(f"     Fecha: {fecha} | Monto aplicado: ${monto:,.0f}")
        
        # Ver líneas del asiento de PAGO
        print(f"     [LINEAS DEL PAGO {move_pago_name}]:")
        lineas_pago = odoo.search_read(
            'account.move.line',
            [['move_id', '=', move_pago_id]],
            ['account_id', 'debit', 'credit', 'name']
        )
        for lp in lineas_pago:
            acc_code_p = lp['account_id'][1].split(' ')[0]
            print(f"       {acc_code_p} | {lp['account_id'][1][:40]}: Debe ${lp['debit']:,.0f} | Haber ${lp['credit']:,.0f}")

else:
    print("  No se identificó linea CXC (1103...) en la factura")

print("\n" + "=" * 70)
