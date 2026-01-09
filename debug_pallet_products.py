"""
Debug script to check what product_id the validation returns for each pallet.
This will reveal why wrong products are being grouped.
"""

import sys
import os
sys.path.insert(0, '/app')
from shared.odoo_client import OdooClient

# Config
USUARIO = os.getenv("ODOO_USER", "mvalladares@riofuturo.cl")
API_KEY = os.getenv("ODOO_API_KEY", "c0766224bec30cac071ffe43a858c9ccbd521ddd")

print(f"=== DEBUG: Checking Product IDs for Each Pallet ===")
print(f"Connecting with {USUARIO}")

try:
    odoo = OdooClient(username=USUARIO, password=API_KEY)
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)

# Pallets from user input
PALLETS = [
    {"codigo": "PACK0015749", "expected_code": "101222000"},
    {"codigo": "PACK0016141", "expected_code": "101124000"},
    {"codigo": "PACK0015717", "expected_code": "101222000"},
    {"codigo": "PACK0015693", "expected_code": "101122000"},
    {"codigo": "PACK0017237", "expected_code": "104221000"},
    {"codigo": "PACK0017231", "expected_code": "104221000"},
]

print("\n=== CHECKING EACH PALLET ===")

for pallet in PALLETS:
    codigo = pallet['codigo']
    expected = pallet['expected_code']
    print(f"\n--- {codigo} (expected: {expected}) ---")
    
    # 1. Find package
    pkg = odoo.search_read(
        'stock.quant.package',
        [('name', '=', codigo)],
        ['id'],
        limit=1
    )
    
    if not pkg:
        print(f"  Package not found!")
        continue
    
    pkg_id = pkg[0]['id']
    print(f"  Package ID: {pkg_id}")
    
    # 2. Check stock.quant for this package
    quants = odoo.search_read(
        'stock.quant',
        [('package_id', '=', pkg_id)],
        ['product_id', 'lot_id', 'quantity', 'location_id'],
        limit=5
    )
    
    if quants:
        print(f"  Quants found: {len(quants)}")
        for q in quants:
            prod_id = q['product_id'][0] if q['product_id'] else 0
            prod_name = q['product_id'][1] if q['product_id'] else 'N/A'
            
            # Get default_code
            prod = odoo.search_read(
                'product.product',
                [('id', '=', prod_id)],
                ['default_code'],
                limit=1
            )
            code = prod[0]['default_code'] if prod else 'N/A'
            
            loc = q['location_id'][1] if q['location_id'] else 'N/A'
            
            print(f"    Quant: [{code}] {prod_name} - Qty: {q['quantity']} @ {loc}")
            
            if code != expected:
                print(f"    ⚠️ MISMATCH! Expected {expected}, got {code}")
    else:
        print(f"  No quants found for package!")
        
        # 3. Try move.line as fallback
        print(f"  Checking stock.move.line...")
        lines = odoo.search_read(
            'stock.move.line',
            ['|', ('package_id', '=', pkg_id), ('result_package_id', '=', pkg_id)],
            ['product_id', 'lot_id', 'qty_done', 'state'],
            limit=5
        )
        
        if lines:
            print(f"  Move lines found: {len(lines)}")
            for l in lines:
                prod_id = l['product_id'][0] if l['product_id'] else 0
                prod_name = l['product_id'][1] if l['product_id'] else 'N/A'
                
                prod = odoo.search_read(
                    'product.product',
                    [('id', '=', prod_id)],
                    ['default_code'],
                    limit=1
                )
                code = prod[0]['default_code'] if prod else 'N/A'
                
                lot = l['lot_id'][1] if l['lot_id'] else 'N/A'
                
                print(f"    Line: [{code}] {prod_name} - lot={lot}, qty={l['qty_done']}, state={l['state']}")
                
                if code != expected:
                    print(f"    ⚠️ MISMATCH! Expected {expected}, got {code}")
        else:
            print(f"  No move lines found either!")

print("\n=== END DEBUG ===")
