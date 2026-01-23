import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(username=USERNAME, password=PASSWORD)

print("=" * 80)
print("ANÁLISIS FAC 000026")
print("=" * 80)

# Buscar la factura
factura = odoo.search_read(
    'account.move',
    [['name', '=', 'FAC 000026']],
    ['id', 'name', 'move_type', 'state', 'payment_state', 'journal_id', 'date']
)

if not factura:
    print("\n❌ FAC 000026 NO ENCONTRADA")
else:
    print(f"\n✓ Factura encontrada:")
    f = factura[0]
    print(f"   ID: {f['id']}")
    print(f"   Nombre: {f['name']}")
    print(f"   Tipo: {f.get('move_type')}")
    print(f"   Estado: {f.get('state')}")
    print(f"   Payment State: {f.get('payment_state')}")
    print(f"   Diario: {f.get('journal_id', [None, 'N/A'])[1]}")
    print(f"   Fecha: {f.get('date')}")
    
    # Buscar líneas de esta factura
    print("\n📋 LÍNEAS DE LA FACTURA:")
    lineas = odoo.search_read(
        'account.move.line',
        [['move_id', '=', f['id']]],
        ['id', 'product_id', 'name', 'quantity', 'credit', 'debit', 'display_type', 'account_id'],
        limit=1000
    )
    
    print(f"\n   Total líneas: {len(lineas)}")
    
    for i, linea in enumerate(lineas, 1):
        prod_id = linea.get('product_id')
        prod_name = prod_id[1] if prod_id else "Sin producto"
        account = linea.get('account_id', [None, 'N/A'])[1]
        
        print(f"\n   {i}. {prod_name[:50]}")
        print(f"      ID: {linea['id']}")
        print(f"      display_type: {linea.get('display_type')}")
        print(f"      Cuenta: {account}")
        print(f"      Cantidad: {linea.get('quantity', 0)}")
        print(f"      Credit: ${linea.get('credit', 0):,.0f}")
        print(f"      Debit: ${linea.get('debit', 0):,.0f}")
    
    # Si hay productos, verificar sus características
    productos_ids = [l.get('product_id')[0] for l in lineas if l.get('product_id')]
    
    if productos_ids:
        print("\n\n🔍 DETALLES DE PRODUCTOS:")
        productos = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'product.product', 'read',
            [list(set(productos_ids)), ['id', 'name', 'categ_id', 'type', 'active']]
        )
        
        for prod in productos:
            print(f"\n   Producto: {prod['name']}")
            print(f"      ID: {prod['id']}")
            print(f"      Categoría: {prod.get('categ_id', [None, 'N/A'])[1]}")
            print(f"      Tipo: {prod.get('type')}")
            print(f"      Activo: {prod.get('active')}")
            
            # Buscar campos Studio
            prod_full = odoo.models.execute_kw(
                odoo.db, odoo.uid, odoo.password,
                'product.product', 'read',
                [[prod['id']], ['x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo']]
            )
            
            if prod_full:
                tipo_fruta = prod_full[0].get('x_studio_sub_categora')
                manejo = prod_full[0].get('x_studio_categora_tipo_de_manejo')
                print(f"      Tipo Fruta: {tipo_fruta[1] if tipo_fruta else 'NO TIENE'}")
                print(f"      Manejo: {manejo[1] if manejo else 'NO TIENE'}")

print("\n" + "=" * 80)
