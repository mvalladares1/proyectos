"""
Debug para verificar TRONADOR - montos por periodo
"""
import requests

API_URL = "http://167.114.114.51:8002"
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("DATOS EN API (1.1.1) - TRONADOR")
print("=" * 70)

resp = requests.get(
    f"{API_URL}/api/v1/flujo-caja/semanal",
    params={
        "fecha_inicio": "2026-01-01",
        "fecha_fin": "2026-02-28",
        "username": USERNAME,
        "password": PASSWORD
    },
    timeout=120
)

data = resp.json()
conceptos = data.get('actividades', {}).get('OPERACION', {}).get('conceptos', [])
concepto_111 = next((c for c in conceptos if c.get('id') == '1.1.1'), None)

if concepto_111:
    print(f"\nConcepto 1.1.1 - Total: ${concepto_111.get('total', 0):,.0f}")
    
    for cuenta in concepto_111.get('cuentas', []):
        nombre = cuenta.get('nombre', '').replace('\u2705', '[OK]').replace('\u23f3', '[P]').replace('\u274c', '[X]')
        
        for etiq in cuenta.get('etiquetas', []):
            if 'TRONADOR' in str(etiq.get('nombre', '')).upper():
                print(f"\n  Estado: {nombre}")
                print(f"  Cliente: {etiq.get('nombre', '')}")
                print(f"  Monto total: ${etiq.get('monto', 0):,.0f}")
                print(f"  Real: ${etiq.get('real', 0):,.0f}")
                print(f"  Proyectado: ${etiq.get('proyectado', 0):,.0f}")
                
                print(f"\n  Montos por periodo:")
                for periodo, monto in sorted(etiq.get('montos_por_mes', {}).items()):
                    if monto != 0:
                        print(f"    {periodo}: ${monto:,.0f}")
else:
    print("Concepto 1.1.1 no encontrado")

print("\nVerificacion completada")
