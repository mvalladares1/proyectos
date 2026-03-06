#!/usr/bin/env python3
import json

with open('/tmp/flujo_semanal.json') as f:
    data = json.load(f)

print('PERIODOS EN LA RESPUESTA:', data.get('meses'))
print()

# Buscar S10 / W10 en todos los montos por mes
print('BUSCANDO VALORES EN 2026-W10:')
def find_w10(obj, path=''):
    if isinstance(obj, dict):
        montos = obj.get('montos_por_mes', {})
        w10_val = montos.get('2026-W10', 0)
        if w10_val != 0:
            print(f"  {path}: {w10_val:,.0f}")
        for k, v in obj.items():
            find_w10(v, path + '.' + k if path else k)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_w10(item, path + '[' + str(i) + ']')

find_w10(data)

# Mostrar totales por semana para todo OPERACION
print()
print('TOTALES POR SEMANA EN OPERACION:')
operacion = data['actividades']['OPERACION']
totales_semana = {}
for concepto in operacion.get('conceptos', []):
    montos = concepto.get('montos_por_mes', {})
    for sem, val in montos.items():
        totales_semana[sem] = totales_semana.get(sem, 0) + val

for sem in sorted(totales_semana.keys()):
    print(f"  {sem}: {totales_semana[sem]:,.0f}")
