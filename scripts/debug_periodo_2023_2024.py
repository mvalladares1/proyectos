"""
Debug específico: 2023-11-01 a 2024-05-31
Comparar compras vs ventas
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.odoo_client import OdooClient

def debug_periodo():
    username = input("Usuario Odoo: ")
    password = input("API Key: ")
    
    odoo = OdooClient(username=username, password=password)
    
    fecha_desde = "2023-11-01"
    fecha_hasta = "2024-05-31"
    
    print("\n" + "="*80)
    print(f"DEBUG PERÍODO: {fecha_desde} → {fecha_hasta}")
    print("="*80)
    
    # ========== COMPRAS ==========
    print("\n🛒 COMPRAS (account.move.line - in_invoice)")
    print("-" * 80)
    
    lineas_compra = odoo.search_read(
        'account.move.line',
        [
            ['move_id.move_type', '=', 'in_invoice'],
            ['move_id.state', '=', 'posted'],
            ['product_id', '!=', False],
            ['date', '>=', fecha_desde],
            ['date', '<=', fecha_hasta],
            ['quantity', '>', 0],
            ['debit', '>', 0]
        ],
        ['product_id', 'quantity', 'debit'],
        limit=100000
    )
    
    print(f"Líneas de compra: {len(lineas_compra)}")
    total_kg_compra = sum(l.get('quantity', 0) for l in lineas_compra)
    total_monto_compra = sum(l.get('debit', 0) for l in lineas_compra)
    print(f"Total kg: {total_kg_compra:,.2f}")
    print(f"Total monto: ${total_monto_compra:,.0f}")
    
    # Productos en compras
    prod_ids_compra = list(set([l.get('product_id', [None])[0] for l in lineas_compra if l.get('product_id')]))
    print(f"Productos únicos: {len(prod_ids_compra)}")
    
    # Obtener info de productos
    productos_compra = odoo.search_read(
        'product.product',
        [['id', 'in', prod_ids_compra]],
        ['id', 'product_tmpl_id', 'categ_id'],
        limit=100000
    )
    
    # Templates
    template_ids_compra = set()
    product_to_template_compra = {}
    
    for prod in productos_compra:
        prod_id = prod['id']
        tmpl = prod.get('product_tmpl_id')
        categ = prod.get('categ_id', [None, ''])
        categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
        
        if tmpl:
            tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
            template_ids_compra.add(tmpl_id)
            product_to_template_compra[prod_id] = {
                'tmpl_id': tmpl_id,
                'categ_name': categ_name
            }
    
    # Obtener templates
    templates_compra = odoo.search_read(
        'product.template',
        [['id', 'in', list(template_ids_compra)]],
        ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
        limit=100000
    )
    
    template_map_compra = {}
    for tmpl in templates_compra:
        template_map_compra[tmpl['id']] = {
            'nombre': tmpl.get('name', '')
        }
    
    # Categorizar compras
    kg_productos = 0
    kg_otros = 0
    
    productos_compra_detalle = {}
    
    for linea in lineas_compra:
        prod_id = linea.get('product_id', [None])[0]
        kg = linea.get('quantity', 0)
        
        if prod_id in product_to_template_compra:
            prod_data = product_to_template_compra[prod_id]
            categ_name = prod_data['categ_name']
            
            es_producto = 'PRODUCTOS' in categ_name.upper()
            
            if es_producto:
                kg_productos += kg
                
                tmpl_id = prod_data['tmpl_id']
                if tmpl_id not in productos_compra_detalle:
                    nombre = template_map_compra.get(tmpl_id, {}).get('nombre', 'N/A')
                    productos_compra_detalle[tmpl_id] = {
                        'nombre': nombre,
                        'categoria': categ_name,
                        'kg': 0
                    }
                productos_compra_detalle[tmpl_id]['kg'] += kg
            else:
                kg_otros += kg
    
    print(f"\n📊 COMPRAS por categoría:")
    print(f"  PRODUCTOS: {kg_productos:,.2f} kg ({kg_productos/total_kg_compra*100:.1f}%)")
    print(f"  OTROS: {kg_otros:,.2f} kg ({kg_otros/total_kg_compra*100:.1f}%)")
    
    # ========== VENTAS ==========
    print("\n\n💰 VENTAS (account.move.line - out_invoice)")
    print("-" * 80)
    
    lineas_venta = odoo.search_read(
        'account.move.line',
        [
            ['move_id.move_type', '=', 'out_invoice'],
            ['move_id.state', '=', 'posted'],
            ['product_id', '!=', False],
            ['date', '>=', fecha_desde],
            ['date', '<=', fecha_hasta],
            ['quantity', '>', 0],
            ['credit', '>', 0]
        ],
        ['product_id', 'quantity', 'credit'],
        limit=100000
    )
    
    print(f"Líneas de venta: {len(lineas_venta)}")
    total_kg_venta = sum(l.get('quantity', 0) for l in lineas_venta)
    total_monto_venta = sum(l.get('credit', 0) for l in lineas_venta)
    print(f"Total kg: {total_kg_venta:,.2f}")
    print(f"Total monto: ${total_monto_venta:,.0f}")
    
    # Productos en ventas
    prod_ids_venta = list(set([l.get('product_id', [None])[0] for l in lineas_venta if l.get('product_id')]))
    print(f"Productos únicos: {len(prod_ids_venta)}")
    
    # Obtener info de productos
    productos_venta = odoo.search_read(
        'product.product',
        [['id', 'in', prod_ids_venta]],
        ['id', 'product_tmpl_id', 'categ_id'],
        limit=100000
    )
    
    # Templates
    template_ids_venta = set()
    product_to_template_venta = {}
    
    for prod in productos_venta:
        prod_id = prod['id']
        tmpl = prod.get('product_tmpl_id')
        categ = prod.get('categ_id', [None, ''])
        categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
        
        if tmpl:
            tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
            template_ids_venta.add(tmpl_id)
            product_to_template_venta[prod_id] = {
                'tmpl_id': tmpl_id,
                'categ_name': categ_name
            }
    
    # Obtener templates
    templates_venta = odoo.search_read(
        'product.template',
        [['id', 'in', list(template_ids_venta)]],
        ['id', 'name'],
        limit=100000
    )
    
    template_map_venta = {}
    for tmpl in templates_venta:
        template_map_venta[tmpl['id']] = {
            'nombre': tmpl.get('name', '')
        }
    
    # Categorizar ventas
    kg_productos_venta = 0
    kg_otros_venta = 0
    
    productos_venta_detalle = {}
    
    for linea in lineas_venta:
        prod_id = linea.get('product_id', [None])[0]
        kg = linea.get('quantity', 0)
        
        if prod_id in product_to_template_venta:
            prod_data = product_to_template_venta[prod_id]
            categ_name = prod_data['categ_name']
            
            es_producto = 'PRODUCTOS' in categ_name.upper()
            
            if es_producto:
                kg_productos_venta += kg
                
                tmpl_id = prod_data['tmpl_id']
                if tmpl_id not in productos_venta_detalle:
                    nombre = template_map_venta.get(tmpl_id, {}).get('nombre', 'N/A')
                    productos_venta_detalle[tmpl_id] = {
                        'nombre': nombre,
                        'categoria': categ_name,
                        'kg': 0
                    }
                productos_venta_detalle[tmpl_id]['kg'] += kg
            else:
                kg_otros_venta += kg
    
    print(f"\n📊 VENTAS por categoría:")
    print(f"  PRODUCTOS: {kg_productos_venta:,.2f} kg ({kg_productos_venta/total_kg_venta*100:.1f}%)")
    print(f"  OTROS: {kg_otros_venta:,.2f} kg ({kg_otros_venta/total_kg_venta*100:.1f}%)")
    
    # ========== TOP PRODUCTOS ==========
    print(f"\n\n📦 TOP 15 PRODUCTOS COMPRADOS:")
    print("-" * 80)
    top_compra = sorted(productos_compra_detalle.items(), key=lambda x: x[1]['kg'], reverse=True)[:15]
    for i, (tmpl_id, data) in enumerate(top_compra, 1):
        print(f"{i:2d}. {data['nombre'][:60]}")
        print(f"    Categoría: {data['categoria']}")
        print(f"    Kg: {data['kg']:>12,.2f}")
        print()
    
    print(f"\n💰 TOP 15 PRODUCTOS VENDIDOS:")
    print("-" * 80)
    top_venta = sorted(productos_venta_detalle.items(), key=lambda x: x[1]['kg'], reverse=True)[:15]
    for i, (tmpl_id, data) in enumerate(top_venta, 1):
        print(f"{i:2d}. {data['nombre'][:60]}")
        print(f"    Categoría: {data['categoria']}")
        print(f"    Kg: {data['kg']:>12,.2f}")
        print()
    
    print("\n" + "="*80)
    print("RESUMEN COMPARATIVO")
    print("="*80)
    print(f"COMPRAS PRODUCTOS: {kg_productos:,.2f} kg (${total_monto_compra:,.0f})")
    print(f"VENTAS PRODUCTOS:  {kg_productos_venta:,.2f} kg (${total_monto_venta:,.0f})")
    print(f"DIFERENCIA:        {kg_productos_venta - kg_productos:,.2f} kg")
    print(f"RATIO V/C:         {kg_productos_venta/kg_productos if kg_productos > 0 else 0:.2f}x")
    print("="*80)

if __name__ == "__main__":
    debug_periodo()
