"""
Script para buscar detalles de la orden WH/Transf/00666 sin filtro de fecha
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.odoo_client import OdooClient

# Credenciales
ODOO_USERNAME = "mjaramillo@riofuturo.cl"
ODOO_PASSWORD = "659e9fd07b2bc2c0aca3539de16a9da50bb263b1"

def buscar_orden():
    print("=" * 80)
    print("BUSCANDO ORDEN WH/Transf/00666 EN ODOO")
    print("=" * 80)
    
    odoo = OdooClient(username=ODOO_USERNAME, password=ODOO_PASSWORD)
    
    # 1. Buscar en mrp.production
    print("\n1. Buscando en mrp.production...")
    productions = odoo.search_read(
        'mrp.production',
        [('name', 'ilike', 'WH/Transf/00666')],
        ['name', 'state', 'date_planned_start', 'product_id']
    )
    
    if productions:
        print(f"\nEncontradas {len(productions)} ordenes:")
        for prod in productions:
            print(f"\n  - Nombre: {prod.get('name')}")
            print(f"    Estado: {prod.get('state')}")
            print(f"    Fecha: {prod.get('date_planned_start')}")
            print(f"    Producto: {prod.get('product_id')}")
            print(f"    ID: {prod.get('id')}")
            
            production_id = prod['id']
            
            # 2. Buscar stock.move de esa producción
            print(f"\n2. Buscando stock.move de producción {production_id}...")
            moves = odoo.search_read(
                'stock.move',
                [('production_id', '=', production_id)],
                ['name', 'state', 'product_qty', 'quantity_done', 'product_id', 'date']
            )
            
            print(f"   Encontrados {len(moves)} stock.move:")
            for move in moves:
                print(f"\n     - Producto: {move.get('product_id')}")
                print(f"       Cantidad planeada: {move.get('product_qty')}")
                print(f"       Cantidad hecha: {move.get('quantity_done')}")
                print(f"       Estado: {move.get('state')}")
                print(f"       Fecha: {move.get('date')}")
                print(f"       Move ID: {move.get('id')}")
                
                # 3. Buscar stock.move.line de ese move
                move_id = move['id']
                print(f"\n     3. Buscando stock.move.line del move {move_id}...")
                move_lines = odoo.search_read(
                    'stock.move.line',
                    [('move_id', '=', move_id)],
                    ['package_id', 'qty_done', 'product_id', 'state', 'date']
                )
                
                print(f"        Encontrados {len(move_lines)} stock.move.line:")
                for ml in move_lines:
                    print(f"\n          - Package: {ml.get('package_id')}")
                    print(f"            Qty done: {ml.get('qty_done')}")
                    print(f"            Producto: {ml.get('product_id')}")
                    print(f"            Estado: {ml.get('state')}")
                    print(f"            Fecha: {ml.get('date')}")
    else:
        print("\nNo se encontro la orden WH/Transf/00666 en mrp.production")

if __name__ == "__main__":
    buscar_orden()
