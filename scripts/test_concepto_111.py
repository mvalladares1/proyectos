"""
TEST: Verificar concepto 1.1.1 en flujo mensualizado
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"
FECHA_INICIO = "2025-12-01"
FECHA_FIN = "2026-05-31"

print("=" * 70)
print("TEST: Concepto 1.1.1 en get_flujo_mensualizado")
print("=" * 70)

svc = FlujoCajaService(USERNAME, PASSWORD)
print("[OK] Conexion OK")

result = svc.get_flujo_mensualizado(FECHA_INICIO, FECHA_FIN)

for act_key, act_data in result.get('actividades', {}).items():
    print(f"\n[{act_key}] subtotal: ${act_data.get('subtotal', 0):,.0f}")
    for c in act_data.get('conceptos', []):
        cod = c.get('id')
        nombre = c.get('nombre', '')[:35]
        total = c.get('total', 0)
        if cod == '1.1.1' or abs(total) > 0:
            print(f"   * {cod}: {nombre} = ${total:,.0f}")
            if cod == '1.1.1' and c.get('cuentas'):
                for cuenta in c['cuentas'][:3]:
                    print(f"     - {cuenta.get('codigo')}: ${cuenta.get('monto', 0):,.0f}")

print("\n" + "=" * 70 + "\nTEST COMPLETADO")
