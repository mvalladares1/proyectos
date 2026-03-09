#!/bin/bash
curl -s 'http://localhost:8000/api/v1/flujo-caja/semanal?fecha_inicio=2026-03-01&fecha_fin=2026-03-31&username=mvalladares@riofuturo.cl&password=c0766224bec30cac071ffe43a858c9ccbd521ddd&incluir_proyecciones=true' > /tmp/flujo_semanal.json
echo "Response saved to /tmp/flujo_semanal.json"
python3 << 'EOF'
import json

with open('/tmp/flujo_semanal.json') as f:
    data = json.load(f)

# Buscar NEWEN en la respuesta
def search_newen(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            if isinstance(v, str) and 'NEWEN' in v.upper():
                print(f"FOUND: {new_path} = {v}")
            search_newen(v, new_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            search_newen(item, f"{path}[{i}]")

print("Buscando NEWEN en la respuesta...")
search_newen(data)

# Mostrar estructura general
print("\nEstructura de respuesta:")
print(f"Keys: {list(data.keys())[:10]}")
if 'meses' in data:
    print(f"Meses/Periodos: {data['meses']}")
if 'actividades' in data:
    print(f"Actividades: {list(data['actividades'].keys())}")
    for act, act_data in data['actividades'].items():
        print(f"  {act}:")
        if 'conceptos' in act_data:
            for concepto in act_data['conceptos'][:3]:
                print(f"    - {concepto.get('nombre', 'N/A')}")
EOF
