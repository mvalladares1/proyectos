"""
Test rápido del endpoint de containers
"""
import httpx

url = "http://localhost:8000/api/v1/containers/"
params = {
    "username": "mvalladares@riofuturo.cl",
    "password": "c0766224bec30cac071ffe43a858c9ccbd521ddd",
    "start_date": "2025-12-16",
    "end_date": "2026-01-15"
}

try:
    response = httpx.get(url, params=params, timeout=60.0)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Containers encontrados: {len(data)}")
        if data:
            print(f"\nPrimer container:")
            container = data[0]
            print(f"  - ID: {container.get('id')}")
            print(f"  - Name: {container.get('name')}")
            print(f"  - Partner: {container.get('partner_name')}")
            print(f"  - KG Total: {container.get('kg_total')}")
            print(f"  - KG Producidos: {container.get('kg_producidos')}")
            print(f"  - KG por Producto: {container.get('kg_por_producto')}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()
