"""
Exportar análisis completo de TODOS los insumos y servicios en fabricaciones
Incluye: Paletización, electricidad, maquila, embalajes, etiquetas, etc.
Excluye: Solo Materia Prima (PRODUCTOS)
"""
import sys
import os
from datetime import datetime
import pandas as pd
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

# Conectar a Odoo
odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*140)
print("EXPORTACIÓN DETALLADA - INSUMOS Y SERVICIOS EN FABRICACIONES QUE PROCESARON FRUTA")
print("="*140)
print("Incluye: Solo fabricaciones con componentes de fruta (categoría PRODUCTOS)")
print("Excluye: Desmontajes, vueltas, devoluciones")
print("Insumos: Paletización, electricidad, maquila, embalajes, etc.")
print()

# 1. Obtener todos los consumos de fabricaciones
print("🔍 Obteniendo TODOS los consumos históricos de fabricaciones...")

consumos_todos = odoo.search_read(
    'stock.move',
    [
        ['raw_material_production_id', '!=', False],
        ['state', '=', 'done']
    ],
    ['id', 'product_id', 'quantity_done', 'price_unit', 'raw_material_production_id', 'date', 'reference'],
    limit=20000,
    order='date desc'
)

print(f"✓ Total consumos obtenidos: {len(consumos_todos):,}")

# 2. Obtener productos únicos
producto_ids_todos = list(set([c.get('product_id', [None])[0] for c in consumos_todos if c.get('product_id')]))
producto_ids_todos = [x for x in producto_ids_todos if x]

print(f"✓ Productos únicos: {len(producto_ids_todos):,}")

# 3. Obtener información de productos
print("\n📦 Cargando información de productos...")
productos_todos = odoo.search_read(
    'product.product',
    [['id', 'in', producto_ids_todos]],
    ['id', 'name', 'default_code', 'categ_id', 'standard_price', 'list_price', 'uom_id', 'type'],
    limit=10000
)

print(f"✓ Productos cargados: {len(productos_todos)}")

# 4. Filtrar: Excluir SOLO Materia Prima (categoría PRODUCTOS)
print("\n🔍 Categorizando productos...")
productos_mp_ids = []
productos_insumos = []

for prod in productos_todos:
    cat_name = prod.get('categ_id', [None, ''])[1] if prod.get('categ_id') else ''
    
    # Excluir solo PRODUCTOS (Materia Prima)
    if 'PRODUCTOS' in cat_name.upper():
        productos_mp_ids.append(prod['id'])
    else:
        productos_insumos.append(prod)

print(f"✓ Materia Prima (excluir): {len(productos_mp_ids):,}")
print(f"✓ Insumos/Servicios (incluir): {len(productos_insumos):,}")

# Crear mapeo
productos_map = {p['id']: p for p in productos_insumos}

# 5. Filtrar consumos para quedarnos solo con insumos/servicios
print("\n💰 Filtrando consumos de insumos y servicios...")
consumos_insumos = [c for c in consumos_todos if c.get('product_id', [None])[0] in productos_map]

print(f"✓ Consumos de insumos/servicios: {len(consumos_insumos):,}")

# 6. Identificar órdenes que procesaron FRUTA (tienen componentes de PRODUCTOS)
print("\n🏭 Identificando órdenes que procesaron fruta...")
orden_ids_candidatas = list(set([c.get('raw_material_production_id', [None])[0] for c in consumos_insumos if c.get('raw_material_production_id')]))
orden_ids_candidatas = [x for x in orden_ids_candidatas if x]

print(f"✓ Órdenes candidatas: {len(orden_ids_candidatas):,}")

# Obtener TODOS los componentes de estas órdenes para verificar si tienen fruta
print("\n🔍 Verificando componentes de cada orden (buscando fruta)...")
consumos_mp = odoo.search_read(
    'stock.move',
    [
        ['raw_material_production_id', 'in', orden_ids_candidatas],
        ['state', '=', 'done']
    ],
    ['id', 'product_id', 'raw_material_production_id'],
    limit=50000
)

print(f"✓ Total componentes encontrados: {len(consumos_mp):,}")

# Identificar qué productos son MP (fruta)
productos_mp_en_consumos = list(set([c.get('product_id', [None])[0] for c in consumos_mp if c.get('product_id')]))
productos_mp_en_consumos = [x for x in productos_mp_en_consumos if x]

print(f"\n📦 Verificando cuáles son productos de fruta...")
productos_mp_info = odoo.search_read(
    'product.product',
    [['id', 'in', productos_mp_en_consumos]],
    ['id', 'categ_id'],
    limit=10000
)

# IDs de productos que SÍ son fruta (PRODUCTOS)
productos_fruta_ids = set([
    p['id'] for p in productos_mp_info 
    if p.get('categ_id') and 'PRODUCTOS' in (p.get('categ_id', [None, ''])[1] or '').upper()
])

print(f"✓ Productos de fruta identificados: {len(productos_fruta_ids):,}")

# Identificar qué órdenes tienen al menos 1 componente de fruta
ordenes_con_fruta = set()
for consumo_mp in consumos_mp:
    prod_id = consumo_mp.get('product_id', [None])[0]
    if prod_id in productos_fruta_ids:
        orden_id = consumo_mp.get('raw_material_production_id', [None])[0]
        if orden_id:
            ordenes_con_fruta.add(orden_id)

print(f"✓ Órdenes que procesaron fruta: {len(ordenes_con_fruta):,}")

# FILTRAR consumos de insumos para quedarnos solo con órdenes que procesaron fruta
consumos_insumos_filtrados = [
    c for c in consumos_insumos 
    if c.get('raw_material_production_id', [None])[0] in ordenes_con_fruta
]

print(f"✓ Consumos de insumos en órdenes con fruta: {len(consumos_insumos_filtrados):,} (de {len(consumos_insumos):,} totales)")

# Ahora cargar datos de las órdenes con fruta
print("\n🏭 Cargando datos de órdenes con fruta...")
orden_ids = list(ordenes_con_fruta)

ordenes_map = {}
batch_size = 100

for i in range(0, len(orden_ids), batch_size):
    batch = orden_ids[i:i+batch_size]
    print(f"   Lote {i//batch_size + 1}/{(len(orden_ids)-1)//batch_size + 1}...", end='\r')
    
    ordenes_batch = odoo.search_read(
        'mrp.production',
        [['id', 'in', batch]],
        ['id', 'name', 'product_id', 'date_planned_start', 'state'],
        limit=5000
    )
    
    for orden in ordenes_batch:
        ordenes_map[orden['id']] = orden

print(f"\n✓ Órdenes cargadas: {len(ordenes_map):,}")

# Filtrar órdenes de desmontajes/vueltas
print("\n🚫 Excluyendo fabricaciones de desmontajes y vueltas...")
ordenes_excluidas = []
ordenes_validas = {}

for orden_id, orden in ordenes_map.items():
    producto_final = orden.get('product_id', [None, ''])[1] if orden.get('product_id') else ''
    nombre_of = orden.get('name', '').upper()
    
    # Detectar desmontajes/vueltas por nombre de producto o nombre de OF
    es_desmontaje = any(keyword in producto_final.upper() for keyword in [
        'DESMONTAJE', 'DESMONT', 'VUELTA', 'DEVOLUCION', 'DEVOL', 'RETORNO',
        'DESARMADO', 'DESMONTE', 'REVERSA', 'REVERSE'
    ])
    
    es_vuelta_of = any(keyword in nombre_of for keyword in [
        'DESMONTAJE', 'DESMONT', 'VUELTA', 'DEVOL', 'RETORNO'
    ])
    
    if es_desmontaje or es_vuelta_of:
        ordenes_excluidas.append({
            'id': orden_id,
            'nombre': nombre_of,
            'producto': producto_final
        })
    else:
        ordenes_validas[orden_id] = orden

print(f"✓ Órdenes válidas: {len(ordenes_validas):,}")
print(f"✓ Órdenes excluidas (desmontajes/vueltas): {len(ordenes_excluidas):,}")

if ordenes_excluidas and len(ordenes_excluidas) <= 10:
    print("\nEjemplos de órdenes excluidas:")
    for excl in ordenes_excluidas[:10]:
        print(f"  - {excl['nombre']}: {excl['producto'][:60]}")

# Actualizar ordenes_map y orden_ids
ordenes_map = ordenes_validas
orden_ids = list(ordenes_validas.keys())

# Filtrar consumos_insumos_filtrados para excluir desmontajes
consumos_antes = len(consumos_insumos_filtrados)
consumos_insumos_filtrados = [
    c for c in consumos_insumos_filtrados 
    if c.get('raw_material_production_id', [None])[0] in ordenes_validas
]

print(f"✓ Consumos después de excluir desmontajes: {len(consumos_insumos_filtrados):,} (excluidos: {consumos_antes - len(consumos_insumos_filtrados):,})")

# 7. Procesar datos
print("\n📊 Procesando datos para Excel...")

data_detalle = []
estadisticas = {
    'total_valor': 0,
    'total_cantidad': 0,
    'total_consumos': 0,
    'por_ano': defaultdict(lambda: {'valor': 0, 'cantidad': 0, 'consumos': 0}),
    'por_producto': defaultdict(lambda: {'valor': 0, 'cantidad': 0, 'consumos': 0, 'nombre': ''}),
    'por_categoria': defaultdict(lambda: {'valor': 0, 'cantidad': 0, 'consumos': 0, 'nombre': ''}),
    'por_tipo': defaultdict(lambda: {'valor': 0, 'cantidad': 0, 'consumos': 0})
}

for consumo in consumos_insumos_filtrados:
    prod_id = consumo.get('product_id', [None])[0]
    if not prod_id or prod_id not in productos_map:
        continue
    
    producto = productos_map[prod_id]
    orden_id = consumo.get('raw_material_production_id', [None])[0]
    orden = ordenes_map.get(orden_id, {})
    
    qty = consumo.get('quantity_done', 0)
    precio_unit = consumo.get('price_unit', 0)
    valor_total = qty * precio_unit
    
    # Procesar fecha
    fecha_str = consumo.get('date', '')
    try:
        fecha_obj = datetime.strptime(fecha_str[:10], '%Y-%m-%d') if fecha_str else None
        ano = fecha_obj.year if fecha_obj else None
        fecha_display = fecha_obj.strftime('%Y-%m-%d') if fecha_obj else 'N/A'
    except:
        ano = None
        fecha_display = 'N/A'
    
    # Clasificar tipo de insumo
    cat_nombre = producto.get('categ_id', [None, 'N/A'])[1] if producto.get('categ_id') else 'N/A'
    prod_nombre = producto.get('name', '').upper()
    prod_tipo = producto.get('type', 'product')
    
    if prod_tipo == 'service':
        tipo_insumo = 'SERVICIO'
    elif 'ELECTRICIDAD' in prod_nombre or 'ELECTRIC' in prod_nombre or 'ETE' in prod_nombre:
        tipo_insumo = 'ELECTRICIDAD'
    elif 'MAQUILA' in prod_nombre:
        tipo_insumo = 'MAQUILA'
    elif 'PALETIZACION' in cat_nombre.upper() or 'PALLET' in prod_nombre:
        tipo_insumo = 'PALETIZACIÓN'
    elif 'CAJA' in prod_nombre or 'BOLSA' in prod_nombre or 'FILM' in prod_nombre:
        tipo_insumo = 'EMBALAJE'
    elif 'ETIQUETA' in prod_nombre:
        tipo_insumo = 'ETIQUETAS'
    else:
        tipo_insumo = 'OTROS INSUMOS'
    
    # Construir fila
    fila = {
        'Fecha': fecha_display,
        'Año': ano,
        'Orden Fabricación': orden.get('name', 'N/A'),
        'Producto Final': orden.get('product_id', [None, 'N/A'])[1] if orden.get('product_id') else 'N/A',
        'Tipo Insumo': tipo_insumo,
        'Insumo Código': producto.get('default_code', ''),
        'Insumo Nombre': producto.get('name', 'N/A'),
        'Categoría Odoo': cat_nombre,
        'Tipo Producto': prod_tipo,
        'Cantidad': qty,
        'Unidad': producto.get('uom_id', [None, 'unid'])[1] if producto.get('uom_id') else 'unid',
        'Precio Unitario': precio_unit,
        'Valor Total': valor_total,
        'Referencia': consumo.get('reference', ''),
        'Estado OF': orden.get('state', 'N/A')
    }
    
    data_detalle.append(fila)
    
    # Actualizar estadísticas
    estadisticas['total_valor'] += valor_total
    estadisticas['total_cantidad'] += qty
    estadisticas['total_consumos'] += 1
    
    if ano:
        estadisticas['por_ano'][ano]['valor'] += valor_total
        estadisticas['por_ano'][ano]['cantidad'] += qty
        estadisticas['por_ano'][ano]['consumos'] += 1
    
    estadisticas['por_categoria'][cat_nombre]['valor'] += valor_total
    estadisticas['por_categoria'][cat_nombre]['cantidad'] += qty
    estadisticas['por_categoria'][cat_nombre]['consumos'] += 1
    estadisticas['por_categoria'][cat_nombre]['nombre'] = cat_nombre
    
    estadisticas['por_producto'][prod_id]['valor'] += valor_total
    estadisticas['por_producto'][prod_id]['cantidad'] += qty
    estadisticas['por_producto'][prod_id]['consumos'] += 1
    estadisticas['por_producto'][prod_id]['nombre'] = fila['Insumo Nombre']
    
    estadisticas['por_tipo'][tipo_insumo]['valor'] += valor_total
    estadisticas['por_tipo'][tipo_insumo]['cantidad'] += qty
    estadisticas['por_tipo'][tipo_insumo]['consumos'] += 1

print(f"✓ Filas procesadas: {len(data_detalle):,}")

# 8. Crear DataFrames
print("\n📈 Generando DataFrames...")

df_detalle = pd.DataFrame(data_detalle)

# Por año
df_por_ano = pd.DataFrame([
    {
        'Año': ano,
        'Cantidad Total': stats['cantidad'],
        'Valor Total': stats['valor'],
        'Nº Consumos': stats['consumos'],
        'Valor Promedio/Consumo': stats['valor'] / stats['consumos'] if stats['consumos'] > 0 else 0
    }
    for ano, stats in sorted(estadisticas['por_ano'].items())
])

# Por producto
df_por_producto = pd.DataFrame([
    {
        'Insumo': stats['nombre'],
        'Cantidad Total': stats['cantidad'],
        'Valor Total': stats['valor'],
        'Nº Usos': stats['consumos'],
        'Valor Promedio/Uso': stats['valor'] / stats['consumos'] if stats['consumos'] > 0 else 0
    }
    for prod_id, stats in sorted(estadisticas['por_producto'].items(), key=lambda x: x[1]['valor'], reverse=True)
])

# Por categoría
df_por_categoria = pd.DataFrame([
    {
        'Categoría': stats['nombre'],
        'Valor Total': stats['valor'],
        'Nº Consumos': stats['consumos'],
        '% del Total': (stats['valor'] / estadisticas['total_valor'] * 100) if estadisticas['total_valor'] > 0 else 0
    }
    for cat, stats in sorted(estadisticas['por_categoria'].items(), key=lambda x: x[1]['valor'], reverse=True)
])

# Por tipo
df_por_tipo = pd.DataFrame([
    {
        'Tipo de Insumo': tipo,
        'Valor Total': stats['valor'],
        'Nº Consumos': stats['consumos'],
        '% del Total': (stats['valor'] / estadisticas['total_valor'] * 100) if estadisticas['total_valor'] > 0 else 0
    }
    for tipo, stats in sorted(estadisticas['por_tipo'].items(), key=lambda x: x[1]['valor'], reverse=True)
])

# 9. Exportar a Excel
print("\n💾 Exportando a Excel...")

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f"insumos_servicios_fabricaciones_{timestamp}.xlsx"

with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    # Resumen
    df_resumen = pd.DataFrame([
        {'Métrica': 'Total Valor Histórico', 'Valor': f"${estadisticas['total_valor']:,.0f}"},
        {'Métrica': 'Total Consumos', 'Valor': f"{estadisticas['total_consumos']:,}"},
        {'Métrica': 'Órdenes de Fabricación', 'Valor': f"{len(orden_ids):,}"},
        {'Métrica': 'Productos Diferentes', 'Valor': f"{len(estadisticas['por_producto']):,}"},
        {'Métrica': 'Período', 'Valor': f"{min(estadisticas['por_ano'].keys()) if estadisticas['por_ano'] else 'N/A'} - {max(estadisticas['por_ano'].keys()) if estadisticas['por_ano'] else 'N/A'}"},
    ])
    df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
    
    df_por_ano.to_excel(writer, sheet_name='Por Año', index=False)
    df_por_producto.head(100).to_excel(writer, sheet_name='Top 100 Productos', index=False)
    df_por_tipo.to_excel(writer, sheet_name='Por Tipo Insumo', index=False)
    df_por_categoria.to_excel(writer, sheet_name='Por Categoría Odoo', index=False)
    df_detalle.head(100000).to_excel(writer, sheet_name='Detalle Completo', index=False)

print(f"✅ Archivo exportado: {filename}")

# 10. Mostrar resumen en consola
print("\n" + "="*140)
print("RESUMEN EJECUTIVO - INSUMOS Y SERVICIOS EN FABRICACIONES CON FRUTA")
print("="*140)
print("(Solo fabricaciones que procesaron fruta - Excluye desmontajes/vueltas y MP)")
print("="*140)
print()
print(f"💰 VALOR TOTAL HISTÓRICO: ${estadisticas['total_valor']:,.0f}")
print(f"📦 CANTIDAD TOTAL: {estadisticas['total_cantidad']:,.2f} unidades")
print(f"🔢 TOTAL CONSUMOS: {estadisticas['total_consumos']:,}")
print(f"🏭 ÓRDENES DE FABRICACIÓN: {len(orden_ids):,}")
print(f"📋 PRODUCTOS DIFERENTES: {len(estadisticas['por_producto']):,}")

print("\n" + "="*140)
print("EVOLUCIÓN POR AÑO")
print("="*140)
for _, row in df_por_ano.iterrows():
    print(f"{int(row['Año']):6d} | {row['Cantidad Total']:15,.2f} | ${row['Valor Total']:17,.0f} | {int(row['Nº Consumos']):12,d}")

print("\n" + "="*140)
print("DISTRIBUCIÓN POR TIPO DE INSUMO")
print("="*140)
for _, row in df_por_tipo.iterrows():
    print(f"{row['Tipo de Insumo']:<30s} | ${row['Valor Total']:17,.0f} | {row['% del Total']:7.2f}%")

print("\n" + "="*140)
print("TOP 15 PRODUCTOS")
print("="*140)
for _, row in df_por_producto.head(15).iterrows():
    print(f"{row['Insumo'][:60]:60s} | ${row['Valor Total']:17,.0f} | {int(row['Nº Usos']):8,d} usos")

print("\n" + "="*140)
print("✅ PROCESO COMPLETADO")
print("="*140)
print(f"\n📁 Archivo: {filename}")
print(f"📊 Filas en detalle: {len(data_detalle):,}")
