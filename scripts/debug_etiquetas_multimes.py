"""
Debug: Verificar etiquetas en consulta multi-mes
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")

from backend.services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Consulta similar a la del frontend (varios meses)
service = FlujoCajaService(USERNAME, PASSWORD)
flujo = service.get_flujo_mensualizado('2025-09-01', '2026-03-31')

print(f"Meses en resultado: {flujo.get('meses', [])}")

operacion = flujo.get('actividades', {}).get('OPERACION', {})
for c in operacion.get('conceptos', []):
    if c.get('id') == '1.1.1':
        print(f"\nConcepto 1.1.1 - Total: {c.get('total')}")
        print(f"montos_por_mes: {c.get('montos_por_mes')}")
        
        for cuenta in c.get('cuentas', []):
            if cuenta.get('codigo') == '11030101':
                print(f"\nCuenta 11030101 - Total: {cuenta.get('monto')}")
                print(f"montos_por_mes: {cuenta.get('montos_por_mes')}")
                
                print(f"\nEtiquetas ({len(cuenta.get('etiquetas', []))}):")
                for et in cuenta.get('etiquetas', [])[:15]:
                    nombre = et.get('nombre', '')
                    monto_total = et.get('monto', 0)
                    montos_mes = et.get('montos_por_mes', {})
                    
                    # Mostrar solo meses con valor
                    meses_con_valor = {k: v for k, v in montos_mes.items() if v != 0}
                    
                    print(f"  - {nombre}")
                    print(f"    monto total: ${monto_total:,.0f}")
                    print(f"    meses con valor: {meses_con_valor}")
