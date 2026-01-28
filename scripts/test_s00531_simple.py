#!/usr/bin/env python3
"""Test trazabilidad de venta S00531 - versión simple"""
import sys
sys.path.insert(0, '/home/feli/proyectos')

# Importar solo lo necesario
import os
os.environ.setdefault('ODOO_USERNAME', 'frios@riofuturo.cl')
os.environ.setdefault('ODOO_API_KEY', '413c17f8c0a0ebe211cda26c094c2bbb47fce5c6')

# Importar directamente el archivo
import importlib.util
spec = importlib.util.spec_from_file_location(
    "traceability_service", 
    "/home/feli/proyectos/backend/services/traceability/traceability_service.py"
)
traz_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(traz_module)

TraceabilityService = traz_module.TraceabilityService

username = os.getenv('ODOO_USERNAME')
password = os.getenv('ODOO_API_KEY')

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

# Análisis detallado
pallets = result.get("pallets", {})
processes = result.get("processes", {})

print(f'\n{"="*80}')
print('ANÁLISIS:')
print(f'{"="*80}')

# Contar procesos por tipo
process_types = {}
for proc_id, proc_data in processes.items():
    origin = proc_data.get('origin', 'Sin origin')
    if '/MO/' in origin:
        ptype = 'MO (Manufacturing Order)'
    elif '/MOVPSP/' in origin:
        ptype = 'MOVPSP (Movimiento PSP)'
    elif '/IN/' in origin or '/RFP/' in origin:
        ptype = 'RECEPCION'
    else:
        ptype = 'OTRO'
    
    if ptype not in process_types:
        process_types[ptype] = 0
    process_types[ptype] += 1

print('\nProcesos por tipo:')
for ptype, count in sorted(process_types.items()):
    print(f'  {ptype}: {count}')
