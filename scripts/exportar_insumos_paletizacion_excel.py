"""
Exportar análisis completo de insumos de paletización a Excel
Incluye detalle por año, producto, fabricación y totales
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
print("EXPORTACIÓN DETALLADA - INSUMOS Y SERVICIOS EN FABRICACIONES")
print("="*140)
print("Incluye: Insumos de paletización, electricidad, maquila y otros servicios")
print()

# 1. Estrategia: Buscar TODOS los consumos de fabricaciones y luego filtrar MP
print("🔍 Obteniendo TODOS los consumos históricos de fabricaciones...")
print("   (Esto puede tardar un minuto, estamos obteniendo datos completos...)")

# Primero obtener una muestra para identificar qué productos NO son Materia Prima
consumos_muestra = odoo.search_read(
    'stock.move',
    [
        ['raw_material_production_id', '!=', False],
        ['state', '=', 'done']
    ],
    ['id', 'product_id'],
    limit=10000,
    order='date desc'
)

print(f"✓ Muestra de {len(consumos_muestra):,} consumos obtenida")

# Obtener todos los productos únicos de la muestra
producto_ids_muestra = list(set([c.get('product_id', [None])[0] for c in consumos_muestra if c.get('product_id')]))
producto_ids_muestra = [x for x in producto_ids_muestra if x]

print(f"✓ Productos únicos en muestra: {len(producto_ids_muestra):,}")

# 2. Obtener información de estos productos
print("\n📦 Cargando información de productos...")
productos_todos = odoo.search_read(
    'product.product',
    [['id', 'in', producto_ids_muestra]],
    ['id', 'name', 'default_code', 'categ_id', 'standard_price', 'list_price', 'uom_id', 'type'],
    limit=5000
)

print(f"✓ Total productos cargados: {len(productos_todos)}")

# Categorizar productos: MP vs Insumos/Servicios
print("\n🔍 Categorizando productos (MP vs Insumos/Servicios)...")
productos_mp = []
productos_insumos = []

for prod in productos_todos:
    cat_name = prod.get('categ_id', [None, ''])[1] if prod.get('categ_id') else ''
    prod_name = prod.get('name', '').upper()
    
    # Filtrar Materia Prima (PRODUCTOS)
    if 'PRODUCTOS' in cat_name.upper():
        productos_mp.append(prod['id'])
    else:
        # Todo lo demás son insumos/servicios
        productos_insumos.append(prod)

print(f"✓ Productos de Materia Prima (excluir): {len(productos_mp):,}")
print(f"✓ Productos de Insumos/Servicios (incluir): {len(productos_insumos):,}")

# Crear diccionario de productos de insumos
productos_map = {p['id']: p for p in productos_insumos}
producto_ids = list(productos_map.keys())

# 3. Obtener TODOS los consumos históricos de insumos/servicios
print("\n💰 Obteniendo consumos históricos de insumos y servicios...")
print("   (Esto puede tardar varios segundos...)")

# Buscar en lotes para no saturar
consumos_todos = []
batch_size = 100

for i in range(0, len(producto_ids), batch_size):
    batch = producto_ids[i:i+batch_size]
    print(f"   Procesando lote {i//batch_size + 1}/{(len(producto_ids)-1)//batch_size + 1}...", end='\r')
    
    consumos_batch = odoo.search_read(
        'stock.move',
        [
            ['product_id', 'in', batch],
            ['raw_material_production_id', '!=', False],
            ['state', '=', 'done']
        ],
        ['id', 'product_id', 'quantity_done', 'price_unit', 'raw_material_production_id', 'date', 'reference'],
        limit=10000,
        order='date desc'
    )
    
    consumos_todos.extend(consumos_batch)

print(f"\n✓ Total consumos encontrados: {len(consumos_todos):,}")

# 4. Enriquecer con datos de órdenes de fabricación
print("\n🏭 Obteniendo datos de órdenes de fabricación...")

orden_ids = list(set([c.get('raw_material_production_id', [None])[0] for c in consumos_todos if c.get('raw_material_production_id')]))
orden_ids = [x for x in orden_ids if x]

print(f"✓ Órdenes únicas: {len(orden_ids):,}")

# Obtener órdenes en lotes
ordenes_map = {}
batch_size = 100

for i in range(0, len(orden_ids), batch_size):
    batch = orden_ids[i:i+batch_size]
    print(f"   Procesando lote {i//batch_size + 1}/{(len(orden_ids)-1)//batch_size + 1}...", end='\r')
    
    ordenes_batch = odoo.search_read(
        'mrp.production',
        [['id', 'in', batch]],
        ['id', 'name', 'product_id', 'date_planned_start', 'state', 'company_id'],
        limit=5000
    )
    
    for orden in ordenes_batch:
        ordenes_map[orden['id']] = orden

print(f"\n✓ Órdenes cargadas: {len(ordenes_map):,}")

# 5. Preparar datos para Excel
print("\n📊 Preparando datos para exportación...")

data_detalle = []
estadisticas = {
    'total_valor': 0,
    'total_cantidad': 0,
    'total_consumos': 0,
    'por_ano': defaultdict(lambda: {'valor': 0, 'cantidad': 0, 'consumos': 0}),
    'por_producto': defaultdict(lambda: {'valor': 0, 'cantidad': 0, 'consumos': 0, 'nombre': ''}),
    'por_categoria': defaultdict(lambda: {'valor': 0, 'cantidad': 0, 'consumos': 0, 'nombre': ''})
}

for consumo in consumos_todos:
    # Datos básicos
    prod_id = consumo.get('product_id', [None])[0]
    if not prod_id or prod_id not in productos_map:
        continue
    
    producto = productos_map[prod_id]
    orden_id = consumo.get('raw_material_production_id', [None])[0]
    orden = ordenes_map.get(orden_id, {})
    
    qty = consumo.get('quantity_done', 0)
    precio_unit = consumo.get('price_unit', 0)
    valor_total = qty * precio_unit
    
    fecha_str = consumo.get('date', '')
    try:
        fecha_obj = datetime.strptime(fecha_str[:10], '%Y-%m-%d') if fecha_str else None
        ano = fecha_obj.year if fecha_obj else None
        fecha_display = fecha_obj.strftime('%Y-%m-%d') if fecha_obj else 'N/A'
    except:
        ano = None
        fecha_display = 'N/A'
    
    # Construir fila
    # Detectar tipo de insumo
    cat_nombre = producto.get('categ_id', [None, 'N/A'])[1] if producto.get('categ_id') else 'N/A'
    prod_nombre = producto.get('name', '').upper()
    prod_tipo = producto.get('type', 'product')
    
    # Clasificar
    if prod_tipo == 'service':
        tipo_insumo = 'SERVICIO'
    elif 'ELECTRICIDAD' in prod_nombre or 'ELECTRIC' in prod_nombre:
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
    
    # Estadísticas por tipo de insumo
    tipo_insumo = fila['Tipo Insumo']
    if 'por_tipo' not in estadisticas:
        estadisticas['por_tipo'] = defaultdict(lambda: {'valor': 0, 'cantidad': 0, 'consumos': 0})
    estadisticas['por_tipo'][tipo_insumo]['valor'] += valor_total
    estadisticas['por_tipo'][tipo_insumo]['cantidad'] += qty
    estadisticas['por_tipo'][tipo_insumo]['consumos'] += 1
    
    data_detalle.append(fila)
    
    # Actualizar estadísticas
    estadisticas['total_valor'] += valor_total
    estadisticas['total_cantidad'] += qty
    estadisticas['total_consumos'] += 1
    
    if ano:
        estadisticas['por_ano'][ano]['valor'] += valor_total
        estadisticas['por_ano'][ano]['cantidad'] += qty
        estadisticas['por_ano'][ano]['consumos'] += 1
    
    cat_nombre = fila['Categoría']
    estadisticas['por_categoria'][cat_nombre]['valor'] += valor_total
    estadisticas['por_categoria'][cat_nombre]['cantidad'] += qty
    estadisticas['por_categoria'][cat_nombre]['consumos'] += 1
    estadisticas['por_categoria'][cat_nombre]['nombre'] = cat_nombre
    
    estadisticas['por_producto'][prod_id]['valor'] += valor_total
    estadisticas['por_producto'][prod_id]['cantidad'] += qty
    estadisticas['por_producto'][prod_id]['consumos'] += 1
    estadisticas['por_producto'][prod_id]['nombre'] = fila['Insumo Nombre']
    
    # Estadísticas por tipo de insumo
    tipo_insumo = fila['Tipo Insumo']
    if 'por_tipo' not in estadisticas:
        estadisticas['por_tipo'] = defaultdict(lambda: {'valor': 0, 'cantidad': 0, 'consumos': 0})
    estadisticas['por_tipo'][tipo_insumo]['valor'] += valor_total
    estadisticas['por_tipo'][tipo_insumo]['cantidad'] += qty
    estadisticas['por_tipo'][tipo_insumo]['consumos'] += 1

print(f"✓ Filas preparadas: {len(data_detalle):,}")

# 6. Crear DataFrames
print("\n📈 Generando DataFrames...")

df_detalle = pd.DataFrame(data_detalle)

# Resumen por año
data_por_ano = []
for ano, stats in sorted(estadisticas['por_ano'].items()):
    data_por_ano.append({
        'Año': ano,
        'Cantidad Total': stats['cantidad'],
        'Valor Total': stats['valor'],
        'Nº Consumos': stats['consumos'],
        'Valor Promedio/Consumo': stats['valor'] / stats['consumos'] if stats['consumos'] > 0 else 0
    })
df_por_ano = pd.DataFrame(data_por_ano)

# Resumen por producto
data_por_producto = []
for prod_id, stats in sorted(estadisticas['por_producto'].items(), key=lambda x: x[1]['valor'], reverse=True):
    data_por_producto.append({
        'Insumo': stats['nombre'],
        'Cantidad Total': stats['cantidad'],
        'Valor Total': stats['valor'],
        'Nº Usos': stats['consumos'],
        'Valor Promedio/Uso': stats['valor'] / stats['consumos'] if stats['consumos'] > 0 else 0,
        'Cantidad Promedio/Uso': stats['cantidad'] / stats['consumos'] if stats['consumos'] > 0 else 0
    })
df_por_producto = pd.DataFrame(data_por_producto)

# Resumen por categoría Odoo
for cat, stats in sorted(estadisticas['por_categoria'].items(), key=lambda x: x[1]['valor'], reverse=True):
    data_por_categoria.append({
        'Categoría': stats['nombre'],
        'Cantidad Total': stats['cantidad'],
        'Valor Total': stats['valor'],
        'Nº Consumos': stats['consumos'],
        '% del Total': (stats['valor'] / estadisticas['total_valor'] * 100) if estadisticas['total_valor'] > 0 else 0
    })
df_por_categoria = pd.DataFrame(data_por_categoria)

# Resumen por TIPO de insumo
data_por_tipo = []
for tipo, stats in sorted(estadisticas.get('por_tipo', {}).items(), key=lambda x: x[1]['valor'], reverse=True):
    data_por_tipo.append({
        'Tipo de Insumo': tipo,
        'Cantidad Total': stats['cantidad'],
        'Valor Total': stats['valor'],
        'Nº Consumos': stats['consumos'],
        '% del Total': (stats['valor'] / estadisticas['total_valor'] * 100) if estadisticas['total_valor'] > 0 else 0
    })
df_por_tipo = pd.DataFrame(data_por_tipo
        'Cantidad Total': stats['cantidad'],
        'Valor Total': stats['valor'],
        'Nº Consumos': stats['consumos'],
        'Valor Promedio/Consumo': stats['valor'] / stats['consumos'] if stats['consumos'] > 0 else 0
    })
df_por_ano = pd.DataFrame(data_por_ano)

# Resumen por producto
data_por_producto = []
for prod_id, stats in sorted(estadisticas['por_producto'].items(), key=lambda x: x[1]['valor'], reverse=True):
    data_por_producto.append({
        'Insumo': stats['nombre'],
        'Cantidad Total': stats['cantidad'],
        'Valor Total': stats['valor'],
        'Nº Usos': stats['consumos'],
        'Valor Promedio/Uso': stats['valor'] / stats['consumos'] if stats['consumos'] > 0 else 0,
        'Cantidad Promedio/Uso': stats['cantidad'] / stats['consumos'] if stats['consumos'] > 0 else 0
    })
df_por_producto = pd.DataFrame(data_por_producto)

# Resumen por categoría
data_por_categoria = []
for cat, stats in sorted(estadisticas['por_categoria'].items(), key=lambda x: x[1]['valor'], reverse=True):
    data_por_categoria.append({
        'Categoría': stats['nombre'],
        'Cantidad Total': stats['cantidad'],
        'Valor Total': stats['valor'],
        'Nº Consumos': stats['consumos'],
        '% del Total': (stats['valor'] / estadisticas['total_valor'] * 100) if estadisticas['total_valor'] > 0 else 0
    })
df_por_categoria = pd.DataFrame(data_por_categoria)

# 7. Exportar a Excel
print("\n💾 Exportando a Excel...")

timestamp = datetime.serviciosme('%Y%m%d_%H%M%S')
filename = f"insumtipo de insumo
    df_por_tipo.to_excel(writer, sheet_name='Por Tipo Insumo', index=False)
    
    # Hoja 5: Por categoría Odoo
    df_por_categoria.to_excel(writer, sheet_name='Por Categoría Odoo', index=False)
    
    # Hoja 6: Resumen ejecutivo
    df_resumen = pd.DataFrame([
        {'Métrica': 'Total Valor Histórico', 'Valor': f"${estadisticas['total_valor']:,.0f}"},
        {'Métrica': 'Total Cantidad Consumida', 'Valor': f"{estadisticas['total_cantidad']:,.2f} unidades"},
        {'Métrica': 'Total Consumos', 'Valor': f"{estadisticas['total_consumos']:,}"},
        {'Métrica': 'Órdenes de Fabricación', 'Valor': f"{len(orden_ids):,}"},
        {'Métrica': 'Productos de Insumos', 'Valor': f"{len(estadisticas['por_producto']):,}"},
        {'Métrica': 'Período Analizado', 'Valor': f"{min(estadisticas['por_ano'].keys()) if estadisticas['por_ano'] else 'N/A'} - {max(estadisticas['por_ano'].keys()) if estadisticas['por_ano'] else 'N/A'}"},
    ])
    df_resumen.to_excel(writer, sheet_name='Resumen', index=Tipo Insumo', 'Por Categoría Odoo
    
    # Hoja 2: Por año
    df_por_ano.to_excel(writer, sheet_name='Por Año', index=False)
    
    # Hoja 3: Por producto (top 100)
    df_por_producto.head(100).to_excel(writer, sheet_name='Top 100 Productos', index=False)
    
    # Hoja 4: Por categoría
    df_por_categoria.to_excel(writer, sheet_name='Por Categoría', index=False)
    
    # Hoja 5: Detalle completo (limitado a 100,000 filas por rendimiento)
    df_detalle.head(100000).to_excel(writer, sheet_name='Detalle Completo', index=False)
    
    # Formatear columnas de dinero y números
    for sheet_name in ['Por Año', 'Top 100 Productos', 'Por Categoría', 'Detalle Completo']:
        worksheet = writer.sheets[sheet_name]
        
        # Autoajustar columnas
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width

print(f"✅ Archivo exportado: {filename}")

# 8. Mostrar resumen en consola
print("\n" + "="*140)
print("RESUMEN EJECUTIVO - INSUMOS Y SERVICIOS EN FABRICACIONES")
print("="*140)
print("(Excluye Materia Prima - Solo insumos, servicios y costos indirectos)")
print("="*140)
print()
print(f"💰 VALOR TOTAL HISTÓRICO: ${estadisticas['total_valor']:,.0f}")
print(f"📦 CANTIDAD TOTAL: {estadisticas['total_cantidad']:,.2f} unidades")
print(f"🔢 TOTAL CONSUMOS: {estadisticas['total_consumos']:,}")
print(f"🏭 ÓRDENES DE FABRICACIÓN: {len(orden_ids):,}")
print(f"📋 PRODUCTOS DIFERENTES: {len(estadisticas['por_producto']):,}")
print()

print("="*140)
print("EVOLUCIÓN POR AÑO")
print("="*140)
print(f"{'Año':>6s} | {'Cantidad':>15s} | {'Valor Total':>18s} | {'Nº Consumos':>12s} | {'Valor Prom/Consumo':>20s}")
print("-" * 140)

for ano, stats in sorted(estadisticas['por_ano'].items()):
    promedio = stats['valor'] / stats['consumos'] if stats['consumos'] > 0 else 0
    print(f"{ano:6d} | {stats['cantidad']:15,.2f} | ${stats['valor']:17,.0f} | {stats['consumos']:12,d} | ${promedio:19,.0f}")
DISTRIBUCIÓN POR TIPO DE INSUMO")
print("="*140)
print(f"{'Tipo de Insumo':<30s} | {'Valor Total':>18s} | {'% Total':>8s} | {'Nº Consumos':>12s}")
print("-" * 140)

for tipo_data in data_por_tipo:
    print(f"{tipo_data['Tipo de Insumo']:<30s} | ${tipo_data['Valor Total']:17,.0f} | {tipo_data['% del Total']:7.2f}% | {tipo_data['Nº Consumos']:12,d}")

print()
print("="*140)
print("TOP 10 CATEGORÍAS ODOO
print()
print("="*140)
print("TOP 10 CATEGORÍAS POR VALOR")
print("="*140)
print(f"{'Categoría':<60s} | {'Valor Total':>18s} | {'% Total':>8s}")
print("-" * 140)

for cat_data in sorted(data_por_categoria, key=lambda x: x['Valor Total'], reverse=True)[:10]:
    print(f"{cat_data['Categoría'][:60]:60s} | ${cat_data['Valor Total']:17,.0f} | {cat_data['% del Total']:7.2f}%")

print()
print("="*140)
print("TOP 15 PRODUCTOS POR VALOR")
print("="*140)
print(f"{'Producto':<60s} | {'Cantidad':>15s} | {'Valor Total':>18s} | {'Usos':>8s}")
print("-" * 140)

for prod_data in data_por_producto[:15]:
    print(f"{prod_data['Insumo'][:60]:60s} | {prod_data['Cantidad Total']:15,.2f} | ${prod_data['Valor Total']:17,.0f} | {prod_data['Nº Usos']:8,d}")

print()
print("="*140)
print("✅ PROCESO COMPLETADO")
print("="*140)
print(f"\n📁 Archivo Excel generado: {filename}")
print(f"📊 Total filas en detalle: {len(data_detalle):,}")
print(f"📈 Listo para análisis en Excel o carga al dashboard")
