"""
Script para explorar la API de logística y entender la estructura de datos.
Endpoints:
- https://riofuturoprocesos.com/api/logistica/rutas
- https://riofuturoprocesos.com/api/logistica/db/coste-rutas
"""

import requests
import json
from datetime import datetime

# Configuración
API_BASE = "https://riofuturoprocesos.com/api/logistica"

def explorar_endpoint(endpoint_path, nombre="Endpoint"):
    """Explora un endpoint y muestra su estructura"""
    url = f"{API_BASE}/{endpoint_path}"
    print(f"\n{'='*80}")
    print(f"🔍 Explorando: {nombre}")
    print(f"URL: {url}")
    print(f"{'='*80}\n")
    
    try:
        response = requests.get(url, timeout=30)
        print(f"✅ Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"📊 Tipo de dato: {type(data)}")
                
                if isinstance(data, list):
                    print(f"📝 Total de registros: {len(data)}")
                    if len(data) > 0:
                        print(f"\n📋 Estructura del primer registro:")
                        print(json.dumps(data[0], indent=2, ensure_ascii=False))
                        
                        if len(data) > 1:
                            print(f"\n📋 Estructura del segundo registro:")
                            print(json.dumps(data[1], indent=2, ensure_ascii=False))
                        
                        # Mostrar todos los campos únicos
                        all_keys = set()
                        for item in data[:10]:  # Primeros 10 registros
                            if isinstance(item, dict):
                                all_keys.update(item.keys())
                        
                        print(f"\n🔑 Campos encontrados (primeros 10 registros):")
                        for key in sorted(all_keys):
                            print(f"  - {key}")
                
                elif isinstance(data, dict):
                    print(f"🔑 Claves principales: {list(data.keys())}")
                    print(f"\n📋 Estructura completa:")
                    print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
                
                else:
                    print(f"📄 Contenido: {str(data)[:1000]}")
                
                return data
                
            except json.JSONDecodeError:
                print(f"⚠️ Respuesta no es JSON válido")
                print(f"📄 Contenido (primeros 500 chars):\n{response.text[:500]}")
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            print(f"📄 Respuesta: {response.text[:500]}")
            
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout al conectar con el endpoint")
    except requests.exceptions.ConnectionError as e:
        print(f"🔌 Error de conexión: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {type(e).__name__}: {e}")
    
    return None


def main():
    print("\n" + "="*80)
    print("🚚 EXPLORACIÓN DE API DE LOGÍSTICA - RÍO FUTURO")
    print("="*80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Explorar endpoint de rutas
    rutas_data = explorar_endpoint("rutas", "Rutas de Logística")
    
    # Explorar endpoint de coste-rutas
    coste_data = explorar_endpoint("db/coste-rutas", "Costos de Rutas")
    
    # Análisis cruzado si hay datos
    if rutas_data and coste_data:
        print(f"\n{'='*80}")
        print("🔗 ANÁLISIS CRUZADO DE DATOS")
        print(f"{'='*80}\n")
        
        if isinstance(rutas_data, list) and isinstance(coste_data, list):
            print(f"📊 Rutas encontradas: {len(rutas_data)}")
            print(f"💰 Costos encontrados: {len(coste_data)}")
            
            # Intentar encontrar campos de relación
            if len(rutas_data) > 0 and len(coste_data) > 0:
                ruta_keys = set(rutas_data[0].keys()) if isinstance(rutas_data[0], dict) else set()
                coste_keys = set(coste_data[0].keys()) if isinstance(coste_data[0], dict) else set()
                
                common_keys = ruta_keys & coste_keys
                if common_keys:
                    print(f"\n🔑 Campos en común (posibles claves de relación):")
                    for key in sorted(common_keys):
                        print(f"  - {key}")
    
    print("\n" + "="*80)
    print("✅ EXPLORACIÓN COMPLETADA")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
