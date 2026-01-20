"""
Debug: Explorar campos de productos para Stock Teórico
Encuentra los campos reales de tipo de fruta y manejo
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 140)
print("EXPLORACIÓN DE CAMPOS DE PRODUCTOS")
print("=" * 140)

odoo = OdooClient(username=USERNAME, password=PASSWORD)

# Obtener un producto de cada categoría relevante
categorias_buscar = [
    'PRODUCTOS / MP',
    'PRODUCTOS / PSP',
    'PRODUCTOS / PTT',
    'PRODUCTOS / RETAIL'
]

for categoria in categorias_buscar:
    print(f"\n{'=' * 140}")
    print(f"CATEGORÍA: {categoria}")
    print("=" * 140)
    
    # Buscar productos de esta categoría
    productos = odoo.search_read(
        'product.product',
        [['categ_id', 'ilike', categoria]],
        [],  # Sin especificar campos = trae TODOS
        limit=1
    )
    
    if not productos:
        print(f"  ⚠️ No se encontraron productos en esta categoría")
        continue
    
    producto = productos[0]
    
    print(f"\n  Producto ejemplo: {producto.get('name', 'Sin nombre')} (ID: {producto.get('id')})")
    print(f"\n  TODOS LOS CAMPOS Y SUS VALORES:")
    print(f"  {'-' * 136}")
    
    # Ordenar campos alfabéticamente
    campos_ordenados = sorted(producto.items())
    
    for campo, valor in campos_ordenados:
        # Filtrar campos que podrían ser relevantes
        if any(keyword in campo.lower() for keyword in ['tipo', 'fruta', 'manejo', 'categ', 'studio', 'sub', 'clasif']):
            # Formatear valor
            if isinstance(valor, (list, tuple)) and len(valor) > 1:
                valor_mostrar = f"{valor[1]} (ID: {valor[0]})"
            elif isinstance(valor, bool):
                valor_mostrar = "✓" if valor else "✗"
            elif valor is False or valor is None or valor == '':
                valor_mostrar = "❌ VACÍO"
            else:
                valor_mostrar = str(valor)
            
            print(f"  📌 {campo:50s} = {valor_mostrar}")

print(f"\n{'=' * 140}")
print("BÚSQUEDA DE CAMPOS x_studio")
print("=" * 140)

# Buscar todos los campos que empiecen con x_studio
productos_muestra = odoo.search_read(
    'product.product',
    [],
    [],
    limit=10
)

if productos_muestra:
    campos_studio = set()
    
    for prod in productos_muestra:
        for campo in prod.keys():
            if campo.startswith('x_studio'):
                campos_studio.add(campo)
    
    print(f"\n  Campos x_studio encontrados ({len(campos_studio)}):")
    for campo in sorted(campos_studio):
        print(f"    - {campo}")
    
    # Mostrar valores de un producto para cada campo
    if campos_studio:
        print(f"\n  Valores de ejemplo (primer producto):")
        prod_ejemplo = productos_muestra[0]
        for campo in sorted(campos_studio):
            valor = prod_ejemplo.get(campo)
            if isinstance(valor, (list, tuple)) and len(valor) > 1:
                valor_mostrar = f"{valor[1]} (ID: {valor[0]})"
            elif valor:
                valor_mostrar = str(valor)
            else:
                valor_mostrar = "❌ VACÍO"
            print(f"    {campo:50s} = {valor_mostrar}")

print(f"\n{'=' * 140}")
