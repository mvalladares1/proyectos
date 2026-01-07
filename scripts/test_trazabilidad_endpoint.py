"""
Script de prueba para verificar el endpoint de trazabilidad de pallets.
"""
import requests
import json

# Configuración
API_URL = "http://127.0.0.1:8002"  # DEV
USERNAME = "tu_usuario"  # Reemplazar
PASSWORD = "tu_password"  # Reemplazar

# Lista de pallets a probar
pallets = ["TEST-PALLET-001"]

# Probar el endpoint
print("🔍 Probando endpoint de trazabilidad de pallets...")
print(f"URL: {API_URL}/api/v1/rendimiento/trazabilidad-pallets")
print(f"Pallets: {pallets}")
print("-" * 60)

try:
    # Opción 1: Enviando como lista directa en el body
    print("\n📦 Intento 1: Lista directa en body")
    response = requests.post(
        f"{API_URL}/api/v1/rendimiento/trazabilidad-pallets",
        params={"username": USERNAME, "password": PASSWORD},
        json=pallets,  # Lista directa
        timeout=30
    )
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("✅ Éxito!")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ Error: {response.text}")
    
except Exception as e:
    print(f"❌ Exception: {str(e)}")

print("\n" + "=" * 60)

try:
    # Opción 2: Enviando como objeto con key "pallet_names"
    print("\n📦 Intento 2: Objeto con key 'pallet_names'")
    response = requests.post(
        f"{API_URL}/api/v1/rendimiento/trazabilidad-pallets",
        params={"username": USERNAME, "password": PASSWORD},
        json={"pallet_names": pallets},  # Objeto con key
        timeout=30
    )
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("✅ Éxito!")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ Error: {response.text}")
    
except Exception as e:
    print(f"❌ Exception: {str(e)}")

print("\n" + "=" * 60)

# Verificar todos los endpoints disponibles
print("\n📋 Listando todos los endpoints de rendimiento:")
try:
    response = requests.get(f"{API_URL}/docs")
    if response.status_code == 200:
        print("✅ API está corriendo")
        print("👉 Ver documentación en: http://127.0.0.1:8002/docs")
    else:
        print(f"❌ Error al obtener docs: {response.status_code}")
except Exception as e:
    print(f"❌ Exception: {str(e)}")
