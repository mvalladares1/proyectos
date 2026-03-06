#!/usr/bin/env python3
"""Debug: Simular lógica de RealProyectadoCalculator para NEWEN"""
import sys
sys.path.insert(0, '/app')

from backend.services.flujo_caja.real_proyectado import RealProyectadoCalculator
from shared.odoo_client import OdooClient

username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

print("Iniciando cliente Odoo...")
odoo = OdooClient(username=username, password=password)
calculator = RealProyectadoCalculator(odoo_client=odoo)

print("Llamando calcular_pagos_proveedores...")
# Generar lista de semanas para marzo 2026
from datetime import datetime, timedelta
start = datetime(2026, 3, 1)
end = datetime(2026, 3, 31)
semanas = []
current = start
while current <= end:
    week_num = current.isocalendar()[1]
    semana_key = f"S{week_num}"
    if semana_key not in semanas:
        semanas.append(semana_key)
    current += timedelta(days=1)

print(f"Semanas: {semanas}")

result = calculator.calcular_pagos_proveedores(
    fecha_inicio='2026-03-01',
    fecha_fin='2026-03-31',
    meses_lista=semanas
)

proveedores = result.get('proveedores', [])
print(f"\nTotal proveedores: {len(proveedores)}")

# Buscar NEWEN
for prov in proveedores:
    nombre = prov.get('nombre', '')
    if 'NEWEN' in nombre.upper() and 'ARAUCANIA' in nombre.upper():
        print("\n" + "="*80)
        print(f"PROVEEDOR: {nombre}")
        print(f"CATEGORIA: {prov.get('categoria')}")
        print("\nMONTOS POR PERIODO:")
        for periodo, monto in prov.get('montos_por_mes', {}).items():
            if monto != 0:
                print(f"  {periodo}: {monto:,.0f}")
        total = sum(prov.get('montos_por_mes', {}).values())
        print(f"\nTOTAL: {total:,.0f}")
        print("="*80)

# Buscar otros montos grandes
print("\n\nPROVEEDORES CON MONTOS > 1B:")
for prov in proveedores:
    total = sum(abs(v) for v in prov.get('montos_por_mes', {}).values())
    if total > 1_000_000_000:
        print(f"  {prov.get('nombre')}: {total:,.0f}")
