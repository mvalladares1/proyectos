"""
Exploración de análisis correctos que SÍ podemos hacer
con los datos disponibles en Odoo
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*140)
print("EXPLORACIÓN: ANÁLISIS CORRECTOS QUE PODEMOS IMPLEMENTAR")
print("="*140)

# =======================================================================================
# OPCIÓN 1: ANÁLISIS DE COMPRAS (MP/PSP) - AISLADO
# =======================================================================================
print("\n" + "="*140)
print("✅ OPCIÓN 1: ANÁLISIS DE COMPRAS DE MATERIA PRIMA")
print("="*140)

print("""
OBJETIVO: Analizar comportamiento de compras de frutas (PSP/MP)
MÉTRICAS VÁLIDAS:
  - Volumen comprado por tipo de fruta y manejo
  - Precio promedio por kg (tendencias)
  - Distribución por proveedor
  - Estacionalidad de compras
  - Comparación período vs período anterior
  
VISUALIZACIONES:
  - Serie temporal de precios
  - Distribución por categoría
  - Top proveedores
  - Variación mensual de precios
""")

# Verificar datos disponibles
compras_sample = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'in_invoice'],
        ['move_id.state', '=', 'posted'],
        ['product_id', '!=', False],
        ['date', '>=', '2025-11-01'],
        ['quantity', '>', 0],
        ['debit', '>', 0],
        ['account_id.code', '=like', '21%']
    ],
    ['product_id', 'quantity', 'debit', 'date', 'move_id', 'partner_id'],
    limit=5
)

print(f"\n✓ Datos disponibles: {len(compras_sample)} líneas de muestra")
print(f"  Campos: {list(compras_sample[0].keys()) if compras_sample else 'N/A'}")

# =======================================================================================
# OPCIÓN 2: ANÁLISIS DE VENTAS (PTT) - AISLADO
# =======================================================================================
print("\n" + "="*140)
print("✅ OPCIÓN 2: ANÁLISIS DE VENTAS DE PRODUCTOS TERMINADOS")
print("="*140)

print("""
OBJETIVO: Analizar comportamiento de ventas de PT
MÉTRICAS VÁLIDAS:
  - Volumen vendido por producto y categoría
  - Precio promedio de venta
  - Distribución por cliente/mercado
  - Tendencias de venta
  - Productos más rentables
  
VISUALIZACIONES:
  - Top productos vendidos
  - Evolución de precios
  - Distribución por tipo de cliente
  - Estacionalidad de ventas
""")

ventas_sample = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['product_id', '!=', False],
        ['date', '>=', '2025-11-01'],
        ['quantity', '>', 0],
        ['credit', '>', 0],
        ['account_id.code', '=like', '41%']
    ],
    ['product_id', 'quantity', 'credit', 'date', 'move_id', 'partner_id'],
    limit=5
)

print(f"\n✓ Datos disponibles: {len(ventas_sample)} líneas de muestra")

# =======================================================================================
# OPCIÓN 3: ANÁLISIS DE PRODUCCIÓN (PSP → PTT)
# =======================================================================================
print("\n" + "="*140)
print("✅ OPCIÓN 3: ANÁLISIS DE RENDIMIENTO DE PRODUCCIÓN")
print("="*140)

print("""
OBJETIVO: Medir rendimiento real PSP → PTT
MÉTRICAS VÁLIDAS:
  - % de rendimiento por tipo de fruta
  - Merma de proceso real
  - Tiempo de procesamiento
  - Eficiencia de línea
  - Costo de mano de obra por kg producido
  
DATOS NECESARIOS:
  - Órdenes de fabricación (mrp.production)
  - Consumos de MP (stock.move con tipo consume)
  - Producción de PT (stock.move con tipo produce)
  - Lotes/trazabilidad
""")

# Verificar si tenemos órdenes de producción
prod_sample = odoo.search_read(
    'mrp.production',
    [['date_planned_start', '>=', '2025-11-01']],
    ['name', 'product_id', 'product_qty', 'date_planned_start', 'state'],
    limit=10
)

print(f"\n✓ Órdenes de producción encontradas: {len(prod_sample)}")
if prod_sample:
    print("\nEjemplo de orden de producción:")
    orden = prod_sample[0]
    print(f"  - Nombre: {orden.get('name')}")
    print(f"  - Producto: {orden.get('product_id', [None, 'N/A'])[1] if orden.get('product_id') else 'N/A'}")
    print(f"  - Cantidad: {orden.get('product_qty')}")
    print(f"  - Estado: {orden.get('state')}")
    
    # Ver campos disponibles en una orden
    if len(prod_sample) > 0:
        print("\n  Verificando movimientos de stock asociados...")
        stock_moves = odoo.search_read(
            'stock.move',
            [['raw_material_production_id', '=', prod_sample[0]['id']]],
            ['product_id', 'product_uom_qty', 'quantity_done', 'state'],
            limit=5
        )
        print(f"  - Movimientos de consumo MP: {len(stock_moves)}")
        
else:
    print("\n⚠️  No se encontraron órdenes de producción recientes")
    print("   Verificar si el modelo existe o si hay datos en período anterior")

# =======================================================================================
# OPCIÓN 4: ANÁLISIS DE INVENTARIO REAL
# =======================================================================================
print("\n" + "="*140)
print("✅ OPCIÓN 4: ANÁLISIS DE INVENTARIO REAL (STOCK)")
print("="*140)

print("""
OBJETIVO: Analizar stock real en almacén
MÉTRICAS VÁLIDAS:
  - Stock actual por producto
  - Valorización de inventario
  - Rotación de inventario
  - Días de stock disponible
  - Stock mínimo vs máximo
  
DATOS NECESARIOS:
  - Stock actual (stock.quant)
  - Movimientos de stock (stock.move)
  - Ubicaciones de almacén
""")

# Verificar stock actual
stock_sample = odoo.search_read(
    'stock.quant',
    [['quantity', '>', 0]],
    ['product_id', 'quantity', 'location_id', 'inventory_quantity_auto_apply'],
    limit=10
)

print(f"\n✓ Registros de stock encontrados: {len(stock_sample)}")
if stock_sample:
    print("\nEjemplos de stock actual:")
    for i, sq in enumerate(stock_sample[:5]):
        prod_name = sq.get('product_id', [None, 'N/A'])[1] if sq.get('product_id') else 'N/A'
        qty = sq.get('quantity', 0)
        loc_name = sq.get('location_id', [None, 'N/A'])[1] if sq.get('location_id') else 'N/A'
        print(f"  {i+1}. {prod_name}: {qty:.2f} kg en {loc_name}")

# Verificar movimientos de stock
stock_moves_sample = odoo.search_read(
    'stock.move',
    [
        ['date', '>=', '2025-11-01'],
        ['state', '=', 'done']
    ],
    ['product_id', 'product_uom_qty', 'quantity_done', 'location_id', 'location_dest_id', 'date', 'picking_id'],
    limit=5
)

print(f"\n✓ Movimientos de stock encontrados: {len(stock_moves_sample)}")

# =======================================================================================
# OPCIÓN 5: ANÁLISIS DE COSTOS Y RENTABILIDAD
# =======================================================================================
print("\n" + "="*140)
print("✅ OPCIÓN 5: ANÁLISIS DE COSTOS Y RENTABILIDAD POR PRODUCTO")
print("="*140)

print("""
OBJETIVO: Calcular rentabilidad real por producto vendido
MÉTRICAS VÁLIDAS:
  - Costo unitario real (MP + MOD + CIF)
  - Precio de venta
  - Margen de contribución
  - Margen bruto REAL
  - Rentabilidad por cliente/mercado
  
DATOS NECESARIOS:
  - Costo estándar del producto (product.product.standard_price)
  - Costos de producción (mrp.production)
  - Precio de venta (account.move.line de ventas)
  - Opcionalmente: costos por lote
""")

# Verificar costos de productos
productos_con_costo = odoo.search_read(
    'product.product',
    [
        ['x_studio_sub_categora', '!=', False],
        ['categ_id.name', 'ilike', 'PRODUCTOS']
    ],
    ['name', 'default_code', 'standard_price', 'lst_price', 'categ_id'],
    limit=10
)

print(f"\n✓ Productos con costo estándar: {len(productos_con_costo)}")
if productos_con_costo:
    print("\nEjemplos de productos con costos:")
    for i, prod in enumerate(productos_con_costo[:5]):
        nombre = prod['name'][:50]
        codigo = prod.get('default_code', 'N/A')
        costo = prod.get('standard_price', 0)
        precio = prod.get('lst_price', 0)
        margen = ((precio - costo) / precio * 100) if precio > 0 else 0
        print(f"  {i+1}. {codigo} - {nombre}")
        print(f"     Costo: ${costo:,.2f} | Precio: ${precio:,.2f} | Margen: {margen:.1f}%")

# =======================================================================================
# RECOMENDACIONES
# =======================================================================================
print("\n" + "="*140)
print("📋 RECOMENDACIONES DE IMPLEMENTACIÓN")
print("="*140)

print("""
PRIORIDAD 1 - IMPLEMENTAR YA (datos disponibles y claros):
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. DASHBOARD DE COMPRAS                                                 │
│    ├─ Tabs separados por categoría (PSP, MP, Insumos, EPP)             │
│    ├─ Tendencias de precios por tipo de fruta                          │
│    ├─ Análisis de proveedores                                          │
│    └─ Comparación período vs período                                    │
│                                                                          │
│ 2. DASHBOARD DE VENTAS                                                  │
│    ├─ Análisis por tipo de producto (PTT, Retail, Subproducto)        │
│    ├─ Tendencias de precios de venta                                   │
│    ├─ Top productos y clientes                                         │
│    └─ Análisis de mercados                                             │
│                                                                          │
│ 3. ANÁLISIS DE RENTABILIDAD (si costos son confiables)                 │
│    ├─ Margen por producto (usando standard_price)                      │
│    ├─ Productos más/menos rentables                                    │
│    └─ Rentabilidad por cliente                                         │
└─────────────────────────────────────────────────────────────────────────┘

PRIORIDAD 2 - EXPLORAR Y VALIDAR (requiere validación de datos):
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. ANÁLISIS DE PRODUCCIÓN                                              │
│    ├─ Verificar calidad de datos en mrp.production                     │
│    ├─ Calcular rendimientos PSP → PTT                                  │
│    ├─ Medir merma de proceso                                           │
│    └─ Eficiencia de líneas de producción                               │
│                                                                          │
│ 5. ANÁLISIS DE INVENTARIO                                              │
│    ├─ Rotación de stock por producto                                   │
│    ├─ Días de inventario disponible                                    │
│    ├─ Valorización de inventario                                       │
│    └─ Alertas de stock mínimo                                          │
└─────────────────────────────────────────────────────────────────────────┘

ACCIONES INMEDIATAS:
┌─────────────────────────────────────────────────────────────────────────┐
│ ✓ Separar análisis actual en dos tabs:                                 │
│   - "Compras de Materia Prima" (solo PSP/MP)                           │
│   - "Ventas de Productos" (solo PTT/Retail)                            │
│                                                                          │
│ ✓ Eliminar comparaciones directas PSP vs PTT                           │
│                                                                          │
│ ✓ Clasificar productos sin tipo/manejo (260k kg excluidos)             │
│                                                                          │
│ ✓ Agregar filtros por categoría de producto                            │
│                                                                          │
│ ✓ Implementar análisis de tendencias de precios                        │
└─────────────────────────────────────────────────────────────────────────┘

¿QUÉ ANÁLISIS QUIERES IMPLEMENTAR PRIMERO?
1. Separar Compras vs Ventas en tabs independientes
2. Dashboard de análisis de producción (rendimientos PSP→PTT)
3. Dashboard de inventario y rotación
4. Dashboard de rentabilidad por producto
5. Todos los anteriores (implementación completa)
""")

print("\n" + "="*140)
print("FIN DE EXPLORACIÓN")
print("="*140)
