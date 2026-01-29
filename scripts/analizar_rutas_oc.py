"""
Script para analizar rutas con OC generadas y su relación con Odoo.
Busca rutas que tengan purchase_order_name para entender la integración.
"""

import requests
import json
import os
from datetime import datetime

# Configuración
API_BASE = "https://riofuturoprocesos.com/api/logistica"

# Credenciales Odoo
ODOO_USERNAME = os.getenv('ODOO_USERNAME', 'mvalladares@riofuturo.cl')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')

def get_rutas_con_oc():
    """Obtiene rutas que tienen OC generadas"""
    url = f"{API_BASE}/rutas"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            rutas = response.json()
            
            # Filtrar rutas con OC
            rutas_con_oc = [r for r in rutas if r.get('purchase_order_name')]
            
            print(f"📊 Total de rutas: {len(rutas)}")
            print(f"📋 Rutas con OC generada: {len(rutas_con_oc)}")
            
            if rutas_con_oc:
                print(f"\n{'='*80}")
                print("🔍 RUTAS CON ORDEN DE COMPRA GENERADA")
                print(f"{'='*80}\n")
                
                for i, ruta in enumerate(rutas_con_oc[:10], 1):  # Primeras 10
                    print(f"\n--- Ruta #{i} ---")
                    print(f"ID Ruta: {ruta.get('id')}")
                    print(f"Nombre Ruta: {ruta.get('name')}")
                    print(f"Estado: {ruta.get('status')}")
                    print(f"OC: {ruta.get('purchase_order_name')}")
                    print(f"URL OC: {ruta.get('purchase_order_url')}")
                    print(f"Transportista: {ruta.get('carrier_id')}")
                    print(f"Distancia: {ruta.get('total_distance_km')} km")
                    print(f"Costo Ruta: ${ruta.get('route_cost'):,.0f}" if ruta.get('route_cost') else "Costo Ruta: N/A")
                    print(f"Costo Total: ${ruta.get('total_cost'):,.0f}" if ruta.get('total_cost') else "Costo Total: N/A")
                    print(f"Cantidad: {ruta.get('total_qnt')} kg")
                    print(f"Costo por kg: ${ruta.get('cost_per_kg'):.2f}" if ruta.get('cost_per_kg') else "Costo por kg: N/A")
                    print(f"Fecha estimada: {ruta.get('estimated_date')}")
            
            return rutas_con_oc
        else:
            print(f"❌ Error al obtener rutas: {response.status_code}")
            return []
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def get_coste_rutas():
    """Obtiene maestro de costos de rutas"""
    url = f"{API_BASE}/db/coste-rutas"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            costos = response.json()
            
            print(f"\n{'='*80}")
            print("💰 MAESTRO DE COSTOS DE RUTAS")
            print(f"{'='*80}\n")
            print(f"Total de rutas en maestro: {len(costos)}")
            
            # Mostrar primeros 10
            print(f"\n📋 Primeras rutas del maestro:\n")
            for i, costo in enumerate(costos[:10], 1):
                print(f"{i}. {costo.get('route_name')}")
                print(f"   Kilómetros: {costo.get('kilometers')} km")
                print(f"   Camión 8T: ${costo.get('truck_8_cost'):,}" if costo.get('truck_8_cost') else "   Camión 8T: N/A")
                print(f"   Camión 12-14T: ${costo.get('truck_12_14_cost'):,}" if costo.get('truck_12_14_cost') else "   Camión 12-14T: N/A")
                print(f"   Rampla Corta: ${costo.get('short_rampla_cost'):,}" if costo.get('short_rampla_cost') else "   Rampla Corta: N/A")
                print(f"   Rampla: ${costo.get('rampla_cost'):,}" if costo.get('rampla_cost') else "   Rampla: N/A")
                print()
            
            return costos
        else:
            print(f"❌ Error al obtener costos: {response.status_code}")
            return []
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def buscar_oc_en_odoo(purchase_order_names):
    """Busca las OC en Odoo para comparar información"""
    if not ODOO_PASSWORD:
        print("\n⚠️ No se encontró password de Odoo en variables de entorno")
        print("   Para conectar con Odoo, configura ODOO_PASSWORD")
        return []
    
    try:
        from shared.odoo_client import OdooClient
        
        odoo = OdooClient(username=ODOO_USERNAME, password=ODOO_PASSWORD)
        
        print(f"\n{'='*80}")
        print("🔗 BÚSQUEDA EN ODOO")
        print(f"{'='*80}\n")
        
        # Buscar OCs por nombre
        domain = [('name', 'in', purchase_order_names)]
        fields = [
            'id', 'name', 'state', 'partner_id', 'amount_total',
            'x_studio_selection_field_yUNPd',  # Campo TRANSPORTES
            'x_studio_categora_de_producto',   # Campo SERVICIOS
            'user_id',  # Responsable
            'date_order'
        ]
        
        ocs = odoo.search_read('purchase.order', domain, fields, limit=100)
        
        print(f"📋 OCs encontradas en Odoo: {len(ocs)}\n")
        
        for oc in ocs:
            print(f"\n--- OC: {oc.get('name')} ---")
            print(f"Estado: {oc.get('state')}")
            print(f"Proveedor: {oc.get('partner_id')[1] if oc.get('partner_id') else 'N/A'}")
            print(f"Monto Total: ${oc.get('amount_total'):,.0f}" if oc.get('amount_total') else "Monto: N/A")
            print(f"Tipo: {oc.get('x_studio_selection_field_yUNPd')}")
            print(f"Categoría: {oc.get('x_studio_categora_de_producto')}")
            print(f"Responsable: {oc.get('user_id')[1] if oc.get('user_id') else 'N/A'}")
            print(f"Fecha: {oc.get('date_order')}")
        
        return ocs
    
    except ImportError:
        print("\n⚠️ No se pudo importar OdooClient")
        return []
    except Exception as e:
        print(f"\n❌ Error al consultar Odoo: {e}")
        return []


def analizar_desviaciones(rutas_oc, costos_maestro):
    """Analiza desviaciones entre costo real y presupuestado"""
    print(f"\n{'='*80}")
    print("📊 ANÁLISIS DE DESVIACIONES")
    print(f"{'='*80}\n")
    
    # TODO: Implementar lógica de match entre rutas y costos
    # Necesitamos entender cómo se relacionan (por nombre, por kilómetros, etc.)
    
    print("⚠️ Función de análisis de desviaciones pendiente de implementar")
    print("   Se requiere entender la lógica de match entre:")
    print("   - Nombre de ruta en sistema logística")
    print("   - Ruta en maestro de costos")
    print("   - Tipo de vehículo utilizado")


def main():
    print("\n" + "="*80)
    print("🚚 ANÁLISIS DE RUTAS CON OC PARA APROBACIONES DE MÁXIMO")
    print("="*80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. Obtener rutas con OC
    rutas_con_oc = get_rutas_con_oc()
    
    # 2. Obtener maestro de costos
    costos = get_coste_rutas()
    
    # 3. Si hay rutas con OC, buscarlas en Odoo
    if rutas_con_oc:
        oc_names = [r.get('purchase_order_name') for r in rutas_con_oc if r.get('purchase_order_name')]
        if oc_names:
            ocs_odoo = buscar_oc_en_odoo(oc_names)
    
    # 4. Análisis de desviaciones
    if rutas_con_oc and costos:
        analizar_desviaciones(rutas_con_oc, costos)
    
    print("\n" + "="*80)
    print("✅ ANÁLISIS COMPLETADO")
    print("="*80 + "\n")
    
    print("\n💡 PRÓXIMOS PASOS:")
    print("1. Crear servicio backend para consolidar datos Odoo + Logística")
    print("2. Implementar lógica de match entre rutas y costos presupuestados")
    print("3. Calcular % de desviación (costo real vs presupuestado)")
    print("4. Crear UI en Streamlit para aprobaciones masivas")
    print("5. Agregar KPIs: desviación promedio, mejor/peor negociación, etc.\n")


if __name__ == "__main__":
    main()
