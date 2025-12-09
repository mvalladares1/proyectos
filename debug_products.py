"""
Script de depuración para investigar discrepancia de productos en recepciones.
Ejecutar: python debug_products.py
"""
import getpass
import sys
import os

# Agregar el path del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.odoo_client import OdooClient


def main():
    print("=" * 60)
    print("DEBUG: Investigación de productos en recepción")
    print("=" * 60)
    
    # Solicitar credenciales
    username = input("Usuario Odoo: ").strip()
    password = getpass.getpass("API Key Odoo: ").strip()
    
    # Albarán a investigar
    albaran = input("Albarán (ej: RF/RFP/IN//01325): ").strip()
    if not albaran:
        albaran = "RF/RFP/IN//01325"
    
    print(f"\nConectando a Odoo como {username}...")
    
    try:
        client = OdooClient(username=username, password=password)
        print("✓ Conexión exitosa")
        
        # Verificar información de conexión y compañía
        print(f"\n=== Información de conexión ===")
        print(f"URL: {client.url}")
        print(f"DB: {client.db}")
        print(f"UID: {client.uid}")
        
        # Obtener info del usuario y compañías
        user_info = client.read("res.users", [client.uid], ["name", "company_id", "company_ids"])
        if user_info:
            u = user_info[0]
            print(f"Usuario: {u.get('name')}")
            print(f"Compañía actual: {u.get('company_id')}")
            print(f"Compañías disponibles: {u.get('company_ids')}")
            
            # Listar nombres de compañías
            company_ids = u.get('company_ids', [])
            if company_ids:
                companies = client.read("res.company", company_ids, ["id", "name"])
                print("Compañías:")
                for c in companies:
                    current = " <-- ACTUAL" if c.get('id') == (u.get('company_id') or [None])[0] else ""
                    print(f"  - ID={c.get('id')}: {c.get('name')}{current}")
        
    except Exception as e:
        print(f"✗ Error de conexión: {e}")
        return
    
    # 1. Buscar el picking
    print(f"\n1. Buscando picking '{albaran}'...")
    pickings = client.search_read(
        "stock.picking",
        [("name", "=", albaran)],
        ["id", "name", "partner_id", "scheduled_date"]
    )
    
    if not pickings:
        print(f"✗ No se encontró el picking '{albaran}'")
        return
    
    picking = pickings[0]
    print(f"✓ Encontrado: ID={picking['id']}, Partner={picking.get('partner_id')}")
    
    # 2. Obtener stock.move con más campos
    print(f"\n2. Obteniendo movimientos (stock.move)...")
    moves = client.search_read(
        "stock.move",
        [("picking_id", "=", picking["id"])],
        ["id", "product_id", "quantity_done", "product_uom", "price_unit", 
         "name", "description_picking", "reference"]
    )
    print(f"✓ {len(moves)} movimientos encontrados")
    
    # 3. Para cada movimiento, investigar el producto
    for i, move in enumerate(moves):
        print(f"\n{'='*60}")
        print(f"MOVIMIENTO {i+1}")
        print(f"{'='*60}")
        
        move_id = move.get("id")
        product_tuple = move.get("product_id", [None, ""])
        product_id = product_tuple[0] if product_tuple else None
        product_name_from_move = product_tuple[1] if product_tuple else ""
        qty = move.get("quantity_done", 0)
        price = move.get("price_unit", 0)
        
        print(f"Move ID: {move_id}")
        print(f"Cantidad: {qty}")
        print(f"Precio Unitario: ${price:,.2f}")
        print(f"stock.move 'name': {move.get('name')}")
        print(f"stock.move 'reference': {move.get('reference')}")
        print(f"\nProducto según stock.move tuple:")
        print(f"  - product_id: {product_id}")
        print(f"  - Nombre corto: {product_name_from_move}")
        
        if not product_id:
            print("  ✗ Sin product_id")
            continue
        
        # 4. Obtener product.product
        print(f"\nConsultando product.product (ID={product_id})...")
        products = client.read("product.product", [product_id], 
            ["id", "display_name", "name", "default_code", "product_tmpl_id", "categ_id"])
        
        if not products:
            print(f"  ✗ No se encontró product.product con ID={product_id}")
            continue
        
        pp = products[0]
        print(f"  product.product:")
        print(f"    - ID: {pp.get('id')}")
        print(f"    - display_name: {pp.get('display_name')}")
        print(f"    - name: {pp.get('name')}")
        print(f"    - default_code: {pp.get('default_code')}")
        print(f"    - categ_id: {pp.get('categ_id')}")
        
        tmpl_tuple = pp.get("product_tmpl_id", [None, ""])
        tmpl_id = tmpl_tuple[0] if tmpl_tuple else None
        print(f"    - product_tmpl_id: {tmpl_id} ({tmpl_tuple[1] if tmpl_tuple else ''})")
        
        # 5. Obtener product.template
        if tmpl_id:
            print(f"\nConsultando product.template (ID={tmpl_id})...")
            templates = client.read("product.template", [tmpl_id],
                ["id", "name", "default_code", "categ_id"])
            
            if templates:
                pt = templates[0]
                print(f"  product.template:")
                print(f"    - ID: {pt.get('id')}")
                print(f"    - name: {pt.get('name')}")
                print(f"    - default_code: {pt.get('default_code')}")
                print(f"    - categ_id: {pt.get('categ_id')}")
            else:
                print(f"  ✗ No se encontró product.template con ID={tmpl_id}")
        
        # 6. Buscar si hay otro producto con el mismo default_code
        default_code = pp.get("default_code") or ""
        if default_code:
            print(f"\nBuscando otros productos con default_code='{default_code}'...")
            similar = client.search_read(
                "product.product",
                [("default_code", "=", default_code)],
                ["id", "display_name", "name", "product_tmpl_id"]
            )
            print(f"  Encontrados {len(similar)} productos:")
            for s in similar:
                marker = " <-- ESTE" if s.get("id") == product_id else ""
                print(f"    - ID={s.get('id')}: {s.get('display_name')}{marker}")
    
    # 7. Buscar productos DIRECTAMENTE por default_code = '102122000'
    print("\n" + "=" * 60)
    print("BÚSQUEDA DIRECTA: default_code = '102122000'")
    print("=" * 60)
    
    # Buscar en product.product
    print("\nBuscando en product.product...")
    pp_results = client.search_read(
        "product.product",
        [("default_code", "=", "102122000")],
        ["id", "display_name", "name", "default_code", "product_tmpl_id", "active", "company_id"]
    )
    print(f"Encontrados {len(pp_results)} en product.product:")
    for p in pp_results:
        active = "✓ ACTIVO" if p.get("active", True) else "✗ INACTIVO"
        company = p.get("company_id", "Sin compañía")
        print(f"  [{active}] ID={p.get('id')}: {p.get('display_name')}")
        print(f"       name: {p.get('name')}")
        print(f"       template: {p.get('product_tmpl_id')}")
        print(f"       company: {company}")
    
    # Buscar en product.template
    print("\nBuscando en product.template...")
    pt_results = client.search_read(
        "product.template",
        [("default_code", "=", "102122000")],
        ["id", "name", "default_code", "active", "company_id"]
    )
    print(f"Encontrados {len(pt_results)} en product.template:")
    for t in pt_results:
        active = "✓ ACTIVO" if t.get("active", True) else "✗ INACTIVO"
        company = t.get("company_id", "Sin compañía")
        print(f"  [{active}] ID={t.get('id')}: {t.get('name')}")
        print(f"       company: {company}")
    
    # Buscar también productos inactivos
    print("\nBuscando INACTIVOS en product.product...")
    pp_inactive = client.search_read(
        "product.product",
        [("default_code", "=", "102122000"), ("active", "=", False)],
        ["id", "display_name", "name", "active"]
    )
    print(f"Encontrados {len(pp_inactive)} inactivos:")
    for p in pp_inactive:
        print(f"  ID={p.get('id')}: {p.get('display_name')}")
    
    # Buscar el producto que el usuario VE en la UI por nombre exacto
    print("\n" + "=" * 60)
    print("BÚSQUEDA POR NOMBRE: 'FB MK Conv. IQF en Bandeja'")
    print("=" * 60)
    expected_name = "FB MK Conv. IQF en Bandeja"
    fb_exact = client.search_read(
        "product.product",
        [("name", "ilike", expected_name)],
        ["id", "display_name", "name", "default_code", "active", "company_id"]
    )
    print(f"Encontrados {len(fb_exact)} con nombre similar a '{expected_name}':")
    for p in fb_exact:
        active = "✓" if p.get("active", True) else "✗ INACTIVO"
        print(f"  [{active}] ID={p.get('id')}: {p.get('display_name')}")
        print(f"       default_code: {p.get('default_code')}")
        print(f"       company: {p.get('company_id')}")

    print("\n" + "=" * 60)
    print("FIN DEBUG")
    print("=" * 60)


if __name__ == "__main__":
    main()
