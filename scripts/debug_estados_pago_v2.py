"""
Debug: Verificar nueva estructura de estados de pago
"""
import sys
import os
sys.path.insert(0, "c:/new/RIO FUTURO/DASHBOARD/proyectos")

from dotenv import load_dotenv
load_dotenv("c:/new/RIO FUTURO/DASHBOARD/proyectos/.env")

from backend.services.flujo_caja_service import FlujoCajaService
from pprint import pprint

def main():
    service = FlujoCajaService()
    
    # Test con rango Oct-Dic 2025
    resultado = service.get_flujo_mensualizado(
        fecha_inicio="2025-10-01",
        fecha_fin="2025-12-31"
    )
    
    print("="*80)
    print("BUSCANDO ESTRUCTURA DE ESTADOS DE PAGO")
    print("="*80)
    
    # Buscar concepto 1.1.1 (Ingresos operacionales)
    for actividad, conceptos in resultado.get('conceptos', {}).items():
        print(f"\n{actividad}:")
        for concepto in conceptos:
            concepto_id = concepto.get('id', '')
            if concepto_id == '1.1.1':
                print(f"\n  CONCEPTO: {concepto.get('nombre')} ({concepto_id})")
                
                for cuenta in concepto.get('cuentas', []):
                    codigo = cuenta.get('codigo')
                    nombre = cuenta.get('nombre')
                    es_cxc = cuenta.get('es_cuenta_cxc', False)
                    
                    print(f"\n    CUENTA: {codigo} - {nombre}")
                    print(f"    es_cuenta_cxc: {es_cxc}")
                    
                    etiquetas = cuenta.get('etiquetas', [])
                    print(f"    Etiquetas ({len(etiquetas)}):")
                    
                    for etiq in etiquetas:
                        nombre_etiq = etiq.get('nombre')
                        monto = etiq.get('monto', 0)
                        montos_mes = etiq.get('montos_por_mes', {})
                        facturas = etiq.get('facturas', [])
                        total_facturas = etiq.get('total_facturas', 0)
                        
                        print(f"\n      📊 {nombre_etiq}")
                        print(f"         Monto total: ${monto:,.0f}")
                        print(f"         Por mes: {montos_mes}")
                        
                        if facturas:
                            print(f"         📋 Facturas ({len(facturas)}/{total_facturas}):")
                            for i, fact in enumerate(facturas[:5]):  # Solo primeras 5
                                fact_nombre = fact.get('nombre')
                                fact_monto = fact.get('monto', 0)
                                fact_mes = fact.get('montos_por_mes', {})
                                print(f"            {i+1}. {fact_nombre}: ${fact_monto:,.0f}")
                                # Mostrar mes donde tiene monto
                                for mes, val in fact_mes.items():
                                    if val != 0:
                                        print(f"               └── {mes}: ${val:,.0f}")
                            
                            if len(facturas) > 5:
                                print(f"            ... y {len(facturas)-5} facturas más")
    
    print("\n" + "="*80)
    print("FIN DEL DEBUG")
    print("="*80)

if __name__ == "__main__":
    main()
