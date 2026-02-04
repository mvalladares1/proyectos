"""
TEST: Verificar estructura completa del flujo de caja
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")

from shared.odoo_client import OdooClient
from backend.services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 80)
print("TEST: Estructura Flujo de Caja Sep-Nov 2025")
print("=" * 80)

service = FlujoCajaService(USERNAME, PASSWORD)
flujo = service.get_flujo_mensualizado('2025-09-01', '2025-11-30')

print(f"\nPeríodo: {flujo.get('periodo', {})}")
print(f"Meses: {flujo.get('meses', [])}")

# Buscar concepto 1.1.1
operacion = flujo.get('actividades', {}).get('OPERACION', {})
conceptos = operacion.get('conceptos', [])

for c in conceptos:
    if c.get('id') == '1.1.1':
        print(f"\n{'='*60}")
        print(f"Concepto: {c['id']} - {c['nombre']}")
        print(f"Total: ${c['total']:,.0f}")
        print(f"Montos por mes: {c.get('montos_por_mes', {})}")
        
        cuentas = c.get('cuentas', [])
        print(f"\nCuentas ({len(cuentas)}):")
        
        for cuenta in cuentas:
            codigo = cuenta.get('codigo')
            monto = cuenta.get('monto', 0)
            montos_mes = cuenta.get('montos_por_mes', {})
            print(f"\n  📄 {codigo} - {cuenta.get('nombre', '')}")
            print(f"     Total: ${monto:,.0f}")
            print(f"     Por mes: {montos_mes}")
            
            etiquetas = cuenta.get('etiquetas', [])
            if etiquetas:
                print(f"     Etiquetas ({len(etiquetas)}):")
                for et in etiquetas[:10]:
                    nombre = et.get('nombre', '')
                    monto_et = et.get('monto', 0)
                    montos_et_mes = et.get('montos_por_mes', {})
                    print(f"       - {nombre}: ${monto_et:,.0f}")
                    # Mostrar desglose por mes si hay valores
                    meses_con_valor = {k: v for k, v in montos_et_mes.items() if v != 0}
                    if meses_con_valor:
                        print(f"         Desglose: {meses_con_valor}")
        break

print("\n" + "=" * 80)
print("Test completado")
