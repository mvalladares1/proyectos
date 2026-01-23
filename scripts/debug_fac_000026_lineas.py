import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(username=USERNAME, password=PASSWORD)

# ID de la factura de venta FAC 000026
factura_id = 41909

print("=" * 80)
print("ANÁLISIS COMPLETO - FAC 000026 (Factura de Venta)")
print("=" * 80)

# Obtener TODAS las líneas (sin filtro de producto)
lineas = odoo.search_read(
    'account.move.line',
    [['move_id', '=', factura_id]],
    ['id', 'product_id', 'name', 'quantity', 'credit', 'debit', 'display_type', 'account_id'],
    limit=1000
)

print(f"\nTotal líneas en la factura: {len(lineas)}")

for i, linea in enumerate(lineas, 1):
    prod_id = linea.get('product_id')
    prod_name = prod_id[1] if prod_id else "❌ SIN PRODUCTO"
    account = linea.get('account_id', [None, 'N/A'])[1]
    
    print(f"\n{'=' * 80}")
    print(f"LÍNEA {i}")
    print(f"{'=' * 80}")
    print(f"   ID: {linea['id']}")
    print(f"   Producto: {prod_name}")
    print(f"   product_id: {prod_id}")
    print(f"   Descripción: {linea.get('name', 'N/A')}")
    print(f"   display_type: {linea.get('display_type')}")
    print(f"   Cuenta: {account}")
    print(f"   Cantidad: {linea.get('quantity', 0)}")
    print(f"   Credit: ${linea.get('credit', 0):,.0f}")
    print(f"   Debit: ${linea.get('debit', 0):,.0f}")

print("\n" + "=" * 80)
print("CONCLUSIÓN:")
print("=" * 80)

lineas_con_producto = [l for l in lineas if l.get('product_id')]
lineas_sin_producto = [l for l in lineas if not l.get('product_id')]

print(f"Líneas CON producto: {len(lineas_con_producto)}")
print(f"Líneas SIN producto: {len(lineas_sin_producto)}")

if len(lineas_con_producto) == 0:
    print("\n⚠️  ESTA FACTURA NO TIENE PRODUCTOS ASOCIADOS")
    print("   Por eso NO aparece en el Excel de Stock Teórico")
    print("   Posibles razones:")
    print("   - Factura de servicios")
    print("   - Factura manual sin productos")
    print("   - Error en la captura de datos")
