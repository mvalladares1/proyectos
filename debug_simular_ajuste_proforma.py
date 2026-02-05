"""
DEBUG: Simular ajuste de proforma USD → CLP
Comparar ANTES y DESPUÉS sin modificar nada

OBJETIVO: Verificar que los cálculos son correctos antes de implementar
"""
import xmlrpc.client

# Configuración
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 120)
print("SIMULACIÓN: AJUSTE DE PROFORMA USD → CLP")
print("=" * 120)

# Buscar factura FAC 000001 específicamente
print("\n🔍 Buscando factura FAC 000001...")

facturas = models.execute_kw(db, uid, password,
    'account.move', 'search_read',
    [[['move_type', '=', 'in_invoice'],
      ['state', '=', 'draft'],
      ['currency_id.name', '=', 'USD']]],  # Solo facturas en USD
    {'fields': ['id', 'name', 'partner_id', 'invoice_date', 'currency_id', 
                'amount_total', 'amount_untaxed', 'amount_tax',
                'amount_total_signed', 'amount_untaxed_signed',
                'invoice_line_ids', 'line_ids'],
     'limit': 1,
     'order': 'id desc'}
)

if not facturas:
    print("❌ No se encontró factura en borrador en USD")
    exit()

fac = facturas[0]
print(f"\n✅ Encontrada: {fac.get('name', 'Sin nombre')} (ID: {fac['id']})")
print(f"   Proveedor: {fac.get('partner_id', ['N/A', 'N/A'])[1]}")

# ============================================================================
# ESTADO ACTUAL (ANTES)
# ============================================================================
print("\n" + "=" * 120)
print("📋 ESTADO ACTUAL (ANTES) - Valores en USD")
print("=" * 120)

print(f"\n   MONEDA: {fac.get('currency_id', ['N/A', 'USD'])[1]}")
print(f"\n   TOTALES FACTURA:")
print(f"   ├─ Base imponible (sin IVA): USD$ {fac.get('amount_untaxed', 0):>15,.2f}")
print(f"   ├─ IVA 19%:                  USD$ {fac.get('amount_tax', 0):>15,.2f}")
print(f"   └─ TOTAL (con IVA):          USD$ {fac.get('amount_total', 0):>15,.2f}")

# Leer líneas de factura
invoice_line_ids = fac.get('invoice_line_ids', [])
lines = models.execute_kw(db, uid, password,
    'account.move.line', 'read',
    [invoice_line_ids],
    {'fields': ['id', 'name', 'quantity', 'price_unit', 
                'price_subtotal', 'price_total',
                'debit', 'credit', 'amount_currency',
                'display_type']}
)

# Filtrar solo líneas de producto (no secciones ni notas)
lines_producto = [l for l in lines if l.get('display_type') not in ['line_section', 'line_note', 'payment_term']]

print(f"\n   LÍNEAS DE FACTURA ({len(lines_producto)}):")
print(f"   {'─' * 110}")
print(f"   {'Etiqueta':<50} {'Qty':>10} {'P.Unit USD':>12} {'Subtotal USD':>15} {'Total USD':>15}")
print(f"   {'─' * 110}")

total_subtotal_usd = 0
total_total_usd = 0

for line in lines_producto:
    nombre = (line.get('name') or 'N/A')[:48]
    qty = line.get('quantity', 0)
    precio = line.get('price_unit', 0)
    subtotal = line.get('price_subtotal', 0)
    total = line.get('price_total', 0)
    
    total_subtotal_usd += subtotal
    total_total_usd += total
    
    print(f"   {nombre:<50} {qty:>10,.2f} {precio:>12,.2f} {subtotal:>15,.2f} {total:>15,.2f}")

print(f"   {'─' * 110}")
print(f"   {'TOTALES':<50} {'':<10} {'':<12} {total_subtotal_usd:>15,.2f} {total_total_usd:>15,.2f}")

# ============================================================================
# ESTADO DESPUÉS (Usando valores CLP de apuntes contables)
# ============================================================================
print("\n" + "=" * 120)
print("📋 ESTADO DESPUÉS (SIMULADO) - Valores en CLP desde apuntes contables")
print("=" * 120)

# Los apuntes contables ya tienen los valores en CLP
print(f"\n   MONEDA: CLP (Pesos Chilenos)")
print(f"\n   TOTALES FACTURA (desde amount_signed):")
print(f"   ├─ Base imponible (sin IVA): CLP$ {abs(fac.get('amount_untaxed_signed', 0)):>15,.0f}")
print(f"   ├─ IVA 19%:                  CLP$ {abs(fac.get('amount_total_signed', 0)) - abs(fac.get('amount_untaxed_signed', 0)):>15,.0f}")
print(f"   └─ TOTAL (con IVA):          CLP$ {abs(fac.get('amount_total_signed', 0)):>15,.0f}")

print(f"\n   LÍNEAS DE FACTURA (valores CLP desde campo 'debit'):")
print(f"   {'─' * 110}")
print(f"   {'Etiqueta':<50} {'Qty':>10} {'USD Orig':>12} {'CLP (debit)':>15} {'TC Impl':>10}")
print(f"   {'─' * 110}")

total_clp = 0
tcs = []

for line in lines_producto:
    nombre = (line.get('name') or 'N/A')[:48]
    qty = line.get('quantity', 0)
    usd_orig = line.get('price_subtotal', 0)
    clp_debit = line.get('debit', 0)
    tc = clp_debit / usd_orig if usd_orig > 0 else 0
    
    total_clp += clp_debit
    if tc > 0:
        tcs.append(tc)
    
    print(f"   {nombre:<50} {qty:>10,.2f} {usd_orig:>12,.2f} {clp_debit:>15,.0f} {tc:>10,.2f}")

print(f"   {'─' * 110}")
print(f"   {'TOTAL BASE IMPONIBLE':<50} {'':<10} {total_subtotal_usd:>12,.2f} {total_clp:>15,.0f}")

# Calcular IVA en CLP
iva_clp = total_clp * 0.19
total_con_iva_clp = total_clp + iva_clp

print(f"   {'IVA 19%':<50} {'':<10} {'':<12} {iva_clp:>15,.0f}")
print(f"   {'TOTAL CON IVA':<50} {'':<10} {'':<12} {total_con_iva_clp:>15,.0f}")

# TC promedio
tc_promedio = sum(tcs) / len(tcs) if tcs else 0
print(f"\n   📊 TIPO DE CAMBIO PROMEDIO: {tc_promedio:,.4f}")

# ============================================================================
# COMPARACIÓN ANTES / DESPUÉS
# ============================================================================
print("\n" + "=" * 120)
print("📊 COMPARACIÓN: ANTES vs DESPUÉS")
print("=" * 120)

print(f"\n   {'Concepto':<30} {'ANTES (USD)':<20} {'DESPUÉS (CLP)':<20} {'TC Aplicado':<15}")
print(f"   {'─' * 85}")
print(f"   {'Base imponible':<30} USD$ {fac.get('amount_untaxed', 0):>12,.2f} CLP$ {total_clp:>12,.0f} {tc_promedio:>12,.2f}")

iva_usd = fac.get('amount_tax', 0)
print(f"   {'IVA 19%':<30} USD$ {iva_usd:>12,.2f} CLP$ {iva_clp:>12,.0f} {tc_promedio:>12,.2f}")

total_usd = fac.get('amount_total', 0)
print(f"   {'TOTAL':<30} USD$ {total_usd:>12,.2f} CLP$ {total_con_iva_clp:>12,.0f} {tc_promedio:>12,.2f}")

# ============================================================================
# VALIDACIÓN CON VALORES SIGNED
# ============================================================================
print("\n" + "=" * 120)
print("✅ VALIDACIÓN: Comparar con amount_signed de Odoo")
print("=" * 120)

signed_untaxed = abs(fac.get('amount_untaxed_signed', 0))
signed_total = abs(fac.get('amount_total_signed', 0))
signed_tax = signed_total - signed_untaxed

print(f"\n   {'Concepto':<30} {'Calculado':<20} {'Odoo Signed':<20} {'Diferencia':<15}")
print(f"   {'─' * 85}")
print(f"   {'Base imponible':<30} CLP$ {total_clp:>12,.0f} CLP$ {signed_untaxed:>12,.0f} {total_clp - signed_untaxed:>12,.0f}")
print(f"   {'IVA 19%':<30} CLP$ {iva_clp:>12,.0f} CLP$ {signed_tax:>12,.0f} {iva_clp - signed_tax:>12,.0f}")
print(f"   {'TOTAL':<30} CLP$ {total_con_iva_clp:>12,.0f} CLP$ {signed_total:>12,.0f} {total_con_iva_clp - signed_total:>12,.0f}")

# Verificar si cuadra
diff = abs(total_clp - signed_untaxed)
if diff < 10:  # Tolerancia de redondeo
    print(f"\n   ✅ VALIDACIÓN EXITOSA: Los cálculos cuadran (diferencia: {diff:.0f})")
else:
    print(f"\n   ⚠️ ADVERTENCIA: Hay diferencia de {diff:,.0f} - revisar cálculos")

# ============================================================================
# PREVIEW DE PROFORMA EN CLP
# ============================================================================
print("\n" + "=" * 120)
print("📄 PREVIEW: CÓMO SE VERÍA LA PROFORMA EN CLP")
print("=" * 120)

partner = fac.get('partner_id', ['N/A', 'Sin proveedor'])
partner_name = partner[1] if isinstance(partner, list) else partner

print(f"""
   ┌─────────────────────────────────────────────────────────────────────────────┐
   │  PROFORMA DE PROVEEDOR                                                      │
   ├─────────────────────────────────────────────────────────────────────────────┤
   │  Proveedor: {partner_name:<60} │
   │  Moneda:    CLP (Pesos Chilenos)                                            │
   │  Fecha:     {fac.get('invoice_date') or 'Sin fecha':<60} │
   ├─────────────────────────────────────────────────────────────────────────────┤
""")

print(f"   │  {'LÍNEAS DE FACTURA':<71} │")
print(f"   ├─────────────────────────────────────────────────────────────────────────────┤")

for line in lines_producto:
    nombre = (line.get('name') or 'N/A')[:45]
    clp = line.get('debit', 0)
    print(f"   │  {nombre:<45} CLP$ {clp:>15,.0f}   │")

print(f"   ├─────────────────────────────────────────────────────────────────────────────┤")
print(f"   │  {'Base imponible:':<45} CLP$ {total_clp:>15,.0f}   │")
print(f"   │  {'IVA 19%:':<45} CLP$ {iva_clp:>15,.0f}   │")
print(f"   │  {'TOTAL:':<45} CLP$ {total_con_iva_clp:>15,.0f}   │")
print(f"   └─────────────────────────────────────────────────────────────────────────────┘")

print("\n" + "=" * 120)
print("📋 RESUMEN DE OPERACIÓN")
print("=" * 120)
print(f"""
   Para convertir esta factura de USD a CLP necesitamos:
   
   1. LEER los valores 'debit' de cada línea (ya están en CLP)
   2. SUMAR para obtener base imponible en CLP: {total_clp:,.0f}
   3. CALCULAR IVA 19%: {iva_clp:,.0f}
   4. TOTAL: {total_con_iva_clp:,.0f}
   
   TIPO DE CAMBIO USADO POR ODOO: {tc_promedio:,.4f}
   
   ⚠️  NOTA: Este es un cálculo de LECTURA, no modifica nada en Odoo.
       El tab de dashboard solo mostrará estos valores para revisión.
""")

print("=" * 120)
print("FIN DE SIMULACIÓN")
print("=" * 120)
