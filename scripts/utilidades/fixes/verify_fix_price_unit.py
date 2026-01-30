"""
DEBUG: Verificar fix de price_unit = 0 usando price_subtotal como fallback
Este script simula la lógica corregida del servicio
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

# Configuracion
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"
FECHA_DESDE = "2025-11-20"

print("=" * 140)
print("VERIFICACION: FIX DE PRICE_UNIT = 0 CON FALLBACK A PRICE_SUBTOTAL")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 140)

try:
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("[OK] Conexion a Odoo establecida\n")
except Exception as e:
    print(f"[ERROR] Error al conectar a Odoo: {e}")
    sys.exit(1)

# Obtener proveedores con linea de credito
partners = odoo.search_read(
    'res.partner',
    [['x_studio_linea_credito_activa', '=', True]],
    ['id', 'name', 'x_studio_linea_credito_monto'],
    limit=10
)

for p in partners[:3]:
    pid = p['id']
    pname = p['name']
    linea_monto = float(p.get('x_studio_linea_credito_monto') or 0)
    
    print(f"\n{'='*100}")
    print(f"PROVEEDOR: {pname} (ID: {pid})")
    print(f"Linea de Credito: ${linea_monto:,.0f}")
    print("="*100)
    
    # Obtener OCs
    ocs = odoo.search_read(
        'purchase.order',
        [
            ['partner_id', '=', pid],
            ['state', 'not in', ['cancel']],
            ['date_order', '>=', FECHA_DESDE]
        ],
        ['id', 'name'],
        limit=50
    )
    oc_ids = [oc['id'] for oc in ocs]
    
    if not oc_ids:
        print("Sin OCs para analizar")
        continue
    
    # Obtener lineas de PO con price_subtotal (el fix)
    po_lines = odoo.search_read(
        'purchase.order.line',
        [['order_id', 'in', oc_ids]],
        ['id', 'order_id', 'product_id', 'name', 'product_qty', 'qty_received', 'qty_invoiced', 'price_unit', 'price_subtotal'],
        limit=500
    )
    
    total_original = 0
    total_corregido = 0
    lineas_corregidas = 0
    
    print(f"\n{'OC':<16} {'Producto':<35} {'Qty Pend':>10} {'P.Unit Orig':>12} {'P.Unit Fix':>12} {'Monto Orig':>14} {'Monto Fix':>14}")
    print("-" * 120)
    
    for line in po_lines:
        qty_received = float(line.get('qty_received') or 0)
        qty_invoiced = float(line.get('qty_invoiced') or 0)
        price_unit_original = float(line.get('price_unit') or 0)
        product_qty = float(line.get('product_qty') or 0)
        price_subtotal = float(line.get('price_subtotal') or 0)
        
        # Logica del fix: Si price_unit = 0 pero hay price_subtotal, calcular
        price_unit_fixed = price_unit_original
        if price_unit_original == 0 and price_subtotal > 0 and product_qty > 0:
            price_unit_fixed = price_subtotal / product_qty
        
        qty_pendiente = qty_received - qty_invoiced
        if qty_pendiente <= 0:
            continue
        
        monto_original = qty_pendiente * price_unit_original
        monto_corregido = qty_pendiente * price_unit_fixed
        
        total_original += monto_original
        total_corregido += monto_corregido
        
        order = line.get('order_id')
        order_name = order[1] if isinstance(order, (list, tuple)) else str(order)
        product = line.get('product_id')
        product_name = product[1][:33] if isinstance(product, (list, tuple)) else ''
        
        # Marcar lineas que cambiaron
        marker = " *FIX*" if price_unit_fixed != price_unit_original else ""
        if price_unit_fixed != price_unit_original:
            lineas_corregidas += 1
        
        print(f"{order_name:<16} {product_name:<35} {qty_pendiente:>10,.0f} "
              f"{price_unit_original:>12,.0f} {price_unit_fixed:>12,.0f} "
              f"${monto_original:>13,.0f} ${monto_corregido:>13,.0f}{marker}")
    
    print("-" * 120)
    print(f"{'TOTALES:':<64} {'':>10} {'':>12} {'':>12} ${total_original:>13,.0f} ${total_corregido:>13,.0f}")
    
    diferencia = total_corregido - total_original
    if diferencia > 0:
        print(f"\n[FIX APLICADO] {lineas_corregidas} lineas corregidas")
        print(f"   Diferencia: +${diferencia:,.0f}")
        print(f"   Esto representa valor que ANTES no se contabilizaba!")

print("\n" + "=" * 140)
print("VERIFICACION COMPLETADA")
print("=" * 140)
