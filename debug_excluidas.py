#!/usr/bin/env python3
"""Buscar cuentas excluidas en la respuesta del API"""
import json

with open('/tmp/flujo_semanal.json') as f:
    data = json.load(f)

# Buscar las cuentas excluidas
cuentas_excluir = ['21020101', '11060101', '62010101']

def buscar_cuenta(obj, path=''):
    if isinstance(obj, dict):
        codigo = str(obj.get('codigo', ''))
        nombre = str(obj.get('nombre', ''))
        for cuenta in cuentas_excluir:
            if cuenta in codigo or cuenta in nombre:
                print(f'ENCONTRADA: {path}')
                print(f'  codigo: {codigo}')
                print(f'  nombre: {nombre}')
                montos = obj.get('montos_por_mes', {})
                print(f'  montos: {montos}')
                print()
        for k, v in obj.items():
            buscar_cuenta(v, path + '.' + k if path else k)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            buscar_cuenta(item, path + '[' + str(i) + ']')

print('Buscando cuentas excluidas: 21020101, 11060101, 62010101')
print('='*80)
buscar_cuenta(data)
print('Busqueda terminada.')
