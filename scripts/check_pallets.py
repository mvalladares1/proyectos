from backend.services.recepciones_gestion_service import RecepcionesGestionService
from shared.odoo_client import OdooClient
import os
from dotenv import load_dotenv

load_dotenv()

def test_pallet_count():
    client = OdooClient()
    # Buscar pickings recientes de MP
    pickings = client.search_read(
        'stock.picking',
        [
            ['picking_type_id', '=', 1],
            ['x_studio_categora_de_producto', '=', 'MP'],
            ['state', '=', 'done']
        ],
        ['id', 'name'],
        limit=5
    )
    
    for p in pickings:
        p_id = p['id']
        name = p['name']
        print(f"\nPicking: {name} (ID: {p_id})")
        
        # Consultar move lines
        move_lines = client.search_read(
            'stock.move.line',
            [['picking_id', '=', p_id]],
            ['id', 'result_package_id', 'product_id', 'qty_done']
        )
        
        print(f"Total Move Lines: {len(move_lines)}")
        packages = [ml['result_package_id'] for ml in move_lines if ml.get('result_package_id')]
        print(f"Lines with Packages: {len(packages)}")
        unique_packages = len(set([pkg[0] if isinstance(pkg, (list, tuple)) else pkg for pkg in packages]))
        print(f"Unique Packages: {unique_packages}")
        
        for ml in move_lines:
             print(f"  - ML ID: {ml['id']}, Product: {ml['product_id']}, Qty: {ml['qty_done']}, Pkg: {ml['result_package_id']}")

if __name__ == "__main__":
    test_pallet_count()
