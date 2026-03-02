"""
Ejecuta el servicio REAL de flujo de caja del dashboard y muestra los resultados
de la seccion 3 (Financiamiento).
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'c:\new\RIO FUTURO\DASHBOARD\proyectos')

import json

# Usar las credenciales estaticas
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

from backend.services.flujo_caja_service import FlujoCajaService

print("=" * 80)
print("EJECUTANDO SERVICIO REAL DE FLUJO DE CAJA")
print("=" * 80)

service = FlujoCajaService(username=username, password=password)

print("\n--- Ejecutando get_flujo_mensualizado('2026-01-01', '2026-02-25') ---\n")

resultado = service.get_flujo_mensualizado('2026-01-01', '2026-02-25')

# Extraer seccion de financiamiento
financiamiento = resultado.get('actividades', {}).get('FINANCIAMIENTO', {})

print("\n" + "=" * 80)
print("RESULTADO: SECCION 3 - FINANCIAMIENTO")
print("=" * 80)

print(f"\nNombre: {financiamiento.get('nombre', 'N/A')}")
print(f"Subtotal: ${financiamiento.get('subtotal', 0):,.0f}")

subtotal_por_mes = financiamiento.get('subtotal_por_mes', {})
print(f"\nSubtotal por mes:")
for mes, val in sorted(subtotal_por_mes.items()):
    print(f"  {mes}: ${val:,.0f}")

print(f"\nConceptos:")
for concepto in financiamiento.get('conceptos', []):
    c_id = concepto.get('id', '?')
    c_nombre = concepto.get('nombre', '?')
    c_total = concepto.get('total', 0)
    c_tipo = concepto.get('tipo', '?')
    
    print(f"\n  {c_id} - {c_nombre}")
    print(f"    Tipo: {c_tipo}, Total: ${c_total:,.0f}")
    
    montos_por_mes = concepto.get('montos_por_mes', {})
    if montos_por_mes:
        print(f"    Por mes:")
        for mes, val in sorted(montos_por_mes.items()):
            if val != 0:
                print(f"      {mes}: ${val:,.0f}")
    
    # Mostrar cuentas detalle
    cuentas = concepto.get('cuentas', [])
    if cuentas:
        print(f"    Cuentas ({len(cuentas)}):")
        for cuenta in cuentas[:10]:
            codigo = cuenta.get('codigo', '?')
            nombre = cuenta.get('nombre', '?')
            monto = cuenta.get('monto', 0)
            print(f"      {codigo} ({nombre[:35]}): ${monto:,.0f}")

# Mostrar conciliacion
print(f"\n\n{'='*80}")
print("CONCILIACION")
print(f"{'='*80}")
conciliacion = resultado.get('conciliacion', {})
for k, v in conciliacion.items():
    print(f"  {k}: ${v:,.0f}" if isinstance(v, (int, float)) else f"  {k}: {v}")

# Mostrar todas las actividades y sus totales
print(f"\n\n{'='*80}")
print("RESUMEN TODAS LAS ACTIVIDADES")
print(f"{'='*80}")
for act_key in ['OPERACION', 'INVERSION', 'FINANCIAMIENTO']:
    act = resultado.get('actividades', {}).get(act_key, {})
    print(f"\n{act.get('nombre', act_key)}")
    print(f"  Subtotal: ${act.get('subtotal', 0):,.0f}")
    for mes, val in sorted(act.get('subtotal_por_mes', {}).items()):
        print(f"    {mes}: ${val:,.0f}")

print(f"\n\n{'='*80}")
print("FIN")
print(f"{'='*80}")
