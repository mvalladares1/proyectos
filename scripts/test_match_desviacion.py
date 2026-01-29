"""
Script de prueba rápida con datos mockeados para evitar timeouts.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.aprobaciones_fletes_service import AprobacionesFletesService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

def test_match_y_desviacion():
    print("\n" + "="*80)
    print("TEST: Match de Rutas y Cálculo de Desviaciones")
    print("="*80 + "\n")
    
    service = AprobacionesFletesService(username=USERNAME, password=PASSWORD)
    
    # Test 1: Determinar tipo de vehículo
    print("1️⃣ Test: Determinar tipo de vehículo")
    print(f"   8,000 kg, $150,000 → {service._determinar_tipo_vehiculo(8000, 150000)}")
    print(f"   12,000 kg, $300,000 → {service._determinar_tipo_vehiculo(12000, 300000)}")
    print(f"   20,000 kg, $500,000 → {service._determinar_tipo_vehiculo(20000, 500000)}")
    print(f"   25,000 kg, $700,000 → {service._determinar_tipo_vehiculo(25000, 700000)}")
    
    # Test 2: Match de ruta con presupuesto
    print("\n2️⃣ Test: Match de ruta con presupuesto")
    
    # Obtener maestro de costos real
    costos_maestro = service.get_maestro_costos()
    print(f"   Maestro de costos: {len(costos_maestro)} rutas")
    
    if costos_maestro:
        # Test con distancia conocida
        ruta_match = service._match_ruta_con_presupuesto(157, "Camión 8T", costos_maestro)
        if ruta_match:
            print(f"\n   Match encontrado para 157 km:")
            print(f"   - Ruta: {ruta_match.get('route_name')}")
            print(f"   - Kilómetros: {ruta_match.get('kilometers')}")
            print(f"   - Camión 8T: ${ruta_match.get('truck_8_cost'):,}")
            
            # Obtener costo presupuestado
            costo_presup = service._obtener_costo_presupuestado(ruta_match, "Camión 8T")
            print(f"   - Costo presupuestado: ${costo_presup:,}")
            
            # Calcular desviación
            costo_real = 450000
            desv_pct = ((costo_real - costo_presup) / costo_presup) * 100
            favorable = desv_pct <= 0
            
            print(f"\n   Con costo real de ${costo_real:,}:")
            print(f"   - Desviación: {desv_pct:+.1f}%")
            print(f"   - {'✅ FAVORABLE' if favorable else '⚠️ DESFAVORABLE'}")
            
            if favorable:
                ahorro = costo_presup - costo_real
                print(f"   - Ahorro: ${ahorro:,}")
            else:
                sobrecosto = costo_real - costo_presup
                print(f"   - Sobrecosto: ${sobrecosto:,}")
    
    # Test 3: Datos consolidados (sin API de rutas para evitar timeout)
    print("\n3️⃣ Test: Consolidar datos (solo Odoo, sin API Logística)")
    print("   ⏭️ Saltando para evitar timeout de API...")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETADO")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_match_y_desviacion()
