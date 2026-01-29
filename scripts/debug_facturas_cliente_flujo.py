"""
DEBUG: Facturas de Cliente para Flujo de Caja (1.1.1)
=====================================================
Objetivo: Analizar estructura de facturas de cliente para implementar
"Cobros procedentes de las ventas de bienes y prestación de servicios"
"""
import sys
import os
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

# Configuración
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Período de análisis
FECHA_INICIO = "2025-01-01"
FECHA_FIN = "2025-12-31"

print("=" * 100)
print("DEBUG: FACTURAS DE CLIENTE PARA FLUJO DE CAJA (1.1.1)")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Período: {FECHA_INICIO} a {FECHA_FIN}")
print("=" * 100)

try:
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("✅ Conexión a Odoo establecida")
except Exception as e:
    print(f"❌ Error al conectar a Odoo: {e}")
    sys.exit(1)

# === 1. IDENTIFICAR DIARIO DE FACTURAS DE CLIENTE ===
print("\n📋 DIARIOS DISPONIBLES (VENTAS):")
print("-" * 60)

journals = odoo.search_read(
    'account.journal',
    [['type', '=', 'sale']],
    ['id', 'name', 'code', 'type'],
    limit=20
)

for j in journals:
    print(f"  ID: {j['id']:>4} | Código: {j.get('code', ''):<10} | Nombre: {j['name']}")

# === 2. EXPLORAR PAYMENT_STATE VALUES ===
print("\n\n📊 PAYMENT_STATE - VALORES ÚNICOS:")
print("-" * 60)

# Obtener muestra de facturas para ver payment_states
facturas_sample = odoo.search_read(
    'account.move',
    [
        ['move_type', '=', 'out_invoice'],
        ['state', '=', 'posted'],
        ['invoice_date', '>=', FECHA_INICIO],
        ['invoice_date', '<=', FECHA_FIN]
    ],
    ['id', 'name', 'payment_state'],
    limit=1000
)

payment_states = {}
for f in facturas_sample:
    ps = f.get('payment_state', 'unknown')
    payment_states[ps] = payment_states.get(ps, 0) + 1

print(f"{'Payment State':<25} {'Cantidad':>10}")
print("-" * 40)
for ps, count in sorted(payment_states.items(), key=lambda x: -x[1]):
    print(f"{ps:<25} {count:>10}")

# === 3. ANALIZAR FACTURAS POR ESTADO DE PAGO ===
print("\n\n📄 FACTURAS DE CLIENTE POR ESTADO:")
print("=" * 100)

# 3A. FACTURAS PAGADAS (Flujo REAL - pasado)
print("\n🟢 PAGADAS (paid) - Cobros realizados:")
facturas_pagadas = odoo.search_read(
    'account.move',
    [
        ['move_type', '=', 'out_invoice'],
        ['state', '=', 'posted'],
        ['payment_state', '=', 'paid'],
        ['invoice_date', '>=', FECHA_INICIO],
        ['invoice_date', '<=', FECHA_FIN]
    ],
    ['id', 'name', 'partner_id', 'invoice_date', 'amount_total', 'amount_residual'],
    limit=15,
    order='invoice_date desc'
)

print(f"  {'Factura':<20} {'Cliente':<30} {'Fecha':<12} {'Total':>15}")
print("  " + "-" * 85)
for f in facturas_pagadas:
    partner = f.get('partner_id')
    partner_name = partner[1][:28] if isinstance(partner, (list, tuple)) else ''
    print(f"  {f['name']:<20} {partner_name:<30} {str(f.get('invoice_date'))[:10]:<12} "
          f"${f.get('amount_total', 0):>14,.0f}")

print(f"\n  (Mostrando 15 de la muestra)")

# 3B. FACTURAS REVERTIDAS
print("\n🔴 REVERTIDAS (reversed):")
facturas_revertidas = odoo.search_read(
    'account.move',
    [
        ['move_type', '=', 'out_invoice'],
        ['state', '=', 'posted'],
        ['payment_state', '=', 'reversed'],
        ['invoice_date', '>=', FECHA_INICIO],
        ['invoice_date', '<=', FECHA_FIN]
    ],
    ['id', 'name', 'partner_id', 'amount_total'],
    limit=10
)
print(f"  Encontradas: {len(facturas_revertidas)} (muestra)")
for f in facturas_revertidas[:5]:
    partner = f.get('partner_id')
    partner_name = partner[1][:30] if isinstance(partner, (list, tuple)) else ''
    print(f"  {f['name']:<20} {partner_name:<30} ${f.get('amount_total', 0):,.0f}")

# 3C. FACTURAS NO PAGADAS (Flujo PROYECTADO)
print("\n🟡 NO PAGADAS (not_paid) - Cobros pendientes:")
facturas_no_pagadas = odoo.search_read(
    'account.move',
    [
        ['move_type', '=', 'out_invoice'],
        ['state', '=', 'posted'],
        ['payment_state', '=', 'not_paid'],
        ['invoice_date', '>=', FECHA_INICIO]
    ],
    ['id', 'name', 'partner_id', 'invoice_date', 'invoice_date_due', 'amount_total', 'amount_residual'],
    limit=15,
    order='invoice_date_due asc'
)

print(f"  {'Factura':<20} {'Cliente':<25} {'Emisión':<12} {'Venc.':<12} {'Total':>14} {'Residual':>12}")
print("  " + "-" * 105)
for f in facturas_no_pagadas:
    partner = f.get('partner_id')
    partner_name = partner[1][:23] if isinstance(partner, (list, tuple)) else ''
    due_date = f.get('invoice_date_due', f.get('invoice_date', ''))
    print(f"  {f['name']:<20} {partner_name:<25} {str(f.get('invoice_date'))[:10]:<12} "
          f"{str(due_date)[:10]:<12} ${f.get('amount_total', 0):>13,.0f} ${f.get('amount_residual', 0):>10,.0f}")

print(f"\n  (Muestra de 15 facturas)")

# 3D. FACTURAS EN PROCESO DE PAGO
print("\n🟠 EN PROCESO (in_payment):")
facturas_in_payment = odoo.search_read(
    'account.move',
    [
        ['move_type', '=', 'out_invoice'],
        ['state', '=', 'posted'],
        ['payment_state', '=', 'in_payment'],
        ['invoice_date', '>=', FECHA_INICIO]
    ],
    ['id', 'name', 'partner_id', 'amount_total', 'amount_residual'],
    limit=10
)

for f in facturas_in_payment:
    partner = f.get('partner_id')
    partner_name = partner[1][:30] if isinstance(partner, (list, tuple)) else ''
    print(f"  {f['name']:<20} {partner_name:<30} Total: ${f.get('amount_total', 0):,.0f} Residual: ${f.get('amount_residual', 0):,.0f}")

if not facturas_in_payment:
    print("  Sin facturas en proceso")
print(f"\n  (Muestra de hasta 10)")

# 3E. FACTURAS PAGADAS PARCIALMENTE
print("\n🟣 PAGADAS PARCIALMENTE (partial):")
facturas_partial = odoo.search_read(
    'account.move',
    [
        ['move_type', '=', 'out_invoice'],
        ['state', '=', 'posted'],
        ['payment_state', '=', 'partial'],
        ['invoice_date', '>=', FECHA_INICIO]
    ],
    ['id', 'name', 'partner_id', 'amount_total', 'amount_residual'],
    limit=15
)

print(f"  {'Factura':<20} {'Cliente':<25} {'Total':>14} {'Pagado':>14} {'Residual':>14} {'%':>8}")
print("  " + "-" * 105)
total_partial_total = 0
total_partial_residual = 0
for f in facturas_partial:
    partner = f.get('partner_id')
    partner_name = partner[1][:23] if isinstance(partner, (list, tuple)) else ''
    monto_total = f.get('amount_total', 0)
    monto_residual = f.get('amount_residual', 0)
    monto_pagado = monto_total - monto_residual
    pct_pagado = (monto_pagado / monto_total * 100) if monto_total > 0 else 0
    total_partial_total += monto_total
    total_partial_residual += monto_residual
    print(f"  {f['name']:<20} {partner_name:<25} ${monto_total:>13,.0f} ${monto_pagado:>13,.0f} "
          f"${monto_residual:>13,.0f} {pct_pagado:>6.1f}%")

if not facturas_partial:
    print("  Sin facturas parciales")
else:
    print(f"\n  SUMA muestra - Total: ${total_partial_total:,.0f} | Residual: ${total_partial_residual:,.0f}")

# === 4. CAMPOS DISPONIBLES RELEVANTES ===
print("\n\n📋 CAMPOS RELEVANTES EN FACTURA:")
print("-" * 60)

# Obtener una factura de ejemplo para ver campos relevantes
if facturas_no_pagadas:
    sample_id = facturas_no_pagadas[0]['id']
    sample_full = odoo.search_read(
        'account.move',
        [['id', '=', sample_id]],
        ['name', 'move_type', 'state', 'payment_state',
         'invoice_date', 'invoice_date_due', 'date',
         'amount_total', 'amount_residual', 'amount_untaxed', 'amount_tax',
         'partner_id', 'currency_id', 'journal_id'],
        limit=1
    )[0]
    
    print(f"  Ejemplo: {sample_full.get('name')}")
    print()
    for campo, valor in sample_full.items():
        if campo == 'id':
            continue
        if isinstance(valor, (list, tuple)):
            valor = f"{valor[0]} - {valor[1]}" if len(valor) > 1 else str(valor)
        print(f"  {campo:<25} = {valor}")

# === 5. RESUMEN PARA FLUJO DE CAJA ===
print("\n\n" + "=" * 100)
print("📊 RESUMEN PARA FLUJO DE CAJA 1.1.1")
print("=" * 100)

print("\n🔵 FLUJO REAL (Cobros ya realizados):")
print("   - payment_state = 'paid': Facturas completamente cobradas")
print("   - payment_state = 'reversed': Facturas revertidas (excluir)")
print("   → Usar: amount_total de facturas pagadas en el período")

print("\n🟡 FLUJO PROYECTADO (Cobros pendientes):")
print("   - payment_state = 'not_paid': Todo por cobrar → amount_residual (igual a amount_total)")
print("   - payment_state = 'in_payment': En proceso → amount_residual")
print("   - payment_state = 'partial': Parcialmente pagado → amount_residual")
print("   → Usar: amount_residual para proyección")

print("\n📅 CAMPO PARA FECHA DE COBRO PROYECTADO:")
print("   1. invoice_date_due (fecha vencimiento)")
print("   2. invoice_date + 30 días (fallback)")

print("\n💡 PROPUESTA DE IMPLEMENTACIÓN:")
print("""
   FLUJO REAL (1.1.1):
   - Facturas out_invoice con payment_state = 'paid'
   - Filtrar por invoice_date en período
   - Sumar amount_total como entrada de efectivo
   
   FLUJO PROYECTADO (1.1.1):
   - Facturas out_invoice con payment_state in ['not_paid', 'in_payment', 'partial']  
   - Fecha proyectada = invoice_date_due (o invoice_date + 30)
   - Filtrar por fecha proyectada en período
   - Sumar amount_residual como proyección de cobro
""")

print("\n" + "=" * 100)
print("DEBUG COMPLETADO")
print("=" * 100)
