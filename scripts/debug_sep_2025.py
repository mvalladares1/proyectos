"""
DEBUG: Investigar discrepancia Septiembre 2025
Odoo muestra: $852,026,113 (22 pagadas)
Dashboard muestra: $2,183,266,984
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("DEBUG: Flujo de caja Septiembre 2025")
print("=" * 70)

svc = FlujoCajaService(USERNAME, PASSWORD)

# Solo septiembre
result = svc.get_flujo_mensualizado("2025-09-01", "2025-09-30")

print(f"\nMeses: {result.get('meses', [])}")

op = result.get('actividades', {}).get('OPERACION', {})
for c in op.get('conceptos', []):
    if c['id'] == '1.1.1':
        print(f"\n[1.1.1] {c.get('nombre')}")
        print(f"   Total: ${c.get('total', 0):,.0f}")
        print(f"   Por mes: {c.get('montos_por_mes', {})}")
        
        print("\n   Cuentas:")
        for cuenta in c.get('cuentas', [])[:5]:
            print(f"     {cuenta.get('codigo')}: ${cuenta.get('monto', 0):,.0f}")
            
            # Mostrar etiquetas top
            for tag in cuenta.get('etiquetas', [])[:10]:
                print(f"        - {tag.get('nombre')}: ${tag.get('monto', 0):,.0f}")

print("\n" + "=" * 70)
