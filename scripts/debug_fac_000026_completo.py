import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(username=USERNAME, password=PASSWORD)

print("=" * 80)
print("BÚSQUEDA EXHAUSTIVA - FAC 000026")
print("=" * 80)

# Buscar TODAS las facturas con ese nombre (pueden haber múltiples)
facturas = odoo.search_read(
    'account.move',
    [['name', 'ilike', 'FAC 000026']],
    ['id', 'name', 'move_type', 'state', 'payment_state', 'journal_id', 'date', 'partner_id'],
    limit=100
)

print(f"\n✓ Facturas encontradas: {len(facturas)}")

for i, f in enumerate(facturas, 1):
    print(f"\n{'=' * 80}")
    print(f"FACTURA #{i}: {f['name']}")
    print(f"{'=' * 80}")
    print(f"   ID: {f['id']}")
    print(f"   Tipo: {f.get('move_type')}")
    print(f"   Estado: {f.get('state')}")
    print(f"   Payment State: {f.get('payment_state')}")
    print(f"   Diario: {f.get('journal_id', [None, 'N/A'])[1]}")
    print(f"   Fecha: {f.get('date')}")
    print(f"   Cliente: {f.get('partner_id', [None, 'N/A'])[1]}")
    
    # Si es out_invoice (factura de venta), verificar por qué no aparece
    if f.get('move_type') == 'out_invoice':
        print(f"\n   ⚠️ ESTA ES FACTURA DE VENTA - Verificando filtros:")
        
        # Test 1: Buscar sus líneas
        lineas_todas = odoo.search_read(
            'account.move.line',
            [
                ['move_id', '=', f['id']],
                ['product_id', '!=', False]
            ],
            ['id', 'product_id', 'display_type', 'quantity', 'credit', 'debit'],
            limit=1000
        )
        print(f"      Total líneas con producto: {len(lineas_todas)}")
        
        # Test 2: Con categoría PRODUCTOS
        lineas_productos = odoo.search_read(
            'account.move.line',
            [
                ['move_id', '=', f['id']],
                ['product_id', '!=', False],
                ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS']
            ],
            ['id', 'product_id', 'display_type'],
            limit=1000
        )
        print(f"      Líneas con categoría PRODUCTOS: {len(lineas_productos)}")
        
        # Test 3: Con display_type product
        lineas_display = odoo.search_read(
            'account.move.line',
            [
                ['move_id', '=', f['id']],
                ['product_id', '!=', False],
                ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
                ['display_type', '=', 'product']
            ],
            ['id', 'product_id'],
            limit=1000
        )
        print(f"      Líneas con display_type='product': {len(lineas_display)}")
        
        # Mostrar detalles de las líneas
        if lineas_todas:
            print(f"\n   📋 DETALLES DE LÍNEAS:")
            for linea in lineas_todas[:5]:
                prod_id = linea.get('product_id')
                print(f"      - {prod_id[1] if prod_id else 'Sin nombre'}")
                print(f"        display_type: {linea.get('display_type')}")
                print(f"        cantidad: {linea.get('quantity', 0)}")
                
                # Buscar categoría del producto
                if prod_id:
                    prod = odoo.models.execute_kw(
                        odoo.db, odoo.uid, odoo.password,
                        'product.product', 'read',
                        [[prod_id[0]], ['categ_id', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo']]
                    )
                    if prod:
                        categ = prod[0].get('categ_id', [None, 'N/A'])[1]
                        tipo_fruta = prod[0].get('x_studio_sub_categora')
                        manejo = prod[0].get('x_studio_categora_tipo_de_manejo')
                        print(f"        categoría: {categ}")
                        print(f"        tipo_fruta: {tipo_fruta[1] if tipo_fruta else 'NO TIENE'}")
                        print(f"        manejo: {manejo[1] if manejo else 'NO TIENE'}")

print("\n" + "=" * 80)
