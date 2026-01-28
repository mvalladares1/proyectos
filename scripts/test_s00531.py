#!/usr/bin/env python3
"""Test trazabilidad de venta S00531"""
import sys
sys.path.insert(0, '/home/feli/proyectos')

from backend.services.traceability.traceability_service import TraceabilityService
import os

username = os.getenv('ODOO_USERNAME', 'frios@riofuturo.cl')
password = os.getenv('ODOO_API_KEY', '413c17f8c0a0ebe211cda26c094c2bbb47fce5c6')

service = TraceabilityService(username=username, password=password)

print("Trazando venta S00531...")
result = service.get_traceability_by_identifier('S00531', include_siblings=False)

# Debug: mostrar pallets iniciales
sale_pallet_pickings = result.get('sale_pallet_pickings', {})
initial_pallets = [pkg_id for pkg_id, picking_id in sale_pallet_pickings.items()]
print(f'\nPallets iniciales de S00531: {len(initial_pallets)}')
if len(initial_pallets) <= 10:
    print(f'  IDs: {initial_pallets}')

print(f'\n{"="*80}')
print(f'RESULTADO:')
print(f'{"="*80}')
print(f'Pallets: {len(result.get("pallets", {}))}')
print(f'Procesos: {len(result.get("processes", {}))}')
print(f'Proveedores: {len(result.get("suppliers", {}))}')
print(f'Clientes: {len(result.get("customers", {}))}')
print(f'Links: {len(result.get("links", []))}')

# Mostrar clientes
customers = result.get('customers', {})
print(f'\nClientes encontrados:')
for cid, cinfo in customers.items():
    print(f'  {cid}: {cinfo.get("name", "")} - Origin: {cinfo.get("origin", "")}')

# Mostrar procesos
processes = result.get('processes', {})
print(f'\nProcesos encontrados:')
for i, (ref, pinfo) in enumerate(processes.items()):
    if i < 10:
        print(f'  {ref}: {pinfo.get("type", "")}')
