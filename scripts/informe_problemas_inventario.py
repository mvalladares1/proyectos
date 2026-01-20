"""
ANÁLISIS DETALLADO: Problemas con el enfoque actual de inventario
Documento para presentar a gerencia
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*140)
print("REPORTE: PROBLEMAS CON ANÁLISIS DE INVENTARIO ACTUAL")
print("Período: 2025-11-24 a 2026-01-31")
print("="*140)

# =======================================================================================
# PROBLEMA 1: PRODUCTOS SIN CLASIFICAR
# =======================================================================================
print("\n" + "="*140)
print("PROBLEMA #1: PRODUCTOS SIN CLASIFICACIÓN")
print("="*140)

lineas_sin_clasificar = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'in_invoice'],
        ['move_id.state', '=', 'posted'],
        ['product_id', '!=', False],
        ['date', '>=', '2025-11-24'],
        ['date', '<=', '2026-01-31'],
        ['quantity', '>', 0],
        ['debit', '>', 0],
        ['account_id.code', '=like', '21%']
    ],
    ['product_id', 'quantity', 'debit', 'move_id'],
    limit=5000
)

# Obtener productos
prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas_sin_clasificar if l.get('product_id')]))
productos = odoo.search_read(
    'product.product',
    [['id', 'in', prod_ids]],
    ['id', 'name', 'default_code', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo', 'categ_id'],
    limit=5000
)

# Filtrar productos SIN clasificación completa
sin_clasificar = []
for prod in productos:
    tipo = prod.get('x_studio_sub_categora')
    manejo = prod.get('x_studio_categora_tipo_de_manejo')
    
    if not tipo or not manejo:
        sin_clasificar.append(prod)

print(f"\n✗ PRODUCTOS SIN CLASIFICACIÓN COMPLETA: {len(sin_clasificar)} de {len(productos)} ({len(sin_clasificar)/len(productos)*100:.1f}%)")
print("\nEjemplos de productos sin clasificar:")
print(f"{'Código':<20} {'Nombre':<60} {'Tipo Fruta':<15} {'Manejo':<15}")
print("-" * 120)

for prod in sin_clasificar[:20]:
    codigo = prod.get('default_code', 'N/A')
    nombre = prod['name'][:60]
    
    tipo = prod.get('x_studio_sub_categora')
    tipo_str = tipo[1][:15] if isinstance(tipo, (list, tuple)) and len(tipo) > 1 else "❌ SIN TIPO"
    
    manejo = prod.get('x_studio_categora_tipo_de_manejo')
    manejo_str = manejo[1][:15] if isinstance(manejo, (list, tuple)) and len(manejo) > 1 else "❌ SIN MANEJO"
    
    print(f"{codigo:<20} {nombre:<60} {tipo_str:<15} {manejo_str:<15}")

if len(sin_clasificar) > 20:
    print(f"... y {len(sin_clasificar) - 20} productos más sin clasificar")

# Calcular impacto económico
kg_sin_clasificar = 0
monto_sin_clasificar = 0

for linea in lineas_sin_clasificar:
    prod_id = linea.get('product_id', [None])[0]
    prod = next((p for p in productos if p['id'] == prod_id), None)
    
    if prod:
        tipo = prod.get('x_studio_sub_categora')
        manejo = prod.get('x_studio_categora_tipo_de_manejo')
        
        if not tipo or not manejo:
            kg_sin_clasificar += linea.get('quantity', 0)
            monto_sin_clasificar += linea.get('debit', 0)

print(f"\n💰 IMPACTO ECONÓMICO:")
print(f"   - Kilogramos excluidos: {kg_sin_clasificar:,.0f} kg")
print(f"   - Monto excluido: ${monto_sin_clasificar:,.0f} CLP")
print(f"   - Porcentaje del total: {kg_sin_clasificar/sum([l.get('quantity', 0) for l in lineas_sin_clasificar])*100:.1f}%")

# =======================================================================================
# PROBLEMA 2: MEZCLA DE PSP Y PTT
# =======================================================================================
print("\n" + "="*140)
print("PROBLEMA #2: COMPARACIÓN INCORRECTA - PSP vs PTT")
print("="*140)

# Analizar categorías de productos
categorias_compra = {}
for prod in productos:
    categ = prod.get('categ_id')
    categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
    
    if categ_name not in categorias_compra:
        categorias_compra[categ_name] = {'count': 0, 'productos': []}
    
    categorias_compra[categ_name]['count'] += 1
    categorias_compra[categ_name]['productos'].append(prod['name'][:50])

print("\nCATEGORÍAS DE PRODUCTOS EN COMPRAS:")
for categ, data in sorted(categorias_compra.items(), key=lambda x: -x[1]['count'])[:10]:
    print(f"\n{categ}: {data['count']} productos")
    print(f"  Ejemplos: {', '.join(data['productos'][:3])}")

# Analizar productos de ventas
lineas_venta = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['product_id', '!=', False],
        ['date', '>=', '2025-11-24'],
        ['date', '<=', '2026-01-31'],
        ['quantity', '>', 0],
        ['credit', '>', 0],
        ['account_id.code', '=like', '41%']
    ],
    ['product_id'],
    limit=5000
)

prod_ids_venta = list(set([l.get('product_id', [None])[0] for l in lineas_venta if l.get('product_id')]))
productos_venta = odoo.search_read(
    'product.product',
    [['id', 'in', prod_ids_venta]],
    ['id', 'name', 'default_code', 'categ_id'],
    limit=5000
)

categorias_venta = {}
for prod in productos_venta:
    categ = prod.get('categ_id')
    categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
    
    if categ_name not in categorias_venta:
        categorias_venta[categ_name] = {'count': 0, 'productos': []}
    
    categorias_venta[categ_name]['count'] += 1
    categorias_venta[categ_name]['productos'].append(prod['name'][:50])

print("\n" + "-" * 140)
print("CATEGORÍAS DE PRODUCTOS EN VENTAS:")
for categ, data in sorted(categorias_venta.items(), key=lambda x: -x[1]['count'])[:10]:
    print(f"\n{categ}: {data['count']} productos")
    print(f"  Ejemplos: {', '.join(data['productos'][:3])}")

# =======================================================================================
# PROBLEMA 3: MARGEN BRUTO INVÁLIDO
# =======================================================================================
print("\n" + "="*140)
print("PROBLEMA #3: MARGEN BRUTO NO TIENE SENTIDO")
print("="*140)

total_compra_kg = sum([l.get('quantity', 0) for l in lineas_sin_clasificar])
total_compra_monto = sum([l.get('debit', 0) for l in lineas_sin_clasificar])
total_venta_kg = sum([l.get('quantity', 0) for l in lineas_venta])
total_venta_monto = sum([l.get('credit', 0) for l in lineas_venta])

margen_monto = total_venta_monto - total_compra_monto
margen_pct = (margen_monto / total_venta_monto * 100) if total_venta_monto > 0 else 0

precio_compra = total_compra_monto/total_compra_kg if total_compra_kg > 0 else 0
precio_venta = total_venta_monto/total_venta_kg if total_venta_kg > 0 else 0

print(f"""
CÁLCULO ACTUAL (INCORRECTO):
├─ Compras:  {total_compra_kg:>12,.0f} kg × ${precio_compra:,.2f}/kg = ${total_compra_monto:>15,.0f}
├─ Ventas:   {total_venta_kg:>12,.0f} kg × ${precio_venta:,.2f}/kg = ${total_venta_monto:>15,.0f}
└─ Margen:   ${margen_monto:>15,.0f} ({margen_pct:+.1f}%)

⚠️  POR QUÉ ESTE MARGEN ES INCORRECTO:
""")

print("""
1. UNIDADES INCOMPARABLES:
   - Compramos 1.79M kg de materia prima (PSP)
   - Vendemos 470k kg de producto terminado (PTT)
   - No son comparables directamente

2. PROCESOS INTERMEDIOS NO CONSIDERADOS:
   - Limpieza y selección (pérdida de peso)
   - Congelado IQF (cambio de presentación)
   - Empaque (peso neto vs bruto)
   - Merma de proceso (10-30% típico)

3. VALOR AGREGADO IGNORADO:
   - Mano de obra de procesamiento
   - Costos de empaque
   - Almacenamiento en frío
   - Certificaciones (orgánico, etc.)
   - Logística y transporte

4. TIMING DIFERENTE:
   - Compramos en temporada alta (Nov-Ene)
   - Vendemos a lo largo del año
   - No podemos comparar períodos iguales
""")

# =======================================================================================
# RECOMENDACIONES
# =======================================================================================
print("\n" + "="*140)
print("RECOMENDACIONES PARA GERENCIA")
print("="*140)

print("""
📋 ACCIONES INMEDIATAS:

1. CLASIFICAR PRODUCTOS FALTANTES
   ├─ Asignar x_studio_sub_categora (tipo de fruta) a todos los productos
   ├─ Asignar x_studio_categora_tipo_de_manejo (Orgánico/Convencional)
   └─ Impacto: {0:,.0f} kg y ${1:,.0f} actualmente excluidos

2. REDEFINIR EL ANÁLISIS
   Opción A: Análisis por Etapa
   ├─ Tab 1: "Compras de Materia Prima (PSP)"
   │  └─ Solo facturas de proveedores con PSP
   ├─ Tab 2: "Ventas de Producto Terminado (PTT)"
   │  └─ Solo facturas de clientes con PTT
   └─ Tab 3: "Rendimiento de Producción"
       └─ PSP → PTT (con % de rendimiento)

   Opción B: Análisis de Inventario Real
   ├─ Usar movimientos de stock (stock.move)
   ├─ Considerar inventario inicial y final
   └─ Calcular rotación y días de stock

3. ELIMINAR MÉTRICAS ENGAÑOSAS
   ├─ ❌ Quitar "Margen Bruto" (no tiene sentido PSP vs PTT)
   ├─ ✓ Agregar "Rotación de Inventario"
   ├─ ✓ Agregar "Días de Stock"
   └─ ✓ Agregar "Merma de Proceso" (desde fabricación)

4. MEJORAR TRAZABILIDAD
   ├─ Vincular compras → producción → ventas
   ├─ Usar lotes y trazabilidad existente
   └─ Medir rendimientos reales por producto

📊 INDICADORES CORRECTOS A IMPLEMENTAR:

1. KPIs de Compras:
   - Volumen comprado por tipo/manejo
   - Precio promedio de compra
   - Variación de precio vs período anterior

2. KPIs de Ventas:
   - Volumen vendido por tipo/manejo
   - Precio promedio de venta
   - Variación de precio vs período anterior

3. KPIs de Operación:
   - Rendimiento de producción (PSP → PTT)
   - Merma de proceso (%)
   - Días de inventario
   - Rotación de stock

💡 CONCLUSIÓN:
El análisis actual compara "peras con manzanas". Necesitamos separar:
1. Análisis de COMPRAS (PSP)
2. Análisis de VENTAS (PTT)
3. Análisis de PRODUCCIÓN (rendimiento PSP→PTT)
4. Análisis de INVENTARIO (stock real en cada etapa)
""".format(kg_sin_clasificar, monto_sin_clasificar))

print("\n" + "="*140)
print("FIN DEL REPORTE")
print("="*140)
