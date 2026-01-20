"""
Probar que los filtros de categorías funcionan correctamente
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*140)
print("TEST: FILTROS DE CATEGORÍAS EN PRODUCCIÓN")
print("="*140)

# Obtener una orden de ejemplo
orden = odoo.search_read(
    'mrp.production',
    [
        ['name', '=', 'WH/RF/MOV/RETAIL/00765']  # La que tenía 15k kg de insumos
    ],
    ['id', 'name'],
    limit=1
)[0]

orden_id = orden['id']
print(f"\n📦 ORDEN: {orden['name']} (ID: {orden_id})")
print("="*140)

# Obtener TODOS los consumos
consumos_todos = odoo.search_read(
    'stock.move',
    [
        ['raw_material_production_id', '=', orden_id],
        ['state', '=', 'done']
    ],
    ['product_id', 'quantity_done'],
    limit=100
)

print(f"\n🔍 CONSUMOS TOTALES: {len(consumos_todos)} movimientos")

# Obtener detalles de productos
prod_ids = [c.get('product_id', [None])[0] for c in consumos_todos if c.get('product_id')]
productos = odoo.search_read(
    'product.product',
    [['id', 'in', prod_ids]],
    ['id', 'name', 'categ_id'],
    limit=100
)

productos_map = {}
for p in productos:
    categ = p.get('categ_id')
    categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
    productos_map[p['id']] = {
        'nombre': p['name'],
        'categoria': categ_name
    }

# Analizar categorías
print(f"\n{'='*140}")
print(f"{'PRODUCTO':<60} {'CATEGORÍA':<40} {'KG':>10} {'INCLUIR':>10}")
print(f"{'='*140}")

total_sin_filtro = 0
total_con_filtro = 0
insumos_excluidos = 0

for consumo in consumos_todos:
    prod_id = consumo.get('product_id', [None])[0]
    if not prod_id or prod_id not in productos_map:
        continue
    
    kg = consumo.get('quantity_done', 0)
    producto = productos_map[prod_id]['nombre'][:60]
    categoria = productos_map[prod_id]['categoria'][:40]
    
    total_sin_filtro += kg
    
    # Aplicar filtro
    incluir = True
    if 'INSUMOS' in categoria.upper() or 'EMBALAJE' in categoria.upper():
        incluir = False
        insumos_excluidos += kg
    else:
        total_con_filtro += kg
    
    print(f"{producto:<60} {categoria:<40} {kg:>10.2f} {'✅ SÍ' if incluir else '❌ NO':>10}")

print(f"{'='*140}")
print(f"\n📊 RESULTADOS:")
print(f"   Total SIN filtro: {total_sin_filtro:,.2f} kg")
print(f"   Total CON filtro: {total_con_filtro:,.2f} kg")
print(f"   Insumos excluidos: {insumos_excluidos:,.2f} kg ({insumos_excluidos/total_sin_filtro*100:.1f}%)")

# Obtener producciones
print(f"\n{'='*140}")
print(f"PRODUCCIONES")
print(f"{'='*140}")

producciones = odoo.search_read(
    'stock.move',
    [
        ['production_id', '=', orden_id],
        ['state', '=', 'done']
    ],
    ['product_id', 'quantity_done'],
    limit=100
)

print(f"\n🏭 PRODUCCIONES TOTALES: {len(producciones)} movimientos")

# Obtener detalles
prod_ids_out = [p.get('product_id', [None])[0] for p in producciones if p.get('product_id')]
productos_out = odoo.search_read(
    'product.product',
    [['id', 'in', prod_ids_out]],
    ['id', 'name', 'categ_id'],
    limit=100
)

productos_out_map = {}
for p in productos_out:
    categ = p.get('categ_id')
    categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
    productos_out_map[p['id']] = {
        'nombre': p['name'],
        'categoria': categ_name
    }

print(f"\n{'='*140}")
print(f"{'PRODUCTO':<60} {'CATEGORÍA':<40} {'KG':>10} {'INCLUIR':>10}")
print(f"{'='*140}")

total_producido_sin_filtro = 0
total_producido_con_filtro = 0
mermas_excluidas = 0

for prod in producciones:
    prod_id = prod.get('product_id', [None])[0]
    if not prod_id or prod_id not in productos_out_map:
        continue
    
    kg = prod.get('quantity_done', 0)
    producto = productos_out_map[prod_id]['nombre'][:60]
    categoria = productos_out_map[prod_id]['categoria'][:40]
    
    total_producido_sin_filtro += kg
    
    # Aplicar filtro
    incluir = True
    if producto.upper().startswith('PROCESO ') or 'MERMA' in producto.upper():
        incluir = False
        mermas_excluidas += kg
    else:
        total_producido_con_filtro += kg
    
    print(f"{producto:<60} {categoria:<40} {kg:>10.2f} {'✅ SÍ' if incluir else '❌ NO':>10}")

print(f"{'='*140}")
print(f"\n📊 RESULTADOS:")
print(f"   Total SIN filtro: {total_producido_sin_filtro:,.2f} kg")
print(f"   Total CON filtro: {total_producido_con_filtro:,.2f} kg")
print(f"   Mermas excluidas: {mermas_excluidas:,.2f} kg ({mermas_excluidas/total_producido_sin_filtro*100:.1f}%)")

# Cálculo final
print(f"\n{'='*140}")
print(f"RENDIMIENTO CALCULADO")
print(f"{'='*140}")

if total_sin_filtro > 0:
    rend_sin_filtro = (total_producido_sin_filtro / total_sin_filtro) * 100
    print(f"\n❌ SIN FILTROS:")
    print(f"   Consumo: {total_sin_filtro:,.2f} kg")
    print(f"   Producción: {total_producido_sin_filtro:,.2f} kg")
    print(f"   Rendimiento: {rend_sin_filtro:.1f}%")

if total_con_filtro > 0:
    rend_con_filtro = (total_producido_con_filtro / total_con_filtro) * 100
    print(f"\n✅ CON FILTROS:")
    print(f"   Consumo (sin insumos): {total_con_filtro:,.2f} kg")
    print(f"   Producción (sin mermas): {total_producido_con_filtro:,.2f} kg")
    print(f"   Rendimiento: {rend_con_filtro:.1f}%")
    
    if 70 <= rend_con_filtro <= 100:
        print(f"   ✅ RENDIMIENTO LÓGICO (70-100%)")
    else:
        print(f"   ⚠️ RENDIMIENTO FUERA DE RANGO")

print(f"\n{'='*140}")
