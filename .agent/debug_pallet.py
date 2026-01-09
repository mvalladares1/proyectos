
import os
import xmlrpc.client
import ssl

# Config
url = os.environ.get('ODOO_URL', 'https://riofuturo.server98c6e.oerpondemand.net')
db = os.environ.get('ODOO_DB', 'riofuturo-production-3968038')
username = os.environ.get('ODOO_USERNAME', 'admin')
# We need to use the real password or run this inside the container where credentials might be available
# Or asking user for password is annoying.
# I will assume I can run this inside the container using the existing `tuneles_service` or just use the `odoo_client` if available.
# Actually, the easiest way is to use `backend/main.py` context or similar, OR just use `xmlrpc` with the credentials from `config/settings` if I can read them.
# But I don't have the password in plain text easily unless I read `.env` waiting...
# I'll try to read `.env` from the project root if it exists, or assuming I run this IN the container where env vars are set.

password = os.environ.get('ODOO_PASSWORD') 

def run():
    if not password:
        print("Error: ODOO_PASSWORD not set")
        return

    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

    # Pallet to check
    pallet_name = "PACK0016141"
    
    print(f"Checking pallet: {pallet_name}")
    
    # 1. Get Package ID
    packages = models.execute_kw(db, uid, password, 'stock.quant.package', 'search_read',
        [[('name', '=', pallet_name)]],
        {'fields': ['id', 'name']})
    
    if not packages:
        print("Package not found")
        return

    pkg_id = packages[0]['id']
    print(f"Package ID: {pkg_id}")

    # 2. Search Move Lines
    lines = models.execute_kw(db, uid, password, 'stock.move.line', 'search_read',
        [[('package_id', '=', pkg_id)]],
        {'fields': ['id', 'picking_id', 'move_id', 'production_id', 'state', 'reference']})
        
    print(f"Found {len(lines)} move lines:")
    for l in lines:
        print(f"Line ID: {l['id']}")
        print(f"  State: {l['state']}")
        print(f"  Reference: {l['reference']}")
        print(f"  Production ID: {l['production_id']}")
        print(f"  Move ID: {l['move_id']}")
        
        # If Move ID exists, check the move for raw_material_production_id
        if l['move_id']:
            move = models.execute_kw(db, uid, password, 'stock.move', 'read',
                [l['move_id'][0]],
                {'fields': ['raw_material_production_id', 'production_id', 'state']})
            if move:
                print(f"  -> Move Raw Material MO: {move[0].get('raw_material_production_id')}")
                print(f"  -> Move Production MO: {move[0].get('production_id')}")
                print(f"  -> Move State: {move[0].get('state')}")

if __name__ == "__main__":
    run()
