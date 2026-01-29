"""
TEST: Verificar implementación concepto 1.1.1
Usa get_flujo_efectivo que invoca ProyeccionFlujo
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

FECHA_INICIO = "2025-12-01"
FECHA_FIN = "2026-02-28"

print("=" * 80)
print("TEST: Concepto 1.1.1 en proyección de flujo de caja")
print(f"Período: {FECHA_INICIO} a {FECHA_FIN}")
print("=" * 80)

try:
    svc = FlujoCajaService(USERNAME, PASSWORD)
    print("✅ Servicio inicializado")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Obtener flujo efectivo (que incluye proyección)
print("\n📊 Obteniendo flujo de efectivo (incluye proyección)...")
result = svc.get_flujo_efectivo(FECHA_INICIO, FECHA_FIN)

# Revisar proyección
proyeccion = result.get('proyeccion', {})
print(f"\n📋 PROYECCIÓN:")

if 'error' in proyeccion:
    print(f"   ❌ Error: {proyeccion['error']}")
else:
    actividades = proyeccion.get('actividades', {})
    for act_key, act_data in actividades.items():
        print(f"\n🔹 {act_key} (subtotal: ${act_data.get('subtotal', 0):,.0f}):")
        for concepto in act_data.get('conceptos', []):
            codigo = concepto.get('codigo')
            nombre = concepto.get('nombre', '')[:40]
            monto = concepto.get('monto', 0)
            docs = concepto.get('documentos', [])
            
            # Mostrar 1.1.1 siempre, otros solo si tienen monto
            if codigo == '1.1.1' or monto != 0:
                print(f"   • {codigo}: {nombre}")
                print(f"     Monto: ${monto:,.0f} ({len(docs)} docs)")
                if docs and codigo == '1.1.1':
                    for d in docs[:3]:
                        print(f"       - {d.get('documento')}: {d.get('partner', '')[:25]} = ${d.get('monto', 0):,.0f}")
    
    # Sin clasificar
    sin_clas = proyeccion.get('sin_clasificar', [])
    monto_sin = proyeccion.get('monto_sin_clasificar', 0)
    if sin_clas:
        print(f"\n⚠️ SIN CLASIFICAR: {len(sin_clas)} docs, ${monto_sin:,.0f}")

print("\n" + "=" * 80)
print("TEST COMPLETADO")
print("=" * 80)
