"""
Debug: Explorar facturas de clientes y proveedores para trazabilidad
- Buscar categorías de productos
- Ver tipos de fruta
- Categorías de manejo (orgánico, convencional, etc.)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

def main():
    odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")
    
    print("="*100)
    print("EXPLORACIÓN DE FACTURAS PARA TRAZABILIDAD")
    print("="*100)
    
    # 1. Buscar facturas de proveedor (compras) de 2025
    print("\n" + "="*100)
    print("1. FACTURAS DE PROVEEDOR (COMPRAS)")
    print("="*100)
    
    facturas_compra = odoo.search_read(
        'account.move',
        [
            ['move_type', '=', 'in_invoice'],  # Facturas de proveedor
            ['state', '=', 'posted'],
            ['date', '>=', '2025-01-01'],
            ['date', '<=', '2025-12-31']
        ],
        ['name', 'partner_id', 'date', 'invoice_date', 'amount_total'],
        limit=5
    )
    
    print(f"\nTotal facturas compra 2025: {len(facturas_compra)}")
    if facturas_compra:
        print("\nEjemplo de factura:")
        fc = facturas_compra[0]
        print(f"  Nombre: {fc.get('name')}")
        print(f"  Proveedor: {fc.get('partner_id')}")
        print(f"  Fecha: {fc.get('date')}")
        print(f"  Monto: {fc.get('amount_total')}")
        
        # Obtener líneas de la factura
        move_id = fc.get('id')
        lineas = odoo.search_read(
            'account.move.line',
            [
                ['move_id', '=', move_id],
                ['product_id', '!=', False]
            ],
            ['product_id', 'name', 'quantity', 'price_unit', 'price_subtotal'],
            limit=10
        )
        
        print(f"\n  Líneas de productos ({len(lineas)}):")
        for linea in lineas[:3]:
            print(f"    - Producto: {linea.get('product_id')}")
            print(f"      Cantidad: {linea.get('quantity')}")
            print(f"      Precio: {linea.get('price_unit')}")
            print(f"      Descripción: {linea.get('name', '')[:60]}")
    
    # 2. Buscar facturas de cliente (ventas)
    print("\n" + "="*100)
    print("2. FACTURAS DE CLIENTE (VENTAS)")
    print("="*100)
    
    facturas_venta = odoo.search_read(
        'account.move',
        [
            ['move_type', '=', 'out_invoice'],  # Facturas de cliente
            ['state', '=', 'posted'],
            ['date', '>=', '2025-01-01'],
            ['date', '<=', '2025-12-31']
        ],
        ['name', 'partner_id', 'date', 'invoice_date', 'amount_total'],
        limit=5
    )
    
    print(f"\nTotal facturas venta 2025: {len(facturas_venta)}")
    if facturas_venta:
        print("\nEjemplo de factura:")
        fc = facturas_venta[0]
        print(f"  Nombre: {fc.get('name')}")
        print(f"  Cliente: {fc.get('partner_id')}")
        print(f"  Fecha: {fc.get('date')}")
        print(f"  Monto: {fc.get('amount_total')}")
        
        # Obtener líneas
        move_id = fc.get('id')
        lineas = odoo.search_read(
            'account.move.line',
            [
                ['move_id', '=', move_id],
                ['product_id', '!=', False]
            ],
            ['product_id', 'name', 'quantity', 'price_unit', 'price_subtotal'],
            limit=10
        )
        
        print(f"\n  Líneas de productos ({len(lineas)}):")
        for linea in lineas[:3]:
            print(f"    - Producto: {linea.get('product_id')}")
            print(f"      Cantidad: {linea.get('quantity')}")
            print(f"      Precio: {linea.get('price_unit')}")
    
    # 3. Explorar estructura de productos
    print("\n" + "="*100)
    print("3. ESTRUCTURA DE PRODUCTOS")
    print("="*100)
    
    # Buscar algunos productos
    productos = odoo.search_read(
        'product.product',
        [],
        ['name', 'default_code', 'categ_id', 'type', 'uom_id'],
        limit=10
    )
    
    print(f"\nEjemplos de productos ({len(productos)}):")
    for prod in productos[:5]:
        print(f"\n  ID: {prod.get('id')}")
        print(f"  Nombre: {prod.get('name')}")
        print(f"  Código: {prod.get('default_code')}")
        print(f"  Categoría: {prod.get('categ_id')}")
        print(f"  Tipo: {prod.get('type')}")
        print(f"  UM: {prod.get('uom_id')}")
    
    # 4. Explorar categorías de productos
    print("\n" + "="*100)
    print("4. CATEGORÍAS DE PRODUCTOS")
    print("="*100)
    
    categorias = odoo.search_read(
        'product.category',
        [],
        ['name', 'parent_id', 'complete_name'],
        limit=30
    )
    
    print(f"\nCategorías encontradas ({len(categorias)}):")
    for cat in categorias:
        print(f"  - {cat.get('complete_name', cat.get('name'))}")
    
    # 5. Buscar campos personalizados en productos (manejo, tipo fruta)
    print("\n" + "="*100)
    print("5. CAMPOS PERSONALIZADOS EN PRODUCTOS")
    print("="*100)
    
    # Buscar un producto con más campos
    if productos:
        prod_id = productos[0]['id']
        print(f"\nBuscando todos los campos del producto ID {prod_id}...")
        
        # Leer con todos los campos posibles relacionados a categorías/clasificación
        producto_full = odoo.search_read(
            'product.product',
            [['id', '=', prod_id]],
            [],  # Vacío = todos los campos
            limit=1
        )
        
        if producto_full:
            campos_interesantes = {}
            for key, value in producto_full[0].items():
                # Filtrar campos que podrían ser útiles
                if any(keyword in key.lower() for keyword in ['categ', 'type', 'manejo', 'fruta', 'organic', 'variedad', 'clasificacion', 'x_']):
                    campos_interesantes[key] = value
            
            print("\nCampos potencialmente útiles:")
            for key, value in sorted(campos_interesantes.items()):
                print(f"  {key}: {value}")
    
    # 6. Analizar una factura completa con productos
    print("\n" + "="*100)
    print("6. ANÁLISIS DE LÍNEAS DE FACTURA CON PRODUCTOS")
    print("="*100)
    
    # Buscar líneas de factura con productos en 2025
    lineas_factura = odoo.search_read(
        'account.move.line',
        [
            ['move_id.move_type', 'in', ['in_invoice', 'out_invoice']],
            ['move_id.state', '=', 'posted'],
            ['product_id', '!=', False],
            ['date', '>=', '2025-01-01'],
            ['date', '<=', '2025-12-31']
        ],
        ['move_id', 'product_id', 'quantity', 'price_unit', 'product_uom_id', 'date'],
        limit=20
    )
    
    print(f"\nLíneas de factura con productos en 2025: {len(lineas_factura)}")
    
    # Agrupar por producto
    productos_agrupados = {}
    for linea in lineas_factura:
        prod_id = linea.get('product_id', [None])[0]
        if prod_id:
            if prod_id not in productos_agrupados:
                productos_agrupados[prod_id] = {
                    'nombre': linea.get('product_id', [None, 'Sin nombre'])[1],
                    'cantidad_total': 0,
                    'num_facturas': 0
                }
            productos_agrupados[prod_id]['cantidad_total'] += linea.get('quantity', 0)
            productos_agrupados[prod_id]['num_facturas'] += 1
    
    print(f"\nResumen por producto (top 10):")
    for i, (prod_id, data) in enumerate(sorted(productos_agrupados.items(), key=lambda x: abs(x[1]['cantidad_total']), reverse=True)[:10]):
        print(f"\n  {i+1}. {data['nombre']}")
        print(f"     Cantidad total: {data['cantidad_total']:,.2f}")
        print(f"     Num. facturas: {data['num_facturas']}")

if __name__ == "__main__":
    main()
