"""
Script para verificar el ID del picking type de San Jose.
Ejecuta esto desde un terminal de Python en Streamlit o con tus credenciales.
"""

def check_picking_types(username, password):
    """Verifica los IDs de picking types de recepciones MP en Odoo."""
    from shared.odoo_client import OdooClient
    
    client = OdooClient(username=username, password=password)
    
    # Buscar todos los picking types de recepciones MP
    pts = client.search_read(
        "stock.picking.type",
        [("name", "ilike", "Recepciones MP")],
        ["id", "name", "warehouse_id"]
    )
    
    print("\n" + "="*70)
    print("PICKING TYPES DE RECEPCIONES MP ENCONTRADOS EN ODOO")
    print("="*70)
    
    if not pts:
        print("NO SE ENCONTRARON PICKING TYPES")
        return None
    
    for pt in pts:
        warehouse = pt.get('warehouse_id', [None, 'N/A'])
        warehouse_name = warehouse[1] if isinstance(warehouse, (list, tuple)) else warehouse
        print(f"ID: {pt['id']:3d} | {pt['name']:50s} | Warehouse: {warehouse_name}")
    
    print("="*70 + "\n")
    
    # Buscar específicamente San Jose
    san_jose = [p for p in pts if 'SAN JOSE' in p['name'].upper() or 'SANJOSE' in p['name'].upper()]
    
    if san_jose:
        print("ENCONTRADO SAN JOSE:")
        for sj in san_jose:
            print(f"  -> ID: {sj['id']} | Nombre: {sj['name']}")
    else:
        print("WARNING: No se encontro 'San Jose' en los nombres")
        print("Revisa manualmente cual es el ID correcto de la lista de arriba")
    
    return pts

# Para usar este script, ejecuta en Python:
# from check_san_jose_id_interactive import check_picking_types
# check_picking_types("tu_usuario_odoo", "tu_api_key_odoo")
