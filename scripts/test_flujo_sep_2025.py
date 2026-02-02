"""
TEST: Verificar flujo de caja de Septiembre 2025 para cuenta 11030101

Este script prueba que:
1. FCXE 000222 (fecha pago 13-Sep) aparezca en Sept con ~$69M
2. No haya duplicación de montos
3. Las etiquetas muestren el nombre del documento (no "Sin etiqueta")
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")

from shared.odoo_client import OdooClient
from backend.services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 80)
print("TEST: Flujo de Caja Septiembre 2025 - Cuenta Deudores por Ventas (11030101)")
print("=" * 80)

# 1. Primero verificar el dato de origen: FCXE 000222
print("\n[PASO 1] Verificar datos de FCXE 000222 en Odoo:")
print("-" * 60)

odoo = OdooClient(USERNAME, PASSWORD)

moves = odoo.search_read(
    'account.move', 
    [['name', '=', 'FCXE 000222']], 
    ['id', 'name', 'date', 'x_studio_fecha_de_pago', 'invoice_date_due', 'amount_total']
)

if moves:
    m = moves[0]
    print(f"  Documento: {m['name']}")
    print(f"  Fecha Contable: {m['date']}")
    print(f"  Fecha Pago Acordada (x_studio_fecha_de_pago): {m.get('x_studio_fecha_de_pago')}")
    print(f"  Fecha Vencimiento: {m.get('invoice_date_due')}")
    print(f"  Monto Total: ${m.get('amount_total', 0):,.0f}")
    
    # Verificar la línea en 11030101
    acc = odoo.search_read('account.account', [['code', '=', '11030101']], ['id'])[0]
    lines = odoo.search_read(
        'account.move.line',
        [['move_id', '=', m['id']], ['account_id', '=', acc['id']]],
        ['balance', 'debit', 'credit']
    )
    if lines:
        l = lines[0]
        print(f"  Línea en 11030101: Débito=${l['debit']:,.0f} | Crédito=${l['credit']:,.0f} | Balance=${l['balance']:,.0f}")
else:
    print("  ❌ No se encontró FCXE 000222")

# 2. Ejecutar el servicio de flujo de caja para Sept 2025
print("\n[PASO 2] Ejecutar FlujoCajaService para Sept 2025:")
print("-" * 60)

service = FlujoCajaService(USERNAME, PASSWORD)

# Obtener flujo mensualizado para Sept 2025
flujo = service.get_flujo_mensualizado('2025-09-01', '2025-09-30')

print(f"  Período: {flujo.get('periodo', {})}")
print(f"  Meses: {flujo.get('meses', [])}")

# 3. Buscar el concepto 1.1.1 (Cobros de ventas) en OPERACION
print("\n[PASO 3] Buscar concepto 1.1.1 en Actividades de Operación:")
print("-" * 60)

operacion = flujo.get('actividades', {}).get('OPERACION', {})
conceptos = operacion.get('conceptos', [])

concepto_111 = None
for c in conceptos:
    if c.get('id') == '1.1.1':
        concepto_111 = c
        break

if concepto_111:
    print(f"  Concepto: {concepto_111.get('id')} - {concepto_111.get('nombre')}")
    print(f"  Total: ${concepto_111.get('total', 0):,.0f}")
    print(f"  Montos por mes: {concepto_111.get('montos_por_mes', {})}")
    
    # Buscar cuentas
    cuentas = concepto_111.get('cuentas', [])
    print(f"\n  Cuentas ({len(cuentas)}):")
    
    for cuenta in cuentas[:10]:  # Top 10
        print(f"    - {cuenta.get('codigo')}: ${cuenta.get('monto', 0):,.0f}")
        
        # Buscar etiquetas con FCXE
        etiquetas = cuenta.get('etiquetas', [])
        for et in etiquetas[:5]:
            nombre = et.get('nombre', '')
            monto = et.get('monto', 0)
            if 'FCXE 000222' in nombre or abs(monto) > 60_000_000:
                print(f"      -> {nombre}: ${monto:,.0f}")
else:
    print("  ❌ No se encontró concepto 1.1.1")

# 4. Buscar específicamente 11030101
print("\n[PASO 4] Buscar cuenta 11030101 en todos los conceptos:")
print("-" * 60)

found = False
for actividad_key, actividad in flujo.get('actividades', {}).items():
    for c in actividad.get('conceptos', []):
        for cuenta in c.get('cuentas', []):
            if cuenta.get('codigo') == '11030101':
                found = True
                print(f"  ✓ Encontrada en {actividad_key} > {c.get('id')} - {c.get('nombre')}")
                print(f"    Monto total: ${cuenta.get('monto', 0):,.0f}")
                print(f"    Montos por mes: {cuenta.get('montos_por_mes', {})}")
                
                etiquetas = cuenta.get('etiquetas', [])
                print(f"    Etiquetas ({len(etiquetas)}):")
                for et in etiquetas[:10]:
                    print(f"      - {et.get('nombre', 'N/A')}: ${et.get('monto', 0):,.0f}")

if not found:
    print("  ❌ No se encontró cuenta 11030101 en ningún concepto")

# 5. Resumen de validación
print("\n" + "=" * 80)
print("RESUMEN DE VALIDACIÓN")
print("=" * 80)

# Obtener monto de Sept para 11030101
monto_sept = 0
found_222 = None
for actividad in flujo.get('actividades', {}).values():
    for c in actividad.get('conceptos', []):
        for cuenta in c.get('cuentas', []):
            if cuenta.get('codigo') == '11030101':
                monto_sept = cuenta.get('montos_por_mes', {}).get('2025-09', 0)
                # Buscar FCXE 000222 en etiquetas
                for et in cuenta.get('etiquetas', []):
                    if 'FCXE 000222' in et.get('nombre', ''):
                        found_222 = et

print(f"\n1. Monto de 11030101 en Sept 2025: ${monto_sept:,.0f}")
print(f"   Esperado (aproximado): ~$69,000,000 (FCXE 000222)")

print(f"\n2. Buscar FCXE 000222 específicamente:")
if found_222:
    print(f"   ✓ ENCONTRADO: {found_222.get('nombre')}")
    print(f"     Monto: ${found_222.get('monto', 0):,.0f}")
    print(f"     Montos por mes: {found_222.get('montos_por_mes', {})}")
else:
    print("   ❌ NO ENCONTRADO en las etiquetas")

if 60_000_000 < abs(monto_sept) < 80_000_000:
    print("   ✓ CORRECTO - Monto dentro del rango esperado")
elif abs(monto_sept) > 150_000_000:
    print("   ❌ ERROR - Posible DUPLICACIÓN (monto muy alto)")
elif abs(monto_sept) < 10_000_000:
    print("   ⚠️ REVISAR - Monto muy bajo, puede faltar el documento")
else:
    print("   ? REVISAR - Monto fuera del rango esperado")

print("\nScript completado.")
