"""
Debug: Analizar facturas de compra 2022-01-01 a 2025-11-01
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.odoo_client import OdooClient

def debug_compras():
    username = input("Usuario Odoo: ")
    password = input("API Key: ")
    
    odoo = OdooClient(username=username, password=password)
    
    fecha_desde = "2022-01-01"
    fecha_hasta = "2025-11-01"
    
    print("\n" + "="*80)
    print(f"DEBUG FACTURAS DE COMPRA")
    print(f"Período: {fecha_desde} → {fecha_hasta}")
    print("="*80)
    
    # Líneas de facturas de proveedor
    lineas = odoo.search_read(
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
        ['product_id', 'quantity', 'debit', 'date'],
        limit=100000
    )
    
    print(f"\n📋 Líneas de factura encontradas: {len(lineas)}")
    total_kg_facturas = sum(l.get('quantity', 0) for l in lineas)
    total_monto_facturas = sum(l.get('debit', 0) for l in lineas)
    print(f"Total kg en facturas: {total_kg_facturas:,.2f}")
    print(f"Total monto: ${total_monto_facturas:,.2f}")
    
    # Productos únicos
    prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas if l.get('product_id')]))
    print(f"Productos únicos: {len(prod_ids)}")
    
    # Obtener product.product
    productos = odoo.search_read(
        'product.product',
        [['id', 'in', prod_ids]],
        ['id', 'product_tmpl_id', 'categ_id'],
        limit=100000
    )
    
    # Extraer templates
    template_ids = set()
    product_to_template = {}
    
    for prod in productos:
        prod_id = prod['id']
        tmpl = prod.get('product_tmpl_id')
        if tmpl:
            tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
            template_ids.add(tmpl_id)
            product_to_template[prod_id] = {
                'tmpl_id': tmpl_id,
                'categ': prod.get('categ_id', [None, ''])
            }
    
    print(f"Templates únicos: {len(template_ids)}")
    
    # Obtener templates
    templates = odoo.search_read(
        'product.template',
        [['id', 'in', list(template_ids)]],
        ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
        limit=100000
    )
    
    # Categorizar templates
    template_map = {}
    con_tipo = 0
    con_manejo = 0
    con_ambos = 0
    
    for tmpl in templates:
        # Parsear tipo
        tipo = tmpl.get('x_studio_sub_categora')
        if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
            tipo_str = tipo[1]
            tiene_tipo = True
        elif isinstance(tipo, str) and tipo:
            tipo_str = tipo
            tiene_tipo = True
        else:
            tipo_str = None
            tiene_tipo = False
        
        # Parsear manejo
        manejo = tmpl.get('x_studio_categora_tipo_de_manejo')
        if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
            manejo_str = manejo[1]
            tiene_manejo = True
        elif isinstance(manejo, str) and manejo:
            manejo_str = manejo
            tiene_manejo = True
        else:
            manejo_str = None
            tiene_manejo = False
        
        if tiene_tipo:
            con_tipo += 1
        if tiene_manejo:
            con_manejo += 1
        if tiene_tipo and tiene_manejo:
            con_ambos += 1
        
        template_map[tmpl['id']] = {
            'nombre': tmpl.get('name', ''),
            'tipo': tipo_str,
            'manejo': manejo_str,
            'tiene_ambos': tiene_tipo and tiene_manejo
        }
    
    print(f"\n📊 TEMPLATES:")
    print(f"  Con tipo: {con_tipo}")
    print(f"  Con manejo: {con_manejo}")
    print(f"  Con AMBOS: {con_ambos}")
    
    # Calcular kg con y sin tipo+manejo
    kg_con_ambos = 0
    kg_sin_ambos = 0
    monto_con_ambos = 0
    monto_sin_ambos = 0
    
    productos_con = {}
    productos_sin = {}
    
    for linea in lineas:
        prod_id = linea.get('product_id', [None])[0]
        kg = linea.get('quantity', 0)
        monto = linea.get('debit', 0)
        
        if prod_id in product_to_template:
            prod_data = product_to_template[prod_id]
            tmpl_id = prod_data['tmpl_id']
            categ = prod_data['categ']
            categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
            
            if tmpl_id in template_map:
                tmpl_info = template_map[tmpl_id]
                
                if tmpl_info['tiene_ambos']:
                    kg_con_ambos += kg
                    monto_con_ambos += monto
                    
                    if tmpl_id not in productos_con:
                        productos_con[tmpl_id] = {
                            'nombre': tmpl_info['nombre'],
                            'tipo': tmpl_info['tipo'],
                            'manejo': tmpl_info['manejo'],
                            'categoria': categ_name,
                            'kg': 0,
                            'monto': 0
                        }
                    productos_con[tmpl_id]['kg'] += kg
                    productos_con[tmpl_id]['monto'] += monto
                else:
                    kg_sin_ambos += kg
                    monto_sin_ambos += monto
                    
                    if tmpl_id not in productos_sin:
                        productos_sin[tmpl_id] = {
                            'nombre': tmpl_info['nombre'],
                            'tipo': tmpl_info['tipo'],
                            'manejo': tmpl_info['manejo'],
                            'categoria': categ_name,
                            'kg': 0,
                            'monto': 0
                        }
                    productos_sin[tmpl_id]['kg'] += kg
                    productos_sin[tmpl_id]['monto'] += monto
    
    print(f"\n💰 ANÁLISIS:")
    print(f"  Kg CON tipo+manejo: {kg_con_ambos:,.2f} (${monto_con_ambos:,.0f})")
    print(f"  Kg SIN tipo+manejo: {kg_sin_ambos:,.2f} (${monto_sin_ambos:,.0f})")
    print(f"  % con tipo+manejo: {kg_con_ambos/total_kg_facturas*100:.1f}%")
    
    # Top 20 productos CON tipo+manejo
    print(f"\n✅ TOP 20 PRODUCTOS CON TIPO+MANEJO:")
    print("-" * 80)
    top_con = sorted(productos_con.items(), key=lambda x: x[1]['kg'], reverse=True)[:20]
    for i, (tmpl_id, data) in enumerate(top_con, 1):
        print(f"{i:2d}. {data['nombre'][:55]}")
        print(f"    Tipo: {data['tipo']:20} | Manejo: {data['manejo']}")
        print(f"    Categoría: {data['categoria']}")
        print(f"    Kg: {data['kg']:>12,.2f} | Monto: ${data['monto']:>12,.0f}")
        print()
    
    # Top 20 productos SIN tipo+manejo
    print(f"\n❌ TOP 20 PRODUCTOS SIN TIPO+MANEJO:")
    print("-" * 80)
    top_sin = sorted(productos_sin.items(), key=lambda x: x[1]['kg'], reverse=True)[:20]
    for i, (tmpl_id, data) in enumerate(top_sin, 1):
        print(f"{i:2d}. {data['nombre'][:55]}")
        print(f"    Tipo: {data['tipo'] or 'NO TIENE':20} | Manejo: {data['manejo'] or 'NO TIENE'}")
        print(f"    Categoría: {data['categoria']}")
        print(f"    Kg: {data['kg']:>12,.2f} | Monto: ${data['monto']:>12,.0f}")
        print()
    
    print("\n" + "="*80)
    print("RESUMEN")
    print("="*80)
    print(f"Total facturas: {total_kg_facturas:,.2f} kg (${total_monto_facturas:,.0f})")
    print(f"Con tipo+manejo: {kg_con_ambos:,.2f} kg ({kg_con_ambos/total_kg_facturas*100:.1f}%)")
    print(f"Sin tipo+manejo: {kg_sin_ambos:,.2f} kg ({kg_sin_ambos/total_kg_facturas*100:.1f}%)")
    print("="*80)

if __name__ == "__main__":
    debug_compras()
