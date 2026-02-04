"""Debug: Verificar procesos cerrados via API"""
import httpx

API_URL = "http://127.0.0.1:8002"

# Usar las credenciales de sesión (ajustar según necesidad)
username = input("Username: ")
password = input("Password: ")

print("=" * 80)
print("DEBUG: Consultando API de procesos cerrados")
print("=" * 80)

# Consultar procesos cerrados
params = {
    "username": username,
    "password": password,
    "fecha": "2026-02-01",
    "fecha_fin": "2026-02-04"
}

try:
    print("\n1. Procesos cerrados (endpoint /cerrados):")
    resp = httpx.get(f"{API_URL}/api/v1/produccion/monitor/cerrados", params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    
    procesos = data.get("procesos", [])
    print(f"   Total: {len(procesos)}")
    
    for p in procesos:
        print(f"   - {p.get('name')}: date_finished={p.get('date_finished')}, termino={p.get('x_studio_termino_de_proceso')}")
    
    print("\n2. Evolución (endpoint /evolucion):")
    params_evol = {
        "username": username,
        "password": password,
        "fecha_inicio": "2026-01-28",
        "fecha_fin": "2026-02-04"
    }
    resp2 = httpx.get(f"{API_URL}/api/v1/produccion/monitor/evolucion", params=params_evol, timeout=60)
    resp2.raise_for_status()
    data2 = resp2.json()
    
    for e in data2.get("evolucion", []):
        print(f"   {e['fecha_display']}: creados={e['procesos_creados']}, cerrados={e['procesos_cerrados']}")

except Exception as e:
    print(f"Error: {e}")
