"""
Script de diagnóstico para analizar órdenes de producción
Verifica por qué el rendimiento sale > 100%
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*140)
print("DIAGNÓSTICO: RENDIMIENTOS DE PRODUCCIÓN")
print("="*140)

# 1. Obtener órdenes del período
ordenes = odoo.search_read(
    'mrp.production',
    [
        ['date_planned_start', '>=', '2025-11-01'],
        ['date_planned_start', '<=', '2026-01-31'],
        ['state', 'in', ['done', 'progress']]
    ],
    ['id', 'name', 'product_id', 'product_qty', 'date_planned_start', 'state'],
    limit=10
)

print(f"\n✓ Órdenes encontradas: {len(ordenes)}")

if not ordenes:
    print("No hay órdenes en el período")
    sys.exit(0)

# Analizar primera orden en detalle
orden = ordenes[0]
orden_id = orden['id']

print(f"\n" + "="*140)
print(f"ANÁLISIS DETALLADO - ORDEN: {orden['name']}")
print("="*140)
print(f"ID: {orden_id}")
print(f"Producto Final: {orden.get('product_id', [None, 'N/A'])[1] if orden.get('product_id') else 'N/A'}")
print(f"Cantidad Planificada: {orden.get('product_qty', 0)}")
print(f"Fecha: {orden.get('date_planned_start', '')}")
print(f"Estado: {orden.get('state', '')}")

# 2. Obtener consumos (MP que entró)
print(f"\n" + "-"*140)
print("CONSUMOS DE MATERIA PRIMA (raw_material_production_id)")
print("-"*140)

consumos = odoo.search_read(
    'stock.move',
    [
        ['raw_material_production_id', '=', orden_id],
        ['state', '=', 'done']
    ],
    ['id', 'product_id', 'product_uom_qty', 'quantity_done', 'location_id', 'location_dest_id', 'reference'],
    limit=100
)

print(f"Total movimientos de consumo: {len(consumos)}")

total_consumo = 0
for i, mov in enumerate(consumos):
    prod_name = mov.get('product_id', [None, 'N/A'])[1] if mov.get('product_id') else 'N/A'
    qty_planned = mov.get('product_uom_qty', 0)
    qty_done = mov.get('quantity_done', 0)
    loc_from = mov.get('location_id', [None, 'N/A'])[1] if mov.get('location_id') else 'N/A'
    loc_to = mov.get('location_dest_id', [None, 'N/A'])[1] if mov.get('location_dest_id') else 'N/A'
    
    print(f"\n{i+1}. {prod_name}")
    print(f"   Planificado: {qty_planned} | Realizado: {qty_done}")
    print(f"   Origen: {loc_from}")
    print(f"   Destino: {loc_to}")
    
    total_consumo += qty_done

print(f"\n{'='*140}")
print(f"TOTAL CONSUMIDO: {total_consumo:,.2f} kg")
print(f"{'='*140}")

# 3. Obtener producciones (PT que salió)
print(f"\n" + "-"*140)
print("PRODUCCIÓN DE PRODUCTO TERMINADO (production_id)")
print("-"*140)

producciones = odoo.search_read(
    'stock.move',
    [
        ['production_id', '=', orden_id],
        ['state', '=', 'done']
    ],
    ['id', 'product_id', 'product_uom_qty', 'quantity_done', 'location_id', 'location_dest_id', 'reference'],
    limit=100
)

print(f"Total movimientos de producción: {len(producciones)}")

total_producido = 0
for i, mov in enumerate(producciones):
    prod_name = mov.get('product_id', [None, 'N/A'])[1] if mov.get('product_id') else 'N/A'
    qty_planned = mov.get('product_uom_qty', 0)
    qty_done = mov.get('quantity_done', 0)
    loc_from = mov.get('location_id', [None, 'N/A'])[1] if mov.get('location_id') else 'N/A'
    loc_to = mov.get('location_dest_id', [None, 'N/A'])[1] if mov.get('location_dest_id') else 'N/A'
    
    print(f"\n{i+1}. {prod_name}")
    print(f"   Planificado: {qty_planned} | Realizado: {qty_done}")
    print(f"   Origen: {loc_from}")
    print(f"   Destino: {loc_to}")
    
    total_producido += qty_done

print(f"\n{'='*140}")
print(f"TOTAL PRODUCIDO: {total_producido:,.2f} kg")
print(f"{'='*140}")

# 4. Calcular rendimiento
print(f"\n" + "="*140)
print("CÁLCULO DE RENDIMIENTO")
print("="*140)

if total_consumo > 0:
    rendimiento = (total_producido / total_consumo) * 100
    merma = total_consumo - total_producido
    merma_pct = (merma / total_consumo) * 100
    
    print(f"Consumo MP:     {total_consumo:>15,.2f} kg")
    print(f"Producción PT:  {total_producido:>15,.2f} kg")
    print(f"Merma:          {merma:>15,.2f} kg ({merma_pct:+.1f}%)")
    print(f"Rendimiento:    {rendimiento:>15.1f}%")
    
    if rendimiento > 100:
        print(f"\n⚠️  PROBLEMA: Rendimiento > 100% es imposible!")
        print(f"   Posibles causas:")
        print(f"   1. Los movimientos están invertidos (consumo ↔ producción)")
        print(f"   2. Hay movimientos duplicados")
        print(f"   3. Las ubicaciones están mal (stock.move puede tener dirección inversa)")
        print(f"   4. Falta filtro por tipo de movimiento")
else:
    print("No hay consumo registrado")

# 5. Verificar todas las órdenes del período
print(f"\n" + "="*140)
print("RESUMEN DE TODAS LAS ÓRDENES")
print("="*140)

orden_ids = [o['id'] for o in ordenes]

# Consumos totales
consumos_todos = odoo.search_read(
    'stock.move',
    [
        ['raw_material_production_id', 'in', orden_ids],
        ['state', '=', 'done']
    ],
    ['quantity_done'],
    limit=50000
)

# Producciones totales
producciones_todas = odoo.search_read(
    'stock.move',
    [
        ['production_id', 'in', orden_ids],
        ['state', '=', 'done']
    ],
    ['quantity_done'],
    limit=50000
)

total_consumo_general = sum([c.get('quantity_done', 0) for c in consumos_todos])
total_producido_general = sum([p.get('quantity_done', 0) for p in producciones_todas])

print(f"\nÓrdenes analizadas: {len(ordenes)}")
print(f"Movimientos de consumo: {len(consumos_todos)}")
print(f"Movimientos de producción: {len(producciones_todas)}")
print(f"\nConsumo total MP: {total_consumo_general:,.2f} kg")
print(f"Producción total PT: {total_producido_general:,.2f} kg")

if total_consumo_general > 0:
    rend_general = (total_producido_general / total_consumo_general) * 100
    print(f"Rendimiento general: {rend_general:.1f}%")
    
    if rend_general > 100:
        print(f"\n⚠️  CONFIRMADO: El rendimiento general también es > 100%")
        print(f"\n🔍 HIPÓTESIS PRINCIPAL:")
        print(f"   Los campos 'raw_material_production_id' y 'production_id' pueden estar")
        print(f"   invertidos o mal interpretados en el modelo de datos de Odoo.")
        print(f"\n💡 SOLUCIÓN SUGERIDA:")
        print(f"   Invertir el uso de los campos o verificar la estructura del modelo MRP")

print(f"\n" + "="*140)
print("FIN DEL DIAGNÓSTICO")
print("="*140)
