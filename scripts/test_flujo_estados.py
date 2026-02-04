"""
Test completo: Verificar estructura de flujo de caja con estados de pago.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.services.flujo_caja_service import FlujoCajaService
import json

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 100)
print("TEST: Estructura de Flujo de Caja con Estados de Pago")
print("=" * 100)

svc = FlujoCajaService(USERNAME, PASSWORD)

# Consultar octubre a diciembre 2025
result = svc.get_flujo_mensualizado("2025-10-01", "2025-12-31")

# Buscar concepto 1.1.1
op = result.get('actividades', {}).get('OPERACION', {})
concepto_ventas = None

for c in op.get('conceptos', []):
    if c['id'] == '1.1.1':
        concepto_ventas = c
        break

if not concepto_ventas:
    print("❌ No se encontró concepto 1.1.1")
    exit(1)

print(f"\n✅ Concepto: [{concepto_ventas['id']}] {concepto_ventas.get('nombre')}")
print(f"   Montos por mes: {concepto_ventas.get('montos_por_mes', {})}")

# Buscar cuenta 11030101
cuentas = concepto_ventas.get('cuentas', [])
cuenta_deudores = None

for cuenta in cuentas:
    if cuenta['codigo'] == '11030101':
        cuenta_deudores = cuenta
        break

if not cuenta_deudores:
    print("❌ No se encontró cuenta 11030101")
    exit(1)

print(f"\n✅ Cuenta: {cuenta_deudores['codigo']} - {cuenta_deudores['nombre']}")
print(f"   es_cuenta_cxc: {cuenta_deudores.get('es_cuenta_cxc', 'NO DEFINIDO')}")
print(f"   Montos por mes: {cuenta_deudores.get('montos_por_mes', {})}")

# Revisar etiquetas
etiquetas = cuenta_deudores.get('etiquetas', [])
print(f"\n📋 ETIQUETAS ({len(etiquetas)}):")
print("-" * 100)

for i, etiq in enumerate(etiquetas[:10], 1):
    nombre = etiq.get('nombre', 'Sin nombre')
    monto = etiq.get('monto', 0)
    montos_mes = etiq.get('montos_por_mes', {})
    tiene_facturas = 'facturas' in etiq
    total_facturas = etiq.get('total_facturas', 0)
    
    print(f"\n{i}. {nombre}")
    print(f"   Monto total: ${monto:,.0f}")
    print(f"   Montos por mes: {montos_mes}")
    
    if tiene_facturas:
        print(f"   ✅ TIENE FACTURAS DETALLADAS: {total_facturas} facturas")
        # Mostrar primeras 3 facturas
        facturas = etiq.get('facturas', [])[:3]
        for fac in facturas:
            print(f"      - {fac.get('nombre')}: ${fac.get('monto', 0):,.0f}")
    else:
        print(f"   ❌ NO tiene facturas detalladas")

# Verificar si alguna etiqueta es de estado de pago
estados_pago = ['Facturas Pagadas', 'Facturas Parcialmente Pagadas', 'En Proceso de Pago', 'Facturas No Pagadas']
print("\n" + "=" * 100)
print("VERIFICACIÓN DE ESTADOS DE PAGO:")
print("=" * 100)

for estado in estados_pago:
    encontrado = any(e.get('nombre') == estado for e in etiquetas)
    if encontrado:
        etiq = next(e for e in etiquetas if e.get('nombre') == estado)
        print(f"✅ {estado}: ${etiq.get('monto', 0):,.0f} | Facturas: {etiq.get('total_facturas', 'N/A')}")
    else:
        print(f"❌ {estado}: NO ENCONTRADO")

print("\n" + "=" * 100)
print("ESTRUCTURA JSON DE EJEMPLO (primera etiqueta con facturas):")
print("=" * 100)

for etiq in etiquetas:
    if 'facturas' in etiq:
        print(json.dumps(etiq, indent=2, ensure_ascii=False, default=str)[:2000])
        break
