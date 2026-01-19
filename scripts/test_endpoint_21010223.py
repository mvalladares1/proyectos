"""
Test rápido del endpoint de flujo de caja para ver qué trae para cuenta 21010223
"""
import requests
import json

url = "http://riofuturoprocesos.com:8002/flujo_caja/mensual"
params = {
    "fecha_inicio": "2026-01-01",
    "fecha_fin": "2026-03-31",
    "username": "mvalladares@riofuturo.cl",
    "password": "c0766224bec30cac071ffe43a858c9ccbd521ddd"
}

print("Consultando flujo de caja enero-marzo 2026...")
response = requests.get(url, params=params, timeout=120)

if response.status_code == 200:
    data = response.json()
    
    # Buscar cuenta 21010223 en todos los conceptos
    print("\nBuscando cuenta 21010223...")
    
    for actividad_nombre, actividad_data in data.get("actividades", {}).items():
        for concepto in actividad_data.get("conceptos", []):
            if concepto.get("tipo") != "LINEA":
                continue
                
            for cuenta in concepto.get("cuentas", []):
                if cuenta.get("codigo") == "21010223":
                    print(f"\n✓ ENCONTRADA en {actividad_nombre}")
                    print(f"  Concepto: {concepto.get('id')} - {concepto.get('nombre')}")
                    print(f"  Código: {cuenta.get('codigo')}")
                    print(f"  Nombre: {cuenta.get('nombre')}")
                    print(f"  Monto total: ${cuenta.get('monto'):,.0f}")
                    print(f"\n  Montos por mes:")
                    montos_mes = cuenta.get("montos_por_mes", {})
                    for mes in sorted(montos_mes.keys()):
                        print(f"    {mes}: ${montos_mes[mes]:,.0f}")
                    
                    # Ver etiquetas
                    etiquetas = cuenta.get("etiquetas", [])
                    if etiquetas:
                        print(f"\n  Etiquetas: {len(etiquetas)}")
                        for etiq in etiquetas:
                            print(f"    - {etiq.get('nombre')}: ${etiq.get('monto'):,.0f}")
                    
                    print("\n" + "="*60)
else:
    print(f"Error {response.status_code}: {response.text}")
