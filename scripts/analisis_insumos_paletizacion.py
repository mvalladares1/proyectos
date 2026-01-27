"""
Script de análisis para cuantificar insumos de paletización en fabricaciones históricas
Objetivo: Calcular cuánto dinero se ha gastado en insumos de paletización (cajas, pallets, etc.)
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

# Conectar a Odoo
odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*140)
print("ANÁLISIS DE INSUMOS DE PALETIZACIÓN EN FABRICACIONES HISTÓRICAS")
print("="*140)
print()

# 1. Primero explorar qué categorías existen en productos
print("🔍 Explorando categorías de productos...")
categorias = odoo.search_read(
    'product.category',
    [],
    ['id', 'name', 'complete_name', 'parent_id'],
    limit=200
)

print(f"\nTotal categorías encontradas: {len(categorias)}")
print("\nCategorías que contienen 'INSUMO', 'EMBALAJE', 'PALLET', 'CAJA':")
print("-" * 100)

categorias_insumos = []
for cat in categorias:
    nombre = cat.get('complete_name', '') or cat.get('name', '')
    if any(keyword in nombre.upper() for keyword in ['INSUMO', 'EMBALAJE', 'PALLET', 'CAJA', 'ENVASE', 'EMPAQUE']):
        categorias_insumos.append(cat)
        print(f"ID: {cat['id']:4d} | {nombre}")

print(f"\nTotal categorías de insumos identificadas: {len(categorias_insumos)}")

# 2. Obtener una muestra de órdenes de fabricación recientes para entender la estructura
print("\n" + "="*140)
print("📦 MUESTRA DE ÓRDENES DE FABRICACIÓN RECIENTES")
print("="*140)

ordenes_muestra = odoo.search_read(
    'mrp.production',
    [['state', '=', 'done'], ['date_planned_start', '>=', '2025-01-01']],
    ['id', 'name', 'product_id', 'date_planned_start', 'move_raw_ids'],
    limit=5,
    order='date_planned_start desc'
)

print(f"\nÓrdenes encontradas: {len(ordenes_muestra)}")

for orden in ordenes_muestra:
    print(f"\n--- Orden: {orden.get('name')} ---")
    print(f"Producto: {orden.get('product_id', [None, 'N/A'])[1]}")
    print(f"Fecha: {orden.get('date_planned_start')}")
    
    move_ids = orden.get('move_raw_ids', [])
    print(f"Componentes (move_raw_ids): {len(move_ids)} movimientos")
    
    if move_ids:
        # Obtener detalle de los primeros componentes
        componentes = odoo.search_read(
            'stock.move',
            [['id', 'in', move_ids[:10]]],
            ['id', 'product_id', 'product_uom_qty', 'quantity_done', 'state', 'price_unit'],
            limit=10
        )
        
        print("\nPrimeros componentes:")
        for comp in componentes:
            prod_name = comp.get('product_id', [None, 'N/A'])[1]
            qty = comp.get('quantity_done', 0) or comp.get('product_uom_qty', 0)
            precio = comp.get('price_unit', 0)
            estado = comp.get('state', 'N/A')
            print(f"  - {prod_name[:60]:60s} | {qty:10.2f} unid | ${precio:12,.0f}/u | Estado: {estado}")

# 3. Buscar productos específicos de insumos de paletización
print("\n" + "="*140)
print("🔍 BÚSQUEDA DE PRODUCTOS DE INSUMOS DE PALETIZACIÓN")
print("="*140)

# Buscar productos en categorías de insumos
cat_ids = [c['id'] for c in categorias_insumos]

productos_insumos = odoo.search_read(
    'product.product',
    [['categ_id', 'in', cat_ids], ['type', '!=', 'service']],
    ['id', 'name', 'categ_id', 'standard_price', 'list_price'],
    limit=100
)

print(f"\nProductos de insumos encontrados: {len(productos_insumos)}")
print("\nMuestra de productos:")
print("-" * 120)
print(f"{'Producto':<60s} | {'Categoría':<30s} | {'Precio Costo':>15s}")
print("-" * 120)

for prod in productos_insumos[:20]:
    nombre = prod.get('name', 'N/A')
    categoria = prod.get('categ_id', [None, 'N/A'])[1] if prod.get('categ_id') else 'N/A'
    precio = prod.get('standard_price', 0)
    print(f"{nombre[:60]:60s} | {categoria[:30]:30s} | ${precio:14,.2f}")

# 4. Ahora buscar uso de estos insumos en fabricaciones
print("\n" + "="*140)
print("💰 CONSUMO HISTÓRICO DE INSUMOS EN FABRICACIONES")
print("="*140)

producto_ids = [p['id'] for p in productos_insumos]

print(f"\nBuscando consumos de {len(producto_ids)} productos de insumos...")

# Buscar movimientos de estos productos en fabricaciones
consumos_insumos = odoo.search_read(
    'stock.move',
    [
        ['product_id', 'in', producto_ids],
        ['raw_material_production_id', '!=', False],
        ['state', '=', 'done']
    ],
    ['id', 'product_id', 'quantity_done', 'price_unit', 'raw_material_production_id', 'date'],
    limit=500,
    order='date desc'
)

print(f"Total consumos encontrados: {len(consumos_insumos)}")

# Calcular totales
total_cantidad = sum([c.get('quantity_done', 0) for c in consumos_insumos])
total_valor = sum([c.get('quantity_done', 0) * c.get('price_unit', 0) for c in consumos_insumos])

print(f"\n📊 RESUMEN:")
print(f"Total cantidad consumida: {total_cantidad:,.2f} unidades")
print(f"Total valor estimado: ${total_valor:,.0f}")

# Agrupar por producto
from collections import defaultdict
por_producto = defaultdict(lambda: {'cantidad': 0, 'valor': 0, 'nombre': '', 'usos': 0})

for consumo in consumos_insumos:
    prod_id = consumo.get('product_id', [None])[0]
    prod_name = consumo.get('product_id', [None, 'N/A'])[1]
    qty = consumo.get('quantity_done', 0)
    precio = consumo.get('price_unit', 0)
    
    por_producto[prod_id]['nombre'] = prod_name
    por_producto[prod_id]['cantidad'] += qty
    por_producto[prod_id]['valor'] += qty * precio
    por_producto[prod_id]['usos'] += 1

print("\n" + "="*140)
print("📦 TOP 20 INSUMOS MÁS UTILIZADOS")
print("="*140)
print(f"{'Producto':<60s} | {'Cantidad':>12s} | {'Valor Total':>18s} | {'Usos':>6s}")
print("-" * 140)

top_productos = sorted(por_producto.values(), key=lambda x: x['valor'], reverse=True)[:20]

for prod in top_productos:
    print(f"{prod['nombre'][:60]:60s} | {prod['cantidad']:12,.2f} | ${prod['valor']:17,.0f} | {prod['usos']:6,d}")

print("\n" + "="*140)
print("✅ ANÁLISIS COMPLETADO")
print("="*140)
print(f"\nSiguiente paso: Generar Excel con detalle completo por año, producto y fabricación")
