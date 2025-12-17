"""
Script de debug para investigar por qué no se detectan las recepciones sin facturar.
Ejecutar con: python debug_recepciones.py
"""
import sys
import os
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from shared.odoo_client import OdooClient

# Conectar a Odoo
username = os.getenv('ODOO_USERNAME')
password = os.getenv('ODOO_PASSWORD')

if not username or not password:
    print("ERROR: Configura ODOO_USERNAME y ODOO_PASSWORD en .env")
    sys.exit(1)

odoo = OdooClient(username=username, password=password)

# 1. Buscar el proveedor TALPACK
print("\n=== 1. BUSCAR PROVEEDOR TALPACK ===")
partners = odoo.search_read(
    'res.partner',
    [['name', 'ilike', 'TALPACK'], ['x_studio_linea_credito_activa', '=', True]],
    ['id', 'name', 'x_studio_linea_credito_monto'],
    limit=5
)
print(f"Proveedores encontrados: {len(partners)}")
for p in partners:
    print(f"  - ID: {p['id']}, Nombre: {p['name']}, Línea: {p.get('x_studio_linea_credito_monto')}")

if not partners:
    print("No se encontró TALPACK con línea de crédito activa")
    sys.exit(1)

partner_id = partners[0]['id']

# 2. Buscar OCs de este proveedor
print("\n=== 2. BUSCAR OCs DEL PROVEEDOR ===")
ocs = odoo.search_read(
    'purchase.order',
    [['partner_id', '=', partner_id], ['state', '=', 'purchase']],
    ['id', 'name', 'amount_total', 'date_order', 'invoice_ids'],
    limit=20
)
print(f"OCs encontradas: {len(ocs)}")
for oc in ocs:
    print(f"  - {oc['name']}: ${oc['amount_total']:,.0f} - Facturas: {oc.get('invoice_ids', [])}")

# Buscar específicamente OC07898
print("\n=== 3. BUSCAR OC07898 ===")
oc07898 = odoo.search_read(
    'purchase.order',
    [['name', '=', 'OC07898']],
    ['id', 'name', 'partner_id', 'amount_total', 'picking_ids'],
    limit=1
)
if oc07898:
    oc = oc07898[0]
    print(f"OC07898 encontrada: ID={oc['id']}, Monto=${oc['amount_total']:,.0f}")
    print(f"  Partner: {oc.get('partner_id')}")
    print(f"  Picking IDs: {oc.get('picking_ids', [])}")
    
    # 4. Buscar pickings asociados por origin
    print("\n=== 4. BUSCAR PICKINGS POR ORIGIN ===")
    pickings_by_origin = odoo.search_read(
        'stock.picking',
        [['origin', '=', 'OC07898']],
        ['id', 'name', 'origin', 'state', 'picking_type_id', 'picking_type_code'],
        limit=10
    )
    print(f"Pickings por origin: {len(pickings_by_origin)}")
    for p in pickings_by_origin:
        print(f"  - {p['name']}: state={p['state']}, type={p.get('picking_type_id')}, code={p.get('picking_type_code')}")
    
    # 5. Buscar pickings por picking_ids de la OC
    if oc.get('picking_ids'):
        print("\n=== 5. BUSCAR PICKINGS POR ID ===")
        pickings_by_id = odoo.read('stock.picking', oc['picking_ids'], 
            ['id', 'name', 'origin', 'state', 'picking_type_id', 'picking_type_code'])
        for p in pickings_by_id:
            print(f"  - {p['name']}: state={p['state']}, origin={p.get('origin')}, code={p.get('picking_type_code')}")
            
            # 6. Buscar movimientos de este picking
            print(f"\n=== 6. MOVIMIENTOS DEL PICKING {p['name']} ===")
            moves = odoo.search_read(
                'stock.move',
                [['picking_id', '=', p['id']]],
                ['id', 'product_id', 'product_uom_qty', 'quantity_done', 'price_unit', 'purchase_line_id', 'state'],
                limit=20
            )
            for m in moves:
                producto = m.get('product_id', [None, 'N/A'])
                prod_name = producto[1] if isinstance(producto, (list, tuple)) else producto
                print(f"    - {prod_name[:30]}: qty={m['product_uom_qty']}, done={m['quantity_done']}, price={m.get('price_unit', 0)}, state={m['state']}")
                print(f"      purchase_line_id: {m.get('purchase_line_id')}")

else:
    print("OC07898 no encontrada")

# 7. Verificar líneas de la OC
print("\n=== 7. LÍNEAS DE OC07898 ===")
if oc07898:
    po_lines = odoo.search_read(
        'purchase.order.line',
        [['order_id', '=', oc07898[0]['id']]],
        ['id', 'product_id', 'product_qty', 'qty_received', 'qty_invoiced', 'price_unit'],
        limit=20
    )
    for l in po_lines:
        producto = l.get('product_id', [None, 'N/A'])
        prod_name = producto[1] if isinstance(producto, (list, tuple)) else producto
        print(f"  - {prod_name[:30]}: qty={l['product_qty']}, recv={l['qty_received']}, inv={l['qty_invoiced']}, price={l['price_unit']}")
