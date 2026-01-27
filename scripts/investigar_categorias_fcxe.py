"""
Investigar categoría de productos en FCXE 000002 y 000007
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*100)
print("INVESTIGACIÓN: CATEGORÍAS DE PRODUCTOS EN FCXE 000002 Y 000007")
print("="*100)

facturas = ['FCXE 000002', 'FCXE 000007']

for factura_nombre in facturas:
    print(f"\n📋 {factura_nombre}")
    
    # Buscar líneas
    lineas = odoo.search_read(
        'account.move.line',
        [
            ['move_id.name', '=', factura_nombre],
            ['display_type', '=', 'product']
        ],
        ['id', 'product_id', 'name', 'quantity'],
        limit=10
    )
    
    for linea in lineas:
        producto_info = linea.get('product_id')
        if isinstance(producto_info, (list, tuple)) and len(producto_info) > 0:
            producto_id = producto_info[0]
        elif isinstance(producto_info, bool) and not producto_info:
            producto_id = None
        else:
            producto_id = producto_info
            
        descripcion = linea.get('name', 'N/A')
        cantidad = linea.get('quantity', 0)
        
        if producto_id:
            # Obtener product.product
            producto = odoo.search_read(
                'product.product',
                [['id', '=', producto_id]],
                ['id', 'name', 'default_code', 'categ_id', 'product_tmpl_id', 'type'],
                limit=1
            )
            
            if producto:
                prod = producto[0]
                categoria_id = prod.get('categ_id', [None])[0]
                categoria_nombre = prod.get('categ_id', [None, 'N/A'])[1]
                tipo = prod.get('type', 'N/A')
                
                # Obtener categoría completa
                if categoria_id:
                    categoria = odoo.search_read(
                        'product.category',
                        [['id', '=', categoria_id]],
                        ['id', 'name', 'complete_name'],
                        limit=1
                    )
                    
                    if categoria:
                        cat = categoria[0]
                        complete_name = cat.get('complete_name', 'N/A')
                        
                        print(f"\n   Producto: {prod.get('name', 'N/A')}")
                        print(f"   Código: {prod.get('default_code', 'N/A')}")
                        print(f"   Cantidad: {cantidad:,.2f} kg")
                        print(f"   Tipo: {tipo}")
                        print(f"   Categoría: {complete_name}")
                        print(f"   ¿Incluye 'PRODUCTOS'?: {'✅ SÍ' if 'PRODUCTOS' in complete_name.upper() else '❌ NO'}")
        else:
            print(f"\n   ⚠️ Texto libre (sin producto): {descripcion[:80]}")
            print(f"   Cantidad: {cantidad:,.2f} kg")
            print(f"   ¿Se incluye?: ✅ SÍ (texto libre permitido)")

print("\n" + "="*100)
print("✅ INVESTIGACIÓN COMPLETADA")
print("="*100)
