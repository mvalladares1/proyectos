"""
Debug: Verificar etiquetas del punto 3 FINANCIAMIENTO
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

svc = FlujoCajaService(USERNAME, PASSWORD)
result = svc.get_flujo_mensualizado('2026-01-01', '2026-02-03')

# Ver etiquetas del punto 3
financiamiento = result.get('actividades', {}).get('FINANCIAMIENTO', {})
for concepto in financiamiento.get('conceptos', []):
    if concepto.get('total', 0) != 0:
        print(f"\n📌 Concepto: {concepto['id']} - {concepto['nombre'][:50]}")
        print(f"   Total: ${concepto['total']:,.0f}")
        
        for cuenta in concepto.get('cuentas', []):
            print(f"\n   💳 Cuenta: {cuenta['codigo']} - Monto: ${cuenta['monto']:,.0f}")
            etiquetas = cuenta.get('etiquetas', [])
            print(f"      Etiquetas encontradas: {len(etiquetas)}")
            
            if etiquetas:
                for et in etiquetas[:10]:
                    print(f"         - {et['nombre'][:40]}: ${et['monto']:,.0f}")
            else:
                print("      ⚠️ SIN ETIQUETAS!")
