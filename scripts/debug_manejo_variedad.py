"""
Debug: Ver categorías de manejo y tipos de fruta en productos
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

def main():
    odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")
    
    print("="*100)
    print("CATEGORÍAS DE MANEJO Y TIPOS DE FRUTA")
    print("="*100)
    
    # 1. Buscar productos de fruta (que tengan código 4* o 1*)
    productos = odoo.search_read(
        'product.product',
        [
            '|',
            ['default_code', '=like', '4%'],
            ['default_code', '=like', '1%']
        ],
        ['name', 'default_code', 'categ_id', 'x_studio_categora_tipo_de_manejo', 'x_studio_sub_categora'],
        limit=100
    )
    
    print(f"\nProductos encontrados: {len(productos)}")
    
    # Ver categorías de manejo y tipos de fruta únicos
    manejos = set()
    tipos_fruta = set()
    
    print("\n" + "="*100)
    print("PRODUCTOS CON MANEJO Y TIPO DE FRUTA")
    print("="*100)
    
    productos_con_datos = []
    for prod in productos:
        manejo = prod.get('x_studio_categora_tipo_de_manejo')
        tipo_fruta = prod.get('x_studio_sub_categora')
        
        if manejo:
            if isinstance(manejo, (list, tuple)):
                manejos.add(manejo[1])
                manejo_str = manejo[1]
            else:
                manejos.add(str(manejo))
                manejo_str = str(manejo)
        else:
            manejo_str = "Sin manejo"
        
        if tipo_fruta:
            if isinstance(tipo_fruta, (list, tuple)):
                tipos_fruta.add(tipo_fruta[1])
                tipo_fruta_str = tipo_fruta[1]
            else:
                tipos_fruta.add(str(tipo_fruta))
                tipo_fruta_str = str(tipo_fruta)
        else:
            tipo_fruta_str = "Sin tipo fruta"
        
        if manejo or tipo_fruta:
            productos_con_datos.append({
                'codigo': prod.get('default_code', ''),
                'nombre': prod.get('name', ''),
                'manejo': manejo_str,
                'tipo_fruta': tipo_fruta_str,
                'categoria': prod.get('categ_id', [None, ''])[1] if prod.get('categ_id') else ''
            })
    
    print(f"\nProductos con datos de manejo/tipo fruta: {len(productos_con_datos)}")
    print("\nEjemplos:")
    for prod in productos_con_datos[:15]:
        print(f"\n  [{prod['codigo']}] {prod['nombre'][:60]}")
        print(f"    Manejo: {prod['manejo']}")
        print(f"    Tipo Fruta: {prod['tipo_fruta']}")
        print(f"    Categoría: {prod['categoria']}")
    
    # 2. Buscar los valores posibles del campo de manejo
    print("\n" + "="*100)
    print("VALORES DE CATEGORÍA DE MANEJO")
    print("="*100)
    
    # Intentar buscar el modelo de selección
    try:
        manejos_records = odoo.search_read(
            'x_categora_tipo_de_manejo',
            [],
            ['name'],
            limit=50
        )
        print(f"\nCategorías de manejo encontradas: {len(manejos_records)}")
        for manejo in manejos_records:
            print(f"  - {manejo.get('name')}")
    except:
        print("\nNo se pudo acceder al modelo x_categora_tipo_de_manejo")
        print("Manejos encontrados en productos:")
        for m in sorted(manejos):
            print(f"  - {m}")
    
    # 3. Buscar tipos de fruta
    print("\n" + "="*100)
    print("VALORES DE TIPO DE FRUTA (x_studio_sub_categora)")
    print("="*100)
    
    try:
        tipos_records = odoo.search_read(
            'x_sub_categora',
            [],
            ['name'],
            limit=50
        )
        print(f"\nTipos de fruta encontrados: {len(tipos_records)}")
        for tipo in tipos_records:
            print(f"  - {tipo.get('name')}")
    except:
        print("\nNo se pudo acceder al modelo x_sub_categora")
        print("Tipos encontrados en productos:")
        for t in sorted(tipos_fruta):
            print(f"  - {t}")
    
    # 4. Ver líneas de factura con estos productos en 2025
    print("\n" + "="*100)
    print("ANÁLISIS DE COMPRAS Y VENTAS 2025")
    print("="*100)
    
    if productos_con_datos:
        # Obtener IDs de productos
        prod_ids = [p['codigo'] for p in productos_con_datos if p['codigo']]
        
        # Buscar líneas de factura
        lineas = odoo.search_read(
            'account.move.line',
            [
                ['product_id.default_code', 'in', prod_ids[:20]],  # Limitar para test
                ['move_id.move_type', 'in', ['in_invoice', 'out_invoice']],
                ['move_id.state', '=', 'posted'],
                ['date', '>=', '2025-01-01'],
                ['date', '<=', '2025-12-31']
            ],
            ['product_id', 'quantity', 'move_id', 'date'],
            limit=50
        )
        
        print(f"\nLíneas de factura encontradas: {len(lineas)}")
        
        # Agrupar por producto
        resumen = {}
        for linea in lineas:
            prod_id = linea.get('product_id', [None])[0]
            prod_nombre = linea.get('product_id', [None, 'Sin nombre'])[1]
            cantidad = linea.get('quantity', 0)
            
            if prod_id:
                if prod_id not in resumen:
                    resumen[prod_id] = {
                        'nombre': prod_nombre,
                        'cantidad': 0
                    }
                resumen[prod_id]['cantidad'] += cantidad
        
        print(f"\nResumen por producto:")
        for prod_id, data in sorted(resumen.items(), key=lambda x: abs(x[1]['cantidad']), reverse=True)[:10]:
            print(f"  {data['nombre'][:70]}: {data['cantidad']:,.2f}")

if __name__ == "__main__":
    main()
