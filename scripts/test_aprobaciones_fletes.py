"""
Script de prueba para el nuevo servicio de aprobaciones de fletes.
Verifica la integración Odoo + API Logística.
"""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.aprobaciones_fletes_service import AprobacionesFletesService

# Credenciales - Usar las mismas que otros scripts
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

def test_servicio():
    print("\n" + "="*80)
    print("TEST: Servicio de Aprobaciones de Fletes")
    print("="*80 + "\n")
    
    # Crear servicio
    service = AprobacionesFletesService(username=USERNAME, password=PASSWORD)
    
    # 1. Obtener OCs pendientes
    print("\n1️⃣ Obteniendo OCs pendientes de aprobación...")
    ocs_pendientes = service.get_ocs_pendientes_aprobacion()
    print(f"   ✅ {len(ocs_pendientes)} OCs pendientes encontradas")
    
    if ocs_pendientes:
        print("\n   Primeras 3 OCs:")
        for oc in ocs_pendientes[:3]:
            print(f"   - {oc.get('name')}: {oc.get('partner_id')[1] if oc.get('partner_id') else 'N/A'} - ${oc.get('amount_total'):,.0f}")
    
    # 2. Obtener rutas de logística
    print("\n2️⃣ Obteniendo rutas del sistema de logística...")
    rutas = service.get_rutas_logistica(con_oc=True)
    print(f"   ✅ {len(rutas)} rutas con OC encontradas")
    
    if rutas:
        print("\n   Primeras 3 rutas:")
        for ruta in rutas[:3]:
            print(f"   - {ruta.get('name')} -> OC: {ruta.get('purchase_order_name')} - ${ruta.get('total_cost'):,.0f}")
    
    # 3. Obtener maestro de costos
    print("\n3️⃣ Obteniendo maestro de costos...")
    costos = service.get_maestro_costos()
    print(f"   ✅ {len(costos)} rutas en maestro de costos")
    
    if costos:
        print("\n   Primeras 3 rutas del maestro:")
        for costo in costos[:3]:
            truck_8 = costo.get('truck_8_cost')
            print(f"   - {costo.get('route_name')}: {costo.get('kilometers')} km - Camión 8T: ${truck_8:,}" if truck_8 else f"   - {costo.get('route_name')}: {costo.get('kilometers')} km")
    
    # 4. Consolidar datos
    print("\n4️⃣ Consolidando datos Odoo + Logística...")
    datos_consolidados = service.consolidar_datos_aprobacion()
    print(f"   ✅ {len(datos_consolidados)} registros consolidados")
    
    if datos_consolidados:
        print("\n   Primeros 3 registros consolidados:")
        for dato in datos_consolidados[:3]:
            print(f"\n   OC: {dato['oc_name']}")
            print(f"   Proveedor: {dato['proveedor']}")
            print(f"   Monto OC: ${dato['oc_amount']:,.0f}")
            print(f"   Tiene info logística: {'✅ Sí' if dato['tiene_info_logistica'] else '❌ No'}")
            
            if dato['tiene_info_logistica']:
                print(f"   Ruta: {dato['ruta_name']}")
                print(f"   Distancia: {dato['distancia_km']:.1f} km")
                print(f"   Costo real: ${dato['costo_real']:,.0f}")
                
                if dato['costo_ruta_negociado']:
                    print(f"   Costo negociado: ${dato['costo_ruta_negociado']:,.0f}")
    
    # 5. Obtener KPIs
    print("\n5️⃣ Obteniendo KPIs del período...")
    kpis = service.get_kpis_fletes(dias=30)
    print(f"   ✅ KPIs calculados:")
    print(f"   Total OCs: {kpis.get('total_ocs', 0)}")
    print(f"   Pendientes: {kpis.get('pendientes', 0)}")
    print(f"   Aprobadas: {kpis.get('aprobadas', 0)}")
    print(f"   Monto total: ${kpis.get('monto_total', 0):,.0f}")
    print(f"   Promedio/OC: ${kpis.get('promedio_por_oc', 0):,.0f}")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETADO")
    print("="*80 + "\n")


if __name__ == "__main__":
    test_servicio()
