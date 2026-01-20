"""
Debug: Verificar datos de inventario 2026 enero
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

def main():
    odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")
    
    print("="*120)
    print("DEBUG INVENTARIO ENERO 2026")
    print("="*120)
    
    # COMPRAS
    print("\n" + "="*120)
    print("FACTURAS DE COMPRA (in_invoice)")
    print("="*120)
    
    lineas_compra = odoo.search_read(
        'account.move.line',
        [
            ['move_id.move_type', '=', 'in_invoice'],
            ['move_id.state', '=', 'posted'],
            ['product_id', '!=', False],
            ['date', '>=', '2026-01-01'],
            ['date', '<=', '2026-01-31'],
            ['quantity', '>', 0],
            ['debit', '>', 0],
            ['account_id.code', '=like', '21%']
        ],
        ['product_id', 'quantity', 'price_unit', 'debit', 'date', 'move_id'],
        limit=100
    )
    
    print(f"\nTotal líneas: {len(lineas_compra)}")
    
    # Obtener productos
    prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas_compra if l.get('product_id')]))
    
    productos = odoo.search_read(
        'product.product',
        [['id', 'in', prod_ids]],
        ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
        limit=1000
    )
    
    prod_map = {p['id']: p for p in productos}
    
    print(f"\n{'Fecha':<12} {'Factura':<25} {'Producto':<60} {'Tipo':<15} {'Manejo':<15} {'Cant':>12} {'P.Unit':>12} {'Total':>15}")
    print("-" * 180)
    
    total_compra = 0
    total_kg_compra = 0
    
    for linea in lineas_compra[:20]:
        fecha = linea.get('date', '')
        factura = linea.get('move_id', [0, ''])[1]
        prod_id = linea.get('product_id', [None])[0]
        cantidad = linea.get('quantity', 0)
        precio_unit = linea.get('price_unit', 0)
        subtotal = linea.get('debit', 0)  # Usar debit para compras
        
        if prod_id and prod_id in prod_map:
            prod = prod_map[prod_id]
            nombre = prod.get('name', '')[:60]
            tipo = prod.get('x_studio_sub_categora')
            tipo = tipo[1] if isinstance(tipo, (list, tuple)) and len(tipo) > 1 else str(tipo) if tipo else "Sin tipo"
            
            manejo = prod.get('x_studio_categora_tipo_de_manejo')
            manejo = manejo[1] if isinstance(manejo, (list, tuple)) and len(manejo) > 1 else str(manejo) if manejo else "Sin manejo"
            
            print(f"{fecha:<12} {factura[:25]:<25} {nombre:<60} {tipo[:15]:<15} {manejo[:15]:<15} {cantidad:>12,.2f} {precio_unit:>12,.2f} {subtotal:>15,.2f}")
            
            total_compra += subtotal
            total_kg_compra += cantidad
    
    print("-" * 180)
    print(f"{'TOTALES':<12} {'':<25} {'':<60} {'':<15} {'':<15} {total_kg_compra:>12,.2f} {'':<12} {total_compra:>15,.2f}")
    
    # VENTAS
    print("\n" + "="*120)
    print("FACTURAS DE VENTA (out_invoice)")
    print("="*120)
    
    lineas_venta = odoo.search_read(
        'account.move.line',
        [
            ['move_id.move_type', '=', 'out_invoice'],
            ['move_id.state', '=', 'posted'],
            ['product_id', '!=', False],
            ['date', '>=', '2026-01-01'],
            ['date', '<=', '2026-01-31'],
            ['quantity', '>', 0],
            ['credit', '>', 0],
            ['account_id.code', '=like', '41%']
        ],
        ['product_id', 'quantity', 'price_unit', 'credit', 'date', 'move_id'],
        limit=100
    )
    
    print(f"\nTotal líneas: {len(lineas_venta)}")
    
    prod_ids_venta = list(set([l.get('product_id', [None])[0] for l in lineas_venta if l.get('product_id')]))
    
    productos_venta = odoo.search_read(
        'product.product',
        [['id', 'in', prod_ids_venta]],
        ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
        limit=1000
    )
    
    prod_map_venta = {p['id']: p for p in productos_venta}
    
    print(f"\n{'Fecha':<12} {'Factura':<25} {'Producto':<60} {'Tipo':<15} {'Manejo':<15} {'Cant':>12} {'P.Unit':>12} {'Total':>15}")
    print("-" * 180)
    
    total_venta = 0
    total_kg_venta = 0
    
    for linea in lineas_venta[:20]:
        fecha = linea.get('date', '')
        factura = linea.get('move_id', [0, ''])[1]
        prod_id = linea.get('product_id', [None])[0]
        cantidad = linea.get('quantity', 0)
        precio_unit = linea.get('price_unit', 0)
        subtotal = linea.get('credit', 0)  # Usar credit para ventas
        
        if prod_id and prod_id in prod_map_venta:
            prod = prod_map_venta[prod_id]
            nombre = prod.get('name', '')[:60]
            tipo = prod.get('x_studio_sub_categora')
            tipo = tipo[1] if isinstance(tipo, (list, tuple)) and len(tipo) > 1 else str(tipo) if tipo else "Sin tipo"
            
            manejo = prod.get('x_studio_categora_tipo_de_manejo')
            manejo = manejo[1] if isinstance(manejo, (list, tuple)) and len(manejo) > 1 else str(manejo) if manejo else "Sin manejo"
            
            print(f"{fecha:<12} {factura[:25]:<25} {nombre:<60} {tipo[:15]:<15} {manejo[:15]:<15} {cantidad:>12,.2f} {precio_unit:>12,.2f} {subtotal:>15,.2f}")
            
            total_venta += subtotal
            total_kg_venta += cantidad
    
    print("-" * 180)
    print(f"{'TOTALES':<12} {'':<25} {'':<60} {'':<15} {'':<15} {total_kg_venta:>12,.2f} {'':<12} {total_venta:>15,.2f}")
    
    # RESUMEN
    print("\n" + "="*120)
    print("RESUMEN FINAL")
    print("="*120)
    print(f"\nCOMPRAS:")
    print(f"  Kilogramos: {total_kg_compra:,.2f} kg")
    print(f"  Monto total: ${total_compra:,.2f}")
    print(f"  Precio promedio: ${(total_compra / total_kg_compra) if total_kg_compra > 0 else 0:,.2f} /kg")
    
    print(f"\nVENTAS:")
    print(f"  Kilogramos: {total_kg_venta:,.2f} kg")
    print(f"  Monto total: ${total_venta:,.2f}")
    print(f"  Precio promedio: ${(total_venta / total_kg_venta) if total_kg_venta > 0 else 0:,.2f} /kg")
    
    print(f"\nMERMA:")
    print(f"  Kilogramos: {total_kg_compra - total_kg_venta:,.2f} kg")
    print(f"  Porcentaje: {((total_kg_compra - total_kg_venta) / total_kg_compra * 100) if total_kg_compra > 0 else 0:.1f}%")

if __name__ == "__main__":
    main()
