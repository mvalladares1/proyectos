"""
Investigar FAC 000115 - Factura que no debería estar (semillas de hortalizas)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*100)
print("INVESTIGACIÓN: FAC 000115 (Semillas de hortalizas)")
print("="*100)

# Buscar la factura
moves = odoo.search_read(
    'account.move',
    [['name', '=', 'FAC 000115']],
    ['id', 'name', 'date', 'state', 'payment_state', 'journal_id', 'move_type', 'partner_id'],
    limit=1
)

if not moves:
    print("❌ Factura no encontrada")
    exit(1)

move = moves[0]
print(f"\n📄 FACTURA: {move['name']}")
print(f"   ID: {move['id']}")
print(f"   Fecha: {move.get('date')}")
print(f"   Cliente: {move.get('partner_id', [None, 'N/A'])[1]}")
print(f"   Tipo: {move.get('move_type')}")
print(f"   Estado: {move.get('state')}")
print(f"   Diario: {move.get('journal_id', [None, 'N/A'])[1]}")

# Buscar líneas
lineas = odoo.search_read(
    'account.move.line',
    [
        ['move_id', '=', move['id']],
        ['display_type', '=', 'product']
    ],
    ['id', 'product_id', 'name', 'quantity', 'credit', 'debit', 'account_id'],
    limit=10
)

print(f"\n📦 LÍNEAS DE PRODUCTO: {len(lineas)}")

for i, linea in enumerate(lineas, 1):
    print(f"\n   Línea {i}:")
    
    producto_info = linea.get('product_id')
    if isinstance(producto_info, (list, tuple)) and len(producto_info) > 0:
        producto_id = producto_info[0]
        producto_nombre = producto_info[1]
    elif isinstance(producto_info, bool) and not producto_info:
        producto_id = None
        producto_nombre = None
    else:
        producto_id = producto_info
        producto_nombre = None
    
    descripcion = linea.get('name', 'N/A')
    cantidad = linea.get('quantity', 0)
    cuenta = linea.get('account_id', [None, 'N/A'])[1]
    valor = linea.get('credit', 0) - linea.get('debit', 0)
    
    print(f"     Descripción: {descripcion}")
    print(f"     Cantidad: {cantidad:,.2f}")
    print(f"     Valor: ${valor:,.0f}")
    print(f"     Cuenta: {cuenta}")
    
    if producto_id:
        # Obtener info del producto
        producto = odoo.search_read(
            'product.product',
            [['id', '=', producto_id]],
            ['id', 'name', 'default_code', 'categ_id', 'product_tmpl_id', 'type', 'active'],
            limit=1
        )
        
        if producto:
            prod = producto[0]
            categoria_id = prod.get('categ_id', [None])[0]
            categoria_nombre = prod.get('categ_id', [None, 'N/A'])[1]
            
            print(f"     ✅ TIENE PRODUCTO:")
            print(f"        - ID: {producto_id}")
            print(f"        - Nombre: {prod.get('name', 'N/A')}")
            print(f"        - Código: {prod.get('default_code', 'N/A')}")
            print(f"        - Tipo: {prod.get('type', 'N/A')}")
            print(f"        - Activo: {prod.get('active', 'N/A')}")
            print(f"        - Categoría: {categoria_nombre}")
            
            # Obtener categoría completa
            if categoria_id:
                categoria = odoo.search_read(
                    'product.category',
                    [['id', '=', categoria_id]],
                    ['id', 'name', 'complete_name', 'parent_id'],
                    limit=1
                )
                
                if categoria:
                    cat = categoria[0]
                    complete_name = cat.get('complete_name', 'N/A')
                    
                    print(f"        - Categoría completa: {complete_name}")
                    print(f"        - ¿Incluye 'PRODUCTOS'?: {'✅ SÍ' if 'PRODUCTOS' in complete_name.upper() else '❌ NO'}")
                    
                    # Verificar si pasa el filtro actual
                    print(f"\n     🔍 ANÁLISIS DE FILTROS:")
                    print(f"        1. product_id != False: ✅ SÍ (tiene producto {producto_id})")
                    print(f"        2. categ_id ilike 'PRODUCTOS': {'✅ SÍ - PASA FILTRO' if 'PRODUCTOS' in complete_name.upper() else '❌ NO - DEBERÍA EXCLUIRSE'}")
                    print(f"        3. type != 'service': {'✅ SÍ' if prod.get('type') != 'service' else '❌ NO'}")
    else:
        print(f"     ⚠️ TEXTO LIBRE (sin producto)")
        print(f"\n     🔍 ANÁLISIS DE FILTROS:")
        print(f"        1. product_id = False: ✅ SÍ (texto libre)")
        print(f"        2. Longitud descripción: {len(descripcion)} caracteres")
        print(f"        3. ¿Empieza con keyword?: {any(descripcion.upper().startswith(kw) for kw in ['FLETE', 'TERMOGRAFO', 'PALLET', 'ARRENDAMIENTO', 'SERVOCOP', 'TRACTOR', 'FIERRO'])}")

print("\n" + "="*100)
print("✅ INVESTIGACIÓN COMPLETADA")
print("="*100)
