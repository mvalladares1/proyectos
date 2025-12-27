"""
Debug script para analizar la recepción RF/RFP/IN/00798
"""
import xmlrpc.client
import getpass

ODOO_URL = "https://riofuturo.server98c6e.oerpondemand.net"
ODOO_DB = "riofuturo-master"

def debug_reception():
    print("=" * 60)
    print("DEBUG: Análisis de Recepción Odoo")
    print("=" * 60)
    email = input("Email Odoo: ")
    api_key = getpass.getpass("API Key: ")
    
    print("\n🔄 Conectando a Odoo...")
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, email, api_key, {})
    
    if not uid:
        print("❌ Error de autenticación")
        return
    
    print(f"✅ Conectado como UID: {uid}")
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    
    def search_read(model, domain, fields, limit=100):
        return models.execute_kw(ODOO_DB, uid, api_key, model, 'search_read', [domain], {'fields': fields, 'limit': limit})
    
    # 1. Buscar picking
    print("\n" + "=" * 60)
    print("1️⃣ Buscando recepción RF/RFP/IN/00798")
    print("=" * 60)
    
    pickings = search_read('stock.picking', [('name', '=', 'RF/RFP/IN/00798')], ['id', 'name', 'state', 'move_line_ids'])
    if not pickings:
        print("❌ Recepción NO encontrada")
        return
    
    picking = pickings[0]
    print(f"✅ ID: {picking['id']}, State: {picking['state']}, Move Lines: {len(picking['move_line_ids'])}")
    
    # 2. Buscar move_lines - SIN product_uom_qty
    print("\n" + "=" * 60)
    print("2️⃣ Buscando move_lines del picking")
    print("=" * 60)
    
    move_lines = search_read(
        'stock.move.line',
        [('picking_id', '=', picking['id'])],
        ['id', 'product_id', 'lot_id', 'package_id', 'result_package_id', 'qty_done', 'reserved_uom_qty', 'state'],
        limit=50
    )
    
    print(f"Total move_lines: {len(move_lines)}")
    
    # 3. Buscar PACK0010493
    print("\n" + "=" * 60)
    print("3️⃣ Buscando PACK0010493 en move_lines")
    print("=" * 60)
    
    found = False
    for ml in move_lines:
        result_pkg = ml.get('result_package_id')
        pkg = ml.get('package_id')
        
        result_pkg_name = result_pkg[1] if result_pkg else 'None'
        pkg_name = pkg[1] if pkg else 'None'
        
        if 'PACK0010493' in str(result_pkg_name) or 'PACK0010493' in str(pkg_name):
            print(f"\n🎯 ENCONTRADO!")
            print(f"   move_line ID: {ml['id']}")
            print(f"   product_id: {ml['product_id']}")
            print(f"   lot_id: {ml['lot_id']}")
            print(f"   package_id: {ml['package_id']}")
            print(f"   result_package_id: {ml['result_package_id']}")
            print(f"   qty_done: {ml['qty_done']}")
            print(f"   reserved_uom_qty: {ml['reserved_uom_qty']}")
            print(f"   state: {ml['state']}")
            found = True
    
    if not found:
        print("❌ PACK0010493 NO encontrado")
        print("\nMostrando TODAS las move_lines para análisis:")
        for i, ml in enumerate(move_lines):
            r_pkg = ml['result_package_id'][1] if ml['result_package_id'] else 'None'
            print(f"   [{i}] result_package: {r_pkg}, qty_done: {ml['qty_done']}")
    
    # 4. Buscar package
    print("\n" + "=" * 60)
    print("4️⃣ Buscando en stock.quant.package")
    print("=" * 60)
    
    packages = search_read('stock.quant.package', [('name', '=', 'PACK0010493')], ['id', 'name'])
    if packages:
        print(f"✅ Package existe: ID={packages[0]['id']}")
    else:
        print("❌ PACK0010493 NO existe en stock.quant.package")
        similar = search_read('stock.quant.package', [('name', 'ilike', 'PACK001049')], ['id', 'name'], limit=10)
        print(f"   Similares: {[p['name'] for p in similar]}")

    print("\n✅ DEBUG COMPLETO")

if __name__ == "__main__":
    debug_reception()
