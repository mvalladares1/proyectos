
import sys
import os
# Add /app to path to allow imports from project structure
sys.path.insert(0, '/app')
from shared.odoo_client import OdooClient

# Config
USUARIO = os.getenv("ODOO_USER", "mvalladares@riofuturo.cl")
API_KEY = os.getenv("ODOO_API_KEY", "c0766224bec30cac071ffe43a858c9ccbd521ddd")

print(f"Connecting with {USUARIO}")
try:
    odoo = OdooClient(username=USUARIO, password=API_KEY)
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)

pallet = 'PACK0016141'
print(f"Checking {pallet}")

# 1. Package ID
pkgs = odoo.search_read('stock.quant.package', [('name', '=', pallet)], ['id'])
if not pkgs:
    print("Package not found")
    sys.exit()

pkg_id = pkgs[0]['id']
print(f"Pkg ID: {pkg_id}")

# 2. Check ALL move lines for this package
lines = odoo.search_read('stock.move.line', [('package_id', '=', pkg_id)], ['move_id', 'production_id', 'state', 'reference'])

print(f"Found {len(lines)} move lines")

active_mo_found = False

for l in lines:
    print(f"\nLine {l['id']}:")
    print(f"  State: {l['state']}")
    print(f"  Reference: {l['reference']}")
    print(f"  Production ID (on line): {l.get('production_id')}")
    
    mo_id = None
    
    # Check directly on line
    if l.get('production_id'):
        mo_id = l['production_id'][0]
        print(f"  -> Found MO via 'production_id' field: {l['production_id'][1]}")
    
    # Check via move_id
    elif l.get('move_id'):
        move = odoo.search_read('stock.move', [('id', '=', l['move_id'][0])], ['raw_material_production_id', 'production_id', 'state'])
        if move:
            m = move[0]
            print(f"  -> Move Raw Material MO: {m.get('raw_material_production_id')}")
            print(f"  -> Move Production MO: {m.get('production_id')}")
            
            if m.get('raw_material_production_id'):
                mo_id = m['raw_material_production_id'][0]
            elif m.get('production_id'):
                mo_id = m['production_id'][0]

    # If we found an MO, check its state
    if mo_id:
        mo = odoo.search_read('mrp.production', [('id', '=', mo_id)], ['state', 'name'])
        if mo:
            state = mo[0]['state']
            name = mo[0]['name']
            print(f"  -> MO {name} State: {state}")
            if state not in ['done', 'cancel']:
                print("  !!! PALLET IS IN ACTIVE MO !!!")
                active_mo_found = True

if active_mo_found:
    print("\nCONCLUSION: Pallet IS in active MO")
else:
    print("\nCONCLUSION: Pallet NOT detected in active MO")
