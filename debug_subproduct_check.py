"""
Debug script to check MO subproducts and test transformation logic.
Checks MO RF/MO/CongTE1/00147 and verifies 101XXXXXX → 201XXXXXX transformation.
"""

import sys
import os
sys.path.insert(0, '/app')
from shared.odoo_client import OdooClient

# Config
USUARIO = os.getenv("ODOO_USER", "mvalladares@riofuturo.cl")
API_KEY = os.getenv("ODOO_API_KEY", "c0766224bec30cac071ffe43a858c9ccbd521ddd")

print(f"=== DEBUG: Checking MO Subproducts and Transformation ===")
print(f"Connecting with {USUARIO}")

try:
    odoo = OdooClient(username=USUARIO, password=API_KEY)
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)

# MO to check
MO_NAME = "RF/MO/CongTE1/00147"

# Pallets from user input
PALLETS = [
    {"codigo": "PACK0015749", "producto_code": "101222000", "kg": 412.38},
    {"codigo": "PACK0016141", "producto_code": "101124000", "kg": 523.25},
    {"codigo": "PACK0015717", "producto_code": "101222000", "kg": 731.70},
    {"codigo": "PACK0015693", "producto_code": "101122000", "kg": 485.05},
    {"codigo": "PACK0017237", "producto_code": "104221000", "kg": 732.70},
    {"codigo": "PACK0017231", "producto_code": "104221000", "kg": 580.20},
]

print(f"\n=== 1. TESTING TRANSFORMATION LOGIC ===")
print("Logic: First digit 1 → 2")

unique_products = list(set(p['producto_code'] for p in PALLETS))
print(f"\nUnique product codes from pallets: {unique_products}")

for code in unique_products:
    expected_output = '2' + code[1:] if code.startswith('1') else code
    print(f"\n{code} → {expected_output}")
    
    # Check if output product exists in Odoo
    prod = odoo.search_read(
        'product.product',
        [('default_code', '=', expected_output)],
        ['id', 'name', 'default_code'],
        limit=1
    )
    
    if prod:
        print(f"  ✅ FOUND: ID={prod[0]['id']}, Name={prod[0]['name']}")
    else:
        print(f"  ❌ NOT FOUND! Product with code {expected_output} does not exist")
        # Check variations
        variations = odoo.search_read(
            'product.product',
            [('default_code', 'ilike', expected_output[:6])],
            ['id', 'name', 'default_code'],
            limit=5
        )
        if variations:
            print(f"  Similar products found:")
            for v in variations:
                print(f"    - {v['default_code']}: {v['name']}")

print(f"\n=== 2. CHECKING MO {MO_NAME} ===")

# Find MO
mo = odoo.search_read(
    'mrp.production',
    [('name', '=', MO_NAME)],
    ['id', 'name', 'state', 'move_raw_ids', 'move_finished_ids', 'product_qty'],
    limit=1
)

if not mo:
    print(f"MO {MO_NAME} not found!")
    sys.exit(1)

mo = mo[0]
print(f"MO ID: {mo['id']}")
print(f"State: {mo['state']}")
print(f"Qty: {mo['product_qty']}")
print(f"Components (move_raw_ids): {len(mo['move_raw_ids'])} moves")
print(f"Subproducts (move_finished_ids): {len(mo['move_finished_ids'])} moves")

print(f"\n=== 3. CHECKING SUBPRODUCTS (move_finished_ids) ===")

if mo['move_finished_ids']:
    moves = odoo.read('stock.move', mo['move_finished_ids'], [
        'product_id', 'product_uom_qty', 'state', 'move_line_ids'
    ])
    
    print(f"\nSubproduct moves found: {len(moves)}")
    
    for move in moves:
        product_name = move['product_id'][1] if move['product_id'] else 'N/A'
        product_id = move['product_id'][0] if move['product_id'] else 0
        
        # Get default_code
        prod_detail = odoo.search_read(
            'product.product',
            [('id', '=', product_id)],
            ['default_code'],
            limit=1
        )
        code = prod_detail[0]['default_code'] if prod_detail else 'N/A'
        
        print(f"\n  Move ID: {move['id']}")
        print(f"    Product: [{code}] {product_name}")
        print(f"    Qty: {move['product_uom_qty']}")
        print(f"    State: {move['state']}")
        print(f"    Move Lines: {len(move.get('move_line_ids', []))}")
        
        # Check move lines
        if move.get('move_line_ids'):
            lines = odoo.read('stock.move.line', move['move_line_ids'], [
                'product_id', 'lot_id', 'result_package_id', 'qty_done', 'reference'
            ])
            for line in lines:
                lot_name = line['lot_id'][1] if line['lot_id'] else 'N/A'
                pkg_name = line['result_package_id'][1] if line['result_package_id'] else 'N/A'
                print(f"      Line: lot={lot_name}, pkg={pkg_name}, qty_done={line['qty_done']}")
else:
    print("NO SUBPRODUCT MOVES FOUND!")

print(f"\n=== 4. EXPECTED vs ACTUAL ===")

# Expected subproduct codes
expected_subproducts = set()
for p in PALLETS:
    code = p['producto_code']
    expected = '2' + code[1:] if code.startswith('1') else code
    expected_subproducts.add(expected)

print(f"Expected subproduct codes: {sorted(expected_subproducts)}")

# Actual subproduct codes from MO
actual_subproducts = set()
if mo['move_finished_ids']:
    for move in moves:
        if move['product_id']:
            prod_detail = odoo.search_read(
                'product.product',
                [('id', '=', move['product_id'][0])],
                ['default_code'],
                limit=1
            )
            if prod_detail and prod_detail[0].get('default_code'):
                actual_subproducts.add(prod_detail[0]['default_code'])

print(f"Actual subproduct codes in MO: {sorted(actual_subproducts)}")

missing = expected_subproducts - actual_subproducts
extra = actual_subproducts - expected_subproducts

if missing:
    print(f"\n❌ MISSING: {sorted(missing)}")
else:
    print(f"\n✅ All expected subproducts present!")

if extra:
    print(f"Extra (unexpected): {sorted(extra)}")

print("\n=== END DEBUG ===")
