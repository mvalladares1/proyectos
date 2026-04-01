#!/usr/bin/env python3
"""Debug del KPI $/Kg USD"""
import requests
import json

# Usar la API de logística directamente
BASE_URL = "https://riofuturoprocesos.com/api/logistica"

# Obtener rutas
response = requests.get(f"{BASE_URL}/rutas", timeout=30)
rutas = response.json()

print(f"Total rutas: {len(rutas)}")

# Ver estructura de una ruta
if rutas:
    print("\n=== Ejemplo de ruta ===")
    print(json.dumps(rutas[0], indent=2, default=str))

# Analizar total_qnt
print("\n=== Análisis de total_qnt ===")
total_qnt_values = []
for r in rutas:
    try:
        val = float(r.get('total_qnt', 0) or 0)
        total_qnt_values.append(val)
    except:
        pass

if total_qnt_values:
    print(f"Min: {min(total_qnt_values)}")
    print(f"Max: {max(total_qnt_values)}")
    print(f"Promedio: {sum(total_qnt_values)/len(total_qnt_values):.2f}")
    print(f"Con valor > 0: {len([v for v in total_qnt_values if v > 0])}")
    print(f"Con valor > 1000: {len([v for v in total_qnt_values if v > 1000])}")

# Ver algunas rutas con sus valores
print("\n=== Primeras 5 rutas con total_qnt ===")
for r in rutas[:5]:
    oc = r.get('purchase_order_id')
    if isinstance(oc, list):
        oc = oc[1] if len(oc) > 1 else oc[0]
    print(f"OC: {oc}, total_qnt: {r.get('total_qnt')}, cost_per_kg: {r.get('cost_per_kg')}")
