#!/usr/bin/env python3
"""Debug: Simular lógica de RealProyectadoService para NEWEN"""
import sys
sys.path.insert(0, '/app')

from backend.services.flujo_caja.real_proyectado import RealProyectadoService

username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

print("Iniciando servicio...")
service = RealProyectadoService(username=username, password=password)

print("Llamando get_proveedores_proyectado...")
result = service.get_proveedores_proyectado(
    fecha_inicio='2026-03-01',
    fecha_fin='2026-03-31',
    granularidad='semanal'
)

print(f"\nTotal proveedores: {len(result.get('proveedores', []))}")
print(f"Periodos: {result.get('periodos', [])}")

# Buscar NEWEN
for prov in result.get('proveedores', []):
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
for prov in result.get('proveedores', []):
    total = sum(abs(v) for v in prov.get('montos_por_mes', {}).values())
    if total > 1_000_000_000:
        print(f"  {prov.get('nombre')}: {total:,.0f}")
