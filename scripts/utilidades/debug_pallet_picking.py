"""
Debug script para probar la búsqueda de pallets como lo hace stock-picking
"""
import sys
from pathlib import Path

# Agregar shared al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.odoo_client import OdooClient

# Credenciales estáticas para debug
ODOO_URL = "https://riofuturo.server98c6e.oerpondemand.net"
ODOO_DB = "riofuturo-master"
ODOO_USER = "mvalladares@riofuturo.cl"
ODOO_PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"


def debug_pallet_search(barcode: str):
    """Buscar pallet por barcode y mostrar toda la info"""
    print(f"\n{'='*60}")
    print(f"🔍 Buscando pallet: {barcode}")
    print(f"{'='*60}")
    
    client = OdooClient(
        username=ODOO_USER,
        password=ODOO_PASSWORD,
        url=ODOO_URL,
        db=ODOO_DB
    )
    print(f"✅ Conectado a Odoo: {client.url}")
    print(f"   DB: {client.db}")
    print(f"   Usuario: {client.username}")
    
    # 1. Buscar el paquete (stock.quant.package)
    print(f"\n📦 Buscando en stock.quant.package...")
    packages = client.search_read(
        'stock.quant.package',
        [['name', '=', barcode]],
        ['id', 'name', 'location_id', 'pack_date', 'quant_ids']
    )
    
    if not packages:
        print(f"❌ Paquete '{barcode}' NO encontrado")
        return
    
    pkg = packages[0]
    print(f"✅ Paquete encontrado:")
    print(f"   ID: {pkg.get('id')}")
    print(f"   Name: {pkg.get('name')}")
    print(f"   Location: {pkg.get('location_id')}")
    print(f"   Pack Date: {pkg.get('pack_date')}")
    print(f"   Quant IDs: {pkg.get('quant_ids')}")
    
    # 2. Buscar los quants del paquete
    quant_ids = pkg.get('quant_ids', [])
    if quant_ids:
        print(f"\n📊 Buscando {len(quant_ids)} quants...")
        quants = client.search_read(
            'stock.quant',
            [['id', 'in', quant_ids]],
            ['id', 'product_id', 'lot_id', 'quantity', 'reserved_quantity', 
             'location_id', 'in_date']
        )
        
        total_qty = 0
        for q in quants:
            print(f"\n   Quant {q.get('id')}:")
            print(f"      Producto: {q.get('product_id')}")
            print(f"      Lote: {q.get('lot_id')}")
            print(f"      Cantidad: {q.get('quantity')}")
            print(f"      Reservado: {q.get('reserved_quantity')}")
            print(f"      Ubicación: {q.get('location_id')}")
            total_qty += q.get('quantity', 0)
        
        print(f"\n   📦 Total KG: {total_qty}")
    else:
        print(f"⚠️ No hay quants asociados al paquete")
    
    # 3. Verificar si hay move_lines pendientes (recepción)
    print(f"\n📋 Buscando move_lines pendientes...")
    move_lines = client.search_read(
        'stock.move.line',
        [
            ['result_package_id', '=', pkg['id']],
            ['state', 'not in', ['done', 'cancel']]
        ],
        ['id', 'picking_id', 'state', 'location_dest_id', 'product_id', 'quantity']
    )
    
    if move_lines:
        print(f"⚠️ {len(move_lines)} move_lines pendientes:")
        for ml in move_lines:
            print(f"   - Picking: {ml.get('picking_id')}, State: {ml.get('state')}")
    else:
        print(f"✅ No hay move_lines pendientes")
    
    print(f"\n{'='*60}")
    print("✅ DEBUG COMPLETO")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Probar con los pallets que no muestran info
    debug_pallet_search("PACK0012543")
    debug_pallet_search("PACK0012542")
