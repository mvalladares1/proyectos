"""
DEBUG: Investigar por qué price_unit = 0 en purchase.order.line
Objetivo: Entender el origen del problema y proponer solución

HIPÓTESIS:
1. Las OCs se crearon sin precio (draft/RFQ)
2. El precio está en el producto pero no se copió a la línea
3. El precio está en moneda USD y hay problema de conversión
4. Es producto de consignación sin precio
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

# Configuración
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 140)
print("DEBUG: INVESTIGACIÓN DE PRICE_UNIT = 0 EN ÓRDENES DE COMPRA")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 140)

try:
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("[OK] Conexion a Odoo establecida\n")
except Exception as e:
    print(f"[ERROR] Error al conectar a Odoo: {e}")
    sys.exit(1)

# === 1. BUSCAR LINEAS DE OC CON PRICE_UNIT = 0 Y QTY_RECEIVED > 0 ===
print("[BUSQUEDA] LINEAS DE OC CON PRICE_UNIT = 0 Y CANTIDAD RECIBIDA > 0:")
print("-" * 140)

# Buscar líneas problemáticas
lineas_problema = odoo.search_read(
    'purchase.order.line',
    [
        ['price_unit', '=', 0],
        ['qty_received', '>', 0],
        ['order_id.date_order', '>=', '2025-11-01']
    ],
    ['id', 'order_id', 'product_id', 'name', 'product_qty', 'qty_received', 
     'qty_invoiced', 'price_unit', 'price_subtotal'],
    limit=100
)

print(f"Encontradas {len(lineas_problema)} líneas con price_unit = 0 y qty_received > 0\n")

if lineas_problema:
    # Obtener detalles de las OCs y productos
    order_ids = list(set([l['order_id'][0] for l in lineas_problema if l.get('order_id')]))
    product_ids = list(set([l['product_id'][0] for l in lineas_problema if l.get('product_id')]))
    
    # Leer OCs
    orders = odoo.search_read(
        'purchase.order',
        [['id', 'in', order_ids]],
        ['id', 'name', 'partner_id', 'state', 'date_order', 'currency_id'],
        limit=100
    )
    orders_map = {o['id']: o for o in orders}
    
    # Leer productos con sus precios estándar
    products = odoo.search_read(
        'product.product',
        [['id', 'in', product_ids]],
        ['id', 'name', 'standard_price', 'list_price', 'categ_id'],
        limit=100
    )
    products_map = {p['id']: p for p in products}
    
    print(f"{'OC':<18} {'Estado':<12} {'Proveedor':<30} {'Producto':<35} {'P.Unit OC':>10} {'Std Price':>12} {'Qty Rec':>10}")
    print("-" * 140)
    
    for l in lineas_problema[:30]:
        order_id = l['order_id'][0] if l.get('order_id') else None
        product_id = l['product_id'][0] if l.get('product_id') else None
        
        order = orders_map.get(order_id, {})
        product = products_map.get(product_id, {})
        
        partner = order.get('partner_id')
        partner_name = partner[1][:28] if isinstance(partner, (list, tuple)) else ''
        
        std_price = product.get('standard_price', 0)
        
        print(f"{order.get('name', ''):<18} {order.get('state', ''):<12} {partner_name:<30} "
              f"{product.get('name', '')[:33]:<35} {l.get('price_unit', 0):>10,.0f} "
              f"{std_price:>12,.0f} {l.get('qty_received', 0):>10,.0f}")

# === 2. ANALIZAR PATRÓN DE OCs ===
print("\n\n" + "=" * 140)
print("ANÁLISIS DE PATRÓN: ¿QUÉ TIPO DE OCs TIENEN PRICE_UNIT = 0?")
print("=" * 140)

# Contar por estado de OC
estados = {}
partners = {}
for l in lineas_problema:
    order_id = l['order_id'][0] if l.get('order_id') else None
    order = orders_map.get(order_id, {})
    
    estado = order.get('state', 'unknown')
    estados[estado] = estados.get(estado, 0) + 1
    
    partner = order.get('partner_id')
    partner_name = partner[1] if isinstance(partner, (list, tuple)) else 'unknown'
    partners[partner_name] = partners.get(partner_name, 0) + 1

print("\nPor estado de OC:")
for estado, count in sorted(estados.items(), key=lambda x: -x[1]):
    print(f"   {estado:<20}: {count:>5} líneas")

print("\nPor proveedor (top 10):")
for partner, count in sorted(partners.items(), key=lambda x: -x[1])[:10]:
    print(f"   {partner[:40]:<40}: {count:>5} líneas")

# === 3. COMPARAR CON LÍNEAS NORMALES ===
print("\n\n" + "=" * 140)
print("COMPARACIÓN: LÍNEAS CON PRICE_UNIT > 0 (muestra)")
print("=" * 140)

lineas_ok = odoo.search_read(
    'purchase.order.line',
    [
        ['price_unit', '>', 0],
        ['qty_received', '>', 0],
        ['order_id.date_order', '>=', '2025-11-01']
    ],
    ['id', 'order_id', 'product_id', 'price_unit', 'qty_received'],
    limit=20
)

print(f"\nEncontradas {len(lineas_ok)} líneas con price_unit > 0 (mostrando 20)\n")

if lineas_ok:
    order_ids_ok = list(set([l['order_id'][0] for l in lineas_ok if l.get('order_id')]))
    orders_ok = odoo.search_read(
        'purchase.order',
        [['id', 'in', order_ids_ok]],
        ['id', 'name', 'partner_id', 'state'],
        limit=50
    )
    orders_ok_map = {o['id']: o for o in orders_ok}
    
    print(f"{'OC':<18} {'Estado':<12} {'Proveedor':<40} {'P.Unit':>12}")
    print("-" * 90)
    for l in lineas_ok[:10]:
        order_id = l['order_id'][0] if l.get('order_id') else None
        order = orders_ok_map.get(order_id, {})
        partner = order.get('partner_id')
        partner_name = partner[1][:38] if isinstance(partner, (list, tuple)) else ''
        print(f"{order.get('name', ''):<18} {order.get('state', ''):<12} {partner_name:<40} {l.get('price_unit', 0):>12,.0f}")

# === 4. VERIFICAR SI EL PRODUCTO TIENE PRECIO ===
print("\n\n" + "=" * 140)
print("VERIFICACIÓN: ¿LOS PRODUCTOS PROBLEMÁTICOS TIENEN PRECIO ESTÁNDAR?")
print("=" * 140)

productos_sin_precio = 0
productos_con_precio = 0

for pid, prod in products_map.items():
    std_price = prod.get('standard_price', 0)
    if std_price == 0:
        productos_sin_precio += 1
    else:
        productos_con_precio += 1

print(f"\nDe los {len(products_map)} productos en líneas problemáticas:")
print(f"   Con standard_price > 0:  {productos_con_precio}")
print(f"   Con standard_price = 0:  {productos_sin_precio}")

if productos_con_precio > 0:
    print("\n[!] CONCLUSION: Los productos SI tienen precio estandar,")
    print("   pero el price_unit de la linea OC esta en 0.")
    print("   SOLUCION: Usar standard_price del producto como fallback cuando price_unit = 0")

# === 5. PROPUESTA DE SOLUCIÓN ===
print("\n\n" + "=" * 140)
print("PROPUESTA DE SOLUCIÓN PARA EL SERVICIO")
print("=" * 140)
print("""
1. PROBLEMA IDENTIFICADO:
   - Algunas líneas de OC tienen price_unit = 0
   - Esto hace que el cálculo de recepciones sin facturar sea incorrecto
   - Los productos SÍ tienen standard_price configurado

2. SOLUCIÓN PROPUESTA:
   - Cuando price_unit = 0 en purchase.order.line:
     a) Usar product.product.standard_price como fallback
     b) Si standard_price también es 0, calcular desde price_subtotal / product_qty
     c) Agregar log/warning para estos casos

3. CÓDIGO A MODIFICAR:
   - Archivo: backend/services/compras/service.py
   - Función: get_lineas_credito()
   - Línea: ~481-492 (donde se procesa qty_pendiente * price_unit)

4. ALTERNATIVA MÁS ROBUSTA:
   - Usar price_subtotal directamente de la línea de OC
   - Esto ya incluye el precio unitario correcto
""")

print("\n" + "=" * 140)
print("DEBUG COMPLETADO")
print("=" * 140)
