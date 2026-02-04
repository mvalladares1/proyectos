#!/usr/bin/env python3
"""
Test de Flujo de Caja para Febrero 2026 (Proyección)
Verifica que las facturas pendientes de cobro aparezcan como proyección
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")

from services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

def main():
    print("=" * 80)
    print("FLUJO DE CAJA FEBRERO 2026 (PROYECCIÓN)")
    print("=" * 80)
    
    service = FlujoCajaService(USERNAME, PASSWORD)
    flujo = service.get_flujo_mensualizado('2026-02-01', '2026-02-28')
    
    print(f"Período: {flujo.get('periodo', {})}")
    print(f"Meses: {flujo.get('meses', [])}")
    
    # Buscar concepto 1.1.1
    operacion = flujo.get('actividades', {}).get('OPERACION', {})
    conceptos = operacion.get('conceptos', [])
    
    for conc in conceptos:
        if conc.get('id') == '1.1.1':
            print(f"\nConcepto: {conc['id']} - {conc['nombre']}")
            print(f"Total: ${conc['total']:,.0f}")
            print(f"Montos por mes: {conc.get('montos_por_mes', {})}")
            print()
            for cuenta in conc.get('cuentas', []):
                if cuenta.get('codigo') == '11030101':
                    print(f"  Cuenta 11030101 - Deudores por Ventas:")
                    print(f"    Total: ${cuenta['monto']:,.0f}")
                    etiquetas = cuenta.get('etiquetas', [])
                    if etiquetas:
                        print(f"    Facturas ({len(etiquetas)}):")
                        # Ordenar por monto descendente
                        etiquetas_sorted = sorted(etiquetas, key=lambda x: -abs(x.get('monto', 0)))
                        for etiq in etiquetas_sorted[:15]:
                            print(f"      - {etiq.get('nombre')}: ${etiq.get('monto', 0):,.0f}")
                    break
            break

if __name__ == "__main__":
    main()
