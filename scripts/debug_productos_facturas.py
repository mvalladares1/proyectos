"""
Debug: Ver por qué los productos de facturas no tienen campos x_studio
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 140)
print("DEBUG: PRODUCTOS DESDE FACTURAS VS PRODUCTOS DIRECTOS")
print("=" * 140)

odoo = OdooClient(username=USERNAME, password=PASSWORD)

# Obtener algunas líneas de factura de 2026
lineas = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'in_invoice'],
        ['move_id.state', '=', 'posted'],
        ['product_id', '!=', False],
        ['date', '>=', '2026-01-01'],
        ['date', '<=', '2026-01-31'],
        ['quantity', '>', 0],
        ['debit', '>', 0]
    ],
    ['product_id', 'quantity', 'debit'],
    limit=10
)

print(f"\n{'─' * 140}")
print(f"Líneas de factura encontradas: {len(lineas)}")
print("─" * 140)

if lineas:
    # Extraer IDs de productos
    prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas if l.get('product_id')]))
    
    print(f"\nProductos únicos en facturas: {len(prod_ids)}")
    print(f"IDs: {prod_ids[:5]}...")
    
    # MÉTODO 1: Buscar productos CON campos específicos
    print(f"\n{'=' * 140}")
    print("MÉTODO 1: search_read CON campos específicos")
    print("=" * 140)
    
    productos_metodo1 = odoo.search_read(
        'product.product',
        [['id', 'in', prod_ids]],
        ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo', 'categ_id'],
        limit=100
    )
    
    print(f"\nProductos obtenidos: {len(productos_metodo1)}")
    
    for i, prod in enumerate(productos_metodo1[:3]):
        print(f"\n  Producto {i+1}:")
        print(f"    ID: {prod.get('id')}")
        print(f"    Nombre: {prod.get('name', 'Sin nombre')[:50]}")
        
        categ = prod.get('categ_id')
        categ_str = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
        print(f"    Categoría: {categ_str}")
        
        tipo = prod.get('x_studio_sub_categora')
        print(f"    x_studio_sub_categora RAW: {tipo}")
        print(f"    x_studio_sub_categora TYPE: {type(tipo)}")
        
        if isinstance(tipo, (list, tuple)):
            if len(tipo) > 1:
                print(f"    x_studio_sub_categora VALUE: {tipo[1]}")
            else:
                print(f"    x_studio_sub_categora VALUE: LISTA VACÍA o de 1 elemento")
        elif tipo:
            print(f"    x_studio_sub_categora VALUE: {tipo}")
        else:
            print(f"    x_studio_sub_categora VALUE: VACÍO (False/None)")
        
        manejo = prod.get('x_studio_categora_tipo_de_manejo')
        print(f"    x_studio_categora_tipo_de_manejo RAW: {manejo}")
        print(f"    x_studio_categora_tipo_de_manejo TYPE: {type(manejo)}")
        
        if isinstance(manejo, str):
            print(f"    x_studio_categora_tipo_de_manejo VALUE: '{manejo}'")
        elif manejo:
            print(f"    x_studio_categora_tipo_de_manejo VALUE: {manejo}")
        else:
            print(f"    x_studio_categora_tipo_de_manejo VALUE: VACÍO (False/None)")
    
    # MÉTODO 2: Buscar productos SIN especificar campos (todos los campos)
    print(f"\n{'=' * 140}")
    print("MÉTODO 2: search_read SIN campos específicos (todos)")
    print("=" * 140)
    
    productos_metodo2 = odoo.search_read(
        'product.product',
        [['id', '=', prod_ids[0]]],  # Solo el primer producto
        [],  # Sin campos = todos
        limit=1
    )
    
    if productos_metodo2:
        prod = productos_metodo2[0]
        print(f"\nProducto ID {prod.get('id')}:")
        print(f"\nCampos x_studio encontrados:")
        
        for campo, valor in sorted(prod.items()):
            if campo.startswith('x_studio'):
                if isinstance(valor, (list, tuple)) and len(valor) > 1:
                    valor_mostrar = f"{valor[1]} (ID: {valor[0]})"
                elif isinstance(valor, str) and valor:
                    valor_mostrar = f"'{valor}'"
                elif valor:
                    valor_mostrar = str(valor)
                else:
                    valor_mostrar = "❌ VACÍO"
                
                print(f"  {campo:50s} = {valor_mostrar}")

print(f"\n{'=' * 140}")
