"""
Debug: Verificar montos_por_mes de etiquetas en septiembre 2025
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")

from shared.odoo_client import OdooClient
from backend.services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

service = FlujoCajaService(USERNAME, PASSWORD)
flujo = service.get_flujo_mensualizado('2025-09-01', '2025-09-30')

print(f"Meses en resultado: {flujo.get('meses', [])}")

operacion = flujo.get('actividades', {}).get('OPERACION', {})
for c in operacion.get('conceptos', []):
    if c.get('id') == '1.1.1':
        print(f"\nConcepto 1.1.1 - montos_por_mes: {c.get('montos_por_mes')}")
        for cuenta in c.get('cuentas', []):
            if cuenta.get('codigo') == '11030101':
                print(f"\nCuenta 11030101 - montos_por_mes: {cuenta.get('montos_por_mes')}")
                print(f"\nEtiquetas ({len(cuenta.get('etiquetas', []))}):")
                for et in cuenta.get('etiquetas', [])[:10]:
                    print(f"  - {et.get('nombre')}")
                    print(f"    monto total: {et.get('monto')}")
                    print(f"    montos_por_mes: {et.get('montos_por_mes')}")
