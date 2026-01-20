"""
Script usando la misma lógica del backend de recepciones
Filtra por x_studio_categora_de_producto = "MP" en stock.picking
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.odoo_client import OdooClient

def analizar_recepciones_mp():
    username = input("Usuario Odoo: ")
    password = input("API Key: ")
    
    odoo = OdooClient(username=username, password=password)
    
    fecha_desde = "2024-12-01"
    fecha_hasta = "2025-01-31"
    
    print("\n" + "="*80)
    print(f"ANÁLISIS RECEPCIONES MP (usando lógica del backend)")
    print(f"Período: {fecha_desde} hasta {fecha_hasta}")
    print("="*80)
    
    # FILTRO EXACTO del backend
    domain = [
        ("picking_type_id", "in", [1, 217, 164]),  # RFP, VILKUN, SAN JOSE
        ("x_studio_categora_de_producto", "=", "MP"),
        ("scheduled_date", ">=", fecha_desde + " 00:00:00"),
        ("scheduled_date", "<=", fecha_hasta + " 23:59:59"),
        ("state", "=", "done")
    ]
    
    print("\n📦 RECEPCIONES MP...")
    recepciones = odoo.search_read(
        "stock.picking",
        domain,
        ["id", "name", "scheduled_date", "x_studio_categora_de_producto"],
        limit=10000
    )
    
    print(f"Total recepciones MP: {len(recepciones)}")
    
    if not recepciones:
        print("No se encontraron recepciones MP")
        return
    
    picking_ids = [r["id"] for r in recepciones]
    
    # Obtener movimientos
    print("\n📋 MOVIMIENTOS DE STOCK...")
    movimientos = odoo.search_read(
        "stock.move",
        [("picking_id", "in", picking_ids)],
        ["id", "picking_id", "product_id", "product_uom_qty"],
        limit=100000
    )
    
    print(f"Total movimientos: {len(movimientos)}")
    total_kg = sum(m.get("product_uom_qty", 0) for m in movimientos)
    print(f"Total kg: {total_kg:,.2f}")
    
    # Obtener productos únicos
    prod_ids = list(set([m.get("product_id", [None])[0] for m in movimientos if m.get("product_id")]))
    print(f"Productos únicos: {len(prod_ids)}")
    
    # Obtener product.product -> product.template
    print("\n🍓 PRODUCTOS...")
    productos = odoo.search_read(
        "product.product",
        [["id", "in", prod_ids]],
        ["id", "product_tmpl_id", "categ_id"],
        limit=10000
    )
    
    # Extraer template IDs
    template_ids = set()
    for p in productos:
        tmpl = p.get("product_tmpl_id")
        if tmpl:
            tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
            template_ids.add(tmpl_id)
    
    print(f"Templates únicos: {len(template_ids)}")
    
    # Obtener templates con campos de tipo y manejo
    print("\n📝 TEMPLATES...")
    templates = odoo.search_read(
        "product.template",
        [["id", "in", list(template_ids)]],
        ["id", "name", "x_studio_categora_tipo_de_manejo", "x_studio_sub_categora"],
        limit=10000
    )
    
    # Mapear templates
    template_map = {}
    con_tipo = 0
    con_manejo = 0
    con_ambos = 0
    
    for t in templates:
        manejo = t.get("x_studio_categora_tipo_de_manejo", "")
        if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
            manejo_str = manejo[1]
            tiene_manejo = True
        elif isinstance(manejo, str) and manejo:
            manejo_str = manejo
            tiene_manejo = True
        else:
            manejo_str = None
            tiene_manejo = False
        
        tipo = t.get("x_studio_sub_categora", "")
        if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
            tipo_str = tipo[1]
            tiene_tipo = True
        elif isinstance(tipo, str) and tipo:
            tipo_str = tipo
            tiene_tipo = True
        else:
            tipo_str = None
            tiene_tipo = False
        
        if tiene_tipo:
            con_tipo += 1
        if tiene_manejo:
            con_manejo += 1
        if tiene_tipo and tiene_manejo:
            con_ambos += 1
        
        template_map[t["id"]] = {
            "nombre": t.get("name", ""),
            "tipo": tipo_str,
            "manejo": manejo_str,
            "tiene_tipo": tiene_tipo,
            "tiene_manejo": tiene_manejo,
            "tiene_ambos": tiene_tipo and tiene_manejo
        }
    
    print(f"\nTemplates con tipo: {con_tipo}")
    print(f"Templates con manejo: {con_manejo}")
    print(f"Templates con AMBOS: {con_ambos}")
    
    # Mapear product -> template
    product_to_template = {}
    for p in productos:
        prod_id = p["id"]
        tmpl = p.get("product_tmpl_id")
        if tmpl:
            tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
            product_to_template[prod_id] = tmpl_id
    
    # Calcular kg por categoría
    kg_con_tipo = 0
    kg_con_manejo = 0
    kg_con_ambos = 0
    
    productos_detalle = {}
    productos_sin_clasificar = {}
    
    for mov in movimientos:
        prod_id = mov.get("product_id", [None])[0]
        kg = mov.get("product_uom_qty", 0)
        
        if prod_id in product_to_template:
            tmpl_id = product_to_template[prod_id]
            if tmpl_id in template_map:
                info = template_map[tmpl_id]
                
                if info["tiene_tipo"]:
                    kg_con_tipo += kg
                if info["tiene_manejo"]:
                    kg_con_manejo += kg
                if info["tiene_ambos"]:
                    kg_con_ambos += kg
                    
                    # Detalle por template
                    if tmpl_id not in productos_detalle:
                        productos_detalle[tmpl_id] = {
                            "nombre": info["nombre"],
                            "tipo": info["tipo"],
                            "manejo": info["manejo"],
                            "kg": 0
                        }
                    productos_detalle[tmpl_id]["kg"] += kg
                else:
                    # Productos SIN tipo+manejo
                    if tmpl_id not in productos_sin_clasificar:
                        productos_sin_clasificar[tmpl_id] = {
                            "nombre": info["nombre"],
                            "tipo": info["tipo"],
                            "manejo": info["manejo"],
                            "kg": 0
                        }
                    productos_sin_clasificar[tmpl_id]["kg"] += kg
    
    print(f"\n📊 KG:")
    print(f"  Total: {total_kg:,.2f}")
    print(f"  Con tipo: {kg_con_tipo:,.2f}")
    print(f"  Con manejo: {kg_con_manejo:,.2f}")
    print(f"  Con AMBOS: {kg_con_ambos:,.2f}")
    print(f"  Sin clasificar: {total_kg - kg_con_ambos:,.2f}")
    
    # Top productos
    print(f"\n🍓 TOP 30 PRODUCTOS CON TIPO+MANEJO:")
    print("-" * 80)
    
    top_productos = sorted(productos_detalle.items(), key=lambda x: x[1]["kg"], reverse=True)[:30]
    
    for i, (tmpl_id, data) in enumerate(top_productos, 1):
        print(f"{i:2d}. {data['nombre'][:60]}")
        print(f"      Tipo: {data['tipo']:20} | Manejo: {data['manejo']}")
        print(f"      Kg: {data['kg']:>12,.2f}")
        print()
    
    # Productos SIN clasificar
    print(f"\n❌ TOP 20 PRODUCTOS SIN TIPO+MANEJO:")
    print("-" * 80)
    
    top_sin_clasificar = sorted(productos_sin_clasificar.items(), key=lambda x: x[1]["kg"], reverse=True)[:20]
    
    for i, (tmpl_id, data) in enumerate(top_sin_clasificar, 1):
        print(f"{i:2d}. {data['nombre'][:60]}")
        print(f"      Tipo: {data['tipo'] or 'NO TIENE':20} | Manejo: {data['manejo'] or 'NO TIENE'}")
        print(f"      Kg: {data['kg']:>12,.2f}")
        print()
    
    print("\n" + "="*80)
    print("RESUMEN FINAL")
    print("="*80)
    print(f"Recepciones MP: {len(recepciones)}")
    print(f"Total kg: {total_kg:,.2f}")
    print(f"Kg con tipo+manejo: {kg_con_ambos:,.2f} ({kg_con_ambos/total_kg*100:.1f}%)")
    print(f"Kg sin tipo+manejo: {total_kg - kg_con_ambos:,.2f} ({(total_kg - kg_con_ambos)/total_kg*100:.1f}%)")
    print("="*80)

if __name__ == "__main__":
    analizar_recepciones_mp()
