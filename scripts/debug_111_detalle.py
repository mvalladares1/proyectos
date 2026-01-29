"""
DEBUG: Ver qué montos trae el flujo para concepto 1.1.1
Separar REAL vs PROYECTADO
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Periodo historico para ver pagos reales
FECHA_INICIO = "2025-10-01"
FECHA_FIN = "2026-04-30"

print("=" * 70)
print(f"DEBUG: Flujo 1.1.1 - Periodo {FECHA_INICIO} a {FECHA_FIN}")
print("=" * 70)

svc = FlujoCajaService(USERNAME, PASSWORD)

result = svc.get_flujo_mensualizado(FECHA_INICIO, FECHA_FIN)

print("\n[MESES]:", result.get('meses', []))

# Buscar concepto 1.1.1
op_data = result.get('actividades', {}).get('OPERACION', {})
for concepto in op_data.get('conceptos', []):
    if concepto.get('id') == '1.1.1':
        print(f"\n[1.1.1] {concepto.get('nombre')}")
        print(f"   Total: ${concepto.get('total', 0):,.0f}")
        print("   Por mes:")
        for mes, monto in concepto.get('montos_por_mes', {}).items():
            if monto != 0:
                print(f"     {mes}: ${monto:,.0f}")
        
        print("\n   Cuentas (detalle):")
        for cuenta in concepto.get('cuentas', [])[:10]:
            print(f"     {cuenta.get('codigo')}: {cuenta.get('nombre', '')[:30]} = ${cuenta.get('monto', 0):,.0f}")
            # Ver por mes
            for mes, m in cuenta.get('montos_por_mes', {}).items():
                if m != 0:
                    print(f"        {mes}: ${m:,.0f}")
            
            # Ver etiquetas si existen
            if 'etiquetas' in cuenta:
                print(f"        [ETIQUETAS]:")
                for tag_data in cuenta.get('etiquetas', []):
                    tag_nombre = tag_data.get('nombre', 'Unknown')
                    monto_tag = tag_data.get('monto', 0)
                    if abs(monto_tag) > 1000000: # Solo > 1M
                        print(f"           - {tag_nombre[:40]}: ${monto_tag:,.0f}")

print("\n" + "=" * 70)
print("FIN DEBUG")
