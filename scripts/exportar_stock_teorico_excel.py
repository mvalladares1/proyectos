"""
DEBUG: Stock Teórico con Exportación a Excel
Exporta detalle completo de compras y ventas para análisis
Período: 2022-01-01 hasta hoy
"""
import sys
import os
from datetime import datetime
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

# Configuración
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Período completo
FECHA_DESDE = "2022-01-01"
FECHA_HASTA = datetime.now().strftime("%Y-%m-%d")

# Temporadas para resumen (2022, 2023, 2024, 2025, 2026)
TEMPORADAS = [2022, 2023, 2024, 2025, 2026]

print("=" * 140)
print("EXPORTACIÓN DETALLADA - COMPRAS Y VENTAS")
print("=" * 140)
print(f"Período: {FECHA_DESDE} hasta {FECHA_HASTA}")
print("=" * 140)

odoo = OdooClient(username=USERNAME, password=PASSWORD)

# ============================================================================
# 1. OBTENER TODAS LAS COMPRAS (FACTURAS PROVEEDORES)
# ============================================================================
print("\n🔄 Obteniendo COMPRAS (Facturas de Proveedores)...")

compras_lineas = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'in_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.journal_id.name', '=', 'Facturas de Proveedores'],
        ['product_id', '!=', False],
        ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],  # PRODUCTOS (plural)
        ['product_id.type', '!=', 'service'],  # Excluir servicios        ['account_id.code', 'in', ['21020107', '21020106']],  # Solo cuentas de facturas por recibir
        ['debit', '>', 0],  # Solo líneas con débito (compra real)        ['date', '>=', FECHA_DESDE],
        ['date', '<=', FECHA_HASTA]
    ],
    ['product_id', 'quantity', 'debit', 'credit', 'account_id', 'date', 'move_id', 'name'],
    limit=100000
)

print(f"✓ Total líneas de compras: {len(compras_lineas):,}")

# Obtener información de productos para compras (busca por ID, incluirá archivados)
if compras_lineas:
    prod_ids_compras = list(set([l.get('product_id', [None])[0] for l in compras_lineas if l.get('product_id')]))
    
    # Búsqueda directa por IDs (incluye archivados automáticamente)
    productos_compras_raw = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'product.product', 'read',
        [prod_ids_compras, ['id', 'name', 'default_code', 'product_tmpl_id', 'categ_id', 'active', 'type']]
    )
    
    productos_compras = productos_compras_raw if productos_compras_raw else []
    
    productos_activos = sum(1 for p in productos_compras if p.get('active', True))
    productos_archivados = len(productos_compras) - productos_activos
    print(f"   - Productos activos: {productos_activos}")
    print(f"   - Productos archivados: {productos_archivados}")
    
    # Mapear productos
    product_map_compras = {p['id']: p for p in productos_compras}
    
    # Obtener templates (incluye archivados automáticamente al buscar por ID)
    template_ids_compras = list(set([p.get('product_tmpl_id', [None])[0] for p in productos_compras if p.get('product_tmpl_id')]))
    
    templates_compras_raw = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'product.template', 'read',
        [template_ids_compras, ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo', 'active']]
    )
    
    templates_compras = templates_compras_raw if templates_compras_raw else []
    
    template_map_compras = {}
    for tmpl in templates_compras:
        tipo = tmpl.get('x_studio_sub_categora')
        if tipo:
            if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
                tipo_str = tipo[1]
            elif isinstance(tipo, str):
                tipo_str = tipo
            else:
                tipo_str = str(tipo) if tipo else None
        else:
            tipo_str = None
        
        manejo = tmpl.get('x_studio_categora_tipo_de_manejo')
        if manejo:
            if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
                manejo_str = manejo[1]
            elif isinstance(manejo, str):
                manejo_str = manejo
            else:
                manejo_str = str(manejo) if manejo else None
        else:
            manejo_str = None
        
        template_map_compras[tmpl['id']] = {
            'tipo': tipo_str or 'Sin tipo',
            'manejo': manejo_str or 'Sin manejo'
        }

# ============================================================================
# 2. OBTENER TODAS LAS VENTAS (FACTURAS CLIENTES)
# ============================================================================
print("\n🔄 Obteniendo VENTAS (Facturas de Cliente)...")

# Incluye líneas CON producto (categoría PRODUCTOS) y SIN producto (texto libre)
# Excluye cuentas de servicios, otros ingresos y activos fijos
ventas_lineas = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.payment_state', '!=', 'reversed'],  # Excluir facturas revertidas
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['display_type', '=', 'product'],  # Solo líneas de producto, excluir COGS
        ['account_id.code', 'not in', ['41010202', '43010111', '71010204']],  # Excluir servicios/otros/activos
        '|',  # OR condition
            ['product_id', '=', False],  # Incluir texto libre
            '&',  # AND condition para productos
                ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
                ['product_id.type', '!=', 'service'],
        ['date', '>=', FECHA_DESDE],
        ['date', '<=', FECHA_HASTA]
    ],
    ['product_id', 'quantity', 'debit', 'credit', 'account_id', 'date', 'move_id', 'name'],
    limit=100000
)

print(f"✓ Total líneas de ventas: {len(ventas_lineas):,}")

# Obtener información de productos para ventas (busca por ID, incluirá archivados)
if ventas_lineas:
    prod_ids_ventas = list(set([l.get('product_id', [None])[0] for l in ventas_lineas if l.get('product_id')]))
    
    # Búsqueda directa por IDs (incluye archivados automáticamente)
    productos_ventas_raw = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'product.product', 'read',
        [prod_ids_ventas, ['id', 'name', 'default_code', 'product_tmpl_id', 'categ_id', 'active', 'type']]
    )
    
    productos_ventas = productos_ventas_raw if productos_ventas_raw else []
    
    productos_activos = sum(1 for p in productos_ventas if p.get('active', True))
    productos_archivados = len(productos_ventas) - productos_activos
    print(f"   - Productos activos: {productos_activos}")
    print(f"   - Productos archivados: {productos_archivados}")
    
    product_map_ventas = {p['id']: p for p in productos_ventas}
    
    template_ids_ventas = list(set([p.get('product_tmpl_id', [None])[0] for p in productos_ventas if p.get('product_tmpl_id')]))
    
    templates_ventas_raw = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'product.template', 'read',
        [template_ids_ventas, ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo', 'active']]
    )
    
    templates_ventas = templates_ventas_raw if templates_ventas_raw else []
    
    template_map_ventas = {}
    for tmpl in templates_ventas:
        tipo = tmpl.get('x_studio_sub_categora')
        if tipo:
            if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
                tipo_str = tipo[1]
            elif isinstance(tipo, str):
                tipo_str = tipo
            else:
                tipo_str = str(tipo) if tipo else None
        else:
            tipo_str = None
        
        manejo = tmpl.get('x_studio_categora_tipo_de_manejo')
        if manejo:
            if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
                manejo_str = manejo[1]
            elif isinstance(manejo, str):
                manejo_str = manejo
            else:
                manejo_str = str(manejo) if manejo else None
        else:
            manejo_str = None
        
        template_map_ventas[tmpl['id']] = {
            'tipo': tipo_str or 'Sin tipo',
            'manejo': manejo_str or 'Sin manejo'
        }

# ============================================================================
# 3. PREPARAR DATOS PARA EXCEL - COMPRAS
# ============================================================================
print("\n📊 Preparando datos de COMPRAS para Excel...")

compras_data = []
for linea in compras_lineas:
    prod_id = linea.get('product_id', [None])[0]
    if not prod_id:
        continue
    
    producto = product_map_compras.get(prod_id, {})
    tmpl_id = producto.get('product_tmpl_id', [None])[0] if producto.get('product_tmpl_id') else None
    template_info = template_map_compras.get(tmpl_id, {}) if tmpl_id else {}
    
    categ = producto.get('categ_id', [None, ''])
    categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
    
    prod_name = producto.get('name', 'Desconocido')
    
    account = linea.get('account_id', [None, ''])
    account_name = account[1] if isinstance(account, (list, tuple)) else str(account)
    
    move = linea.get('move_id', [None, ''])
    move_name = move[1] if isinstance(move, (list, tuple)) else str(move)
    
    fecha = linea.get('date', '')
    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d') if fecha else None
    
    compras_data.append({
        'Fecha': fecha,
        'Temporada': fecha_obj.year if fecha_obj else None,  # Temporada siguiente
        'Año': fecha_obj.year if fecha_obj else None,
        'Mes': fecha_obj.month if fecha_obj else None,
        'Tipo Movimiento': 'COMPRA',
        'Factura': move_name,
        'Producto ID': prod_id,
        'Producto': prod_name,
        'Código': producto.get('default_code', ''),
        'Producto Activo': 'Sí' if producto.get('active', True) else 'No (Archivado)',
        'Categoría': categ_name,
        'Tipo Fruta': template_info.get('tipo', 'Sin tipo'),
        'Manejo': template_info.get('manejo', 'Sin manejo'),
        'Cuenta': account_name,
        'Cantidad (kg)': linea.get('quantity', 0),
        'Débito': linea.get('debit', 0),
        'Crédito': linea.get('credit', 0),
        'Monto': linea.get('debit', 0),  # Para compras, el monto es el débito
        'Precio/kg': linea.get('debit', 0) / linea.get('quantity', 1) if linea.get('quantity', 0) > 0 else 0
    })

df_compras = pd.DataFrame(compras_data)
print(f"✓ Filas de compras: {len(df_compras):,}")

# ============================================================================
# 4. PREPARAR DATOS PARA EXCEL - VENTAS
# ============================================================================
print("\n📊 Preparando datos de VENTAS para Excel...")

ventas_data = []

# Palabras clave a excluir en texto libre (basura)
EXCLUIR_KEYWORDS = [
    'FLETE', 'FREIGHT',
    'TERMOGRAFO', 'THERMOGRAPH',
    'PALLET', 'TARIMA',
    'ARRENDAMIENTO', 'ARRIENDO', 'RENTAL',
    'SERVOCOP', 'REPALETIZACION',
    'TRACTOR', 'MTD', 'FIERRO'
]

for linea in ventas_lineas:
    prod_id = linea.get('product_id', [None])[0] if linea.get('product_id') else None
    
    # Si NO hay product_id, es una línea de texto libre
    if not prod_id:
        prod_name = str(linea.get('name', '') or '').strip()
        
        # Excluir si está vacío o contiene keywords de basura
        if not prod_name or prod_name.upper() in ['N/A', 'FALSE', 'NONE']:
            continue
        
        # Excluir si contiene palabras clave de basura
        prod_name_upper = prod_name.upper()
        if any(keyword in prod_name_upper for keyword in EXCLUIR_KEYWORDS):
            continue
        
        categ_name = 'TEXTO LIBRE'
        tipo_fruta = 'Sin tipo'
        manejo = 'Sin manejo'
        codigo = ''
        activo = 'N/A'
    else:
        # Si hay product_id, obtener toda la info del producto
        producto = product_map_ventas.get(prod_id, {})
        tmpl_id = producto.get('product_tmpl_id', [None])[0] if producto.get('product_tmpl_id') else None
        template_info = template_map_ventas.get(tmpl_id, {}) if tmpl_id else {}
        
        categ = producto.get('categ_id', [None, ''])
        categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
        
        prod_name = producto.get('name', 'Desconocido')
        tipo_fruta = template_info.get('tipo', 'Sin tipo')
        manejo = template_info.get('manejo', 'Sin manejo')
        codigo = producto.get('default_code', '')
        activo = 'Sí' if producto.get('active', True) else 'No (Archivado)'
    
    account = linea.get('account_id', [None, ''])
    account_name = account[1] if isinstance(account, (list, tuple)) else str(account)
    
    move = linea.get('move_id', [None, ''])
    move_name = move[1] if isinstance(move, (list, tuple)) else str(move)
    
    fecha = linea.get('date', '')
    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d') if fecha else None
    
    # Calcular monto neto (credit - debit)
    monto_neto = linea.get('credit', 0) - linea.get('debit', 0)
    
    ventas_data.append({
        'Fecha': fecha,
        'Temporada': fecha_obj.year if fecha_obj else None,
        'Año': fecha_obj.year if fecha_obj else None,
        'Mes': fecha_obj.month if fecha_obj else None,
        'Tipo Movimiento': 'VENTA',
        'Factura': move_name,
        'Producto ID': prod_id if prod_id else 'TEXTO LIBRE',
        'Producto': prod_name,
        'Código': codigo,
        'Producto Activo': activo,
        'Categoría': categ_name,
        'Tipo Fruta': tipo_fruta,
        'Manejo': manejo,
        'Cuenta': account_name,
        'Cantidad (kg)': linea.get('quantity', 0),
        'Débito': linea.get('debit', 0),
        'Crédito': linea.get('credit', 0),
        'Monto': monto_neto,  # Monto neto (credit - debit)
        'Precio/kg': monto_neto / abs(linea.get('quantity', 1)) if linea.get('quantity', 0) != 0 else 0
    })

df_ventas = pd.DataFrame(ventas_data)
print(f"✓ Filas de ventas: {len(df_ventas):,}")

# ============================================================================
# 5. EXPORTAR A EXCEL
# ============================================================================
print("\n💾 Exportando a Excel...")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"stock_teorico_detalle_{timestamp}.xlsx"

with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    # Hoja 1: Todas las compras
    df_compras.to_excel(writer, sheet_name='Compras Detalle', index=False)
    
    # Hoja 2: Todas las ventas
    df_ventas.to_excel(writer, sheet_name='Ventas Detalle', index=False)
    
    # Hoja 3: Resumen por temporada - Compras
    if not df_compras.empty:
        resumen_compras = df_compras.groupby(['Temporada', 'Tipo Fruta', 'Manejo']).agg({
            'Cantidad (kg)': 'sum',
            'Monto': 'sum'
        }).reset_index()
        resumen_compras['Precio/kg'] = resumen_compras['Monto'] / resumen_compras['Cantidad (kg)']
        resumen_compras.to_excel(writer, sheet_name='Resumen Compras', index=False)
    
    # Hoja 4: Resumen por temporada - Ventas
    if not df_ventas.empty:
        resumen_ventas = df_ventas.groupby(['Temporada', 'Tipo Fruta', 'Manejo']).agg({
            'Cantidad (kg)': 'sum',
            'Monto': 'sum'
        }).reset_index()
        resumen_ventas['Precio/kg'] = resumen_ventas['Monto'] / abs(resumen_ventas['Cantidad (kg)'])
        resumen_ventas.to_excel(writer, sheet_name='Resumen Ventas', index=False)
    
    # Hoja 5: Resumen consolidado
    df_todos = pd.concat([df_compras, df_ventas], ignore_index=True)
    if not df_todos.empty:
        resumen_consolidado = df_todos.groupby(['Temporada', 'Tipo Movimiento', 'Tipo Fruta', 'Manejo']).agg({
            'Cantidad (kg)': 'sum',
            'Monto': 'sum'
        }).reset_index()
        resumen_consolidado.to_excel(writer, sheet_name='Resumen Consolidado', index=False)

print(f"✅ Archivo exportado: {filename}")

# ============================================================================
# 6. RESUMEN EN CONSOLA POR AÑO
# ============================================================================
print("\n" + "=" * 140)
print("RESUMEN POR AÑO EN CONSOLA")
print("=" * 140)

df_todos = pd.concat([df_compras, df_ventas], ignore_index=True)

for ano in sorted(df_todos['Temporada'].dropna().unique()):
    df_temp = df_todos[df_todos['Temporada'] == ano]
    
    print(f"\n{'=' * 140}")
    print(f"AÑO {int(ano)}")
    print("=" * 140)
    
    # Compras
    df_compras_temp = df_temp[df_temp['Tipo Movimiento'] == 'COMPRA']
    total_kg_compras = df_compras_temp['Cantidad (kg)'].sum()
    total_monto_compras = df_compras_temp['Monto'].sum()
    
    print(f"\n📦 COMPRAS:")
    print(f"   Total: {total_kg_compras:,.2f} kg  |  ${total_monto_compras:,.2f}  |  ${(total_monto_compras/total_kg_compras if total_kg_compras > 0 else 0):,.2f}/kg")
    
    if not df_compras_temp.empty:
        print(f"\n   Por Tipo de Fruta:")
        compras_por_tipo = df_compras_temp.groupby('Tipo Fruta').agg({
            'Cantidad (kg)': 'sum',
            'Monto': 'sum'
        }).sort_values('Cantidad (kg)', ascending=False)
        
        for tipo, row in compras_por_tipo.iterrows():
            pct = (row['Cantidad (kg)'] / total_kg_compras * 100) if total_kg_compras > 0 else 0
            precio = row['Monto'] / row['Cantidad (kg)'] if row['Cantidad (kg)'] > 0 else 0
            print(f"      {tipo:20} {row['Cantidad (kg)']:>12,.2f} kg ({pct:>5.1f}%)  ${row['Monto']:>15,.2f}  ${precio:>8,.2f}/kg")
    
    # Ventas
    df_ventas_temp = df_temp[df_temp['Tipo Movimiento'] == 'VENTA']
    total_kg_ventas = df_ventas_temp['Cantidad (kg)'].sum()
    total_monto_ventas = df_ventas_temp['Monto'].sum()
    
    print(f"\n💰 VENTAS:")
    print(f"   Total: {total_kg_ventas:,.2f} kg  |  ${total_monto_ventas:,.2f}  |  ${(total_monto_ventas/total_kg_ventas if total_kg_ventas > 0 else 0):,.2f}/kg")
    
    if not df_ventas_temp.empty:
        print(f"\n   Por Tipo de Fruta:")
        ventas_por_tipo = df_ventas_temp.groupby('Tipo Fruta').agg({
            'Cantidad (kg)': 'sum',
            'Monto': 'sum'
        }).sort_values('Cantidad (kg)', ascending=False)
        
        for tipo, row in ventas_por_tipo.iterrows():
            pct = (row['Cantidad (kg)'] / total_kg_ventas * 100) if total_kg_ventas > 0 else 0
            precio = row['Monto'] / abs(row['Cantidad (kg)']) if row['Cantidad (kg)'] != 0 else 0
            print(f"      {tipo:20} {row['Cantidad (kg)']:>12,.2f} kg ({pct:>5.1f}%)  ${row['Monto']:>15,.2f}  ${precio:>8,.2f}/kg")

print("\n" + "=" * 140)
print("PROCESO COMPLETADO")
print("=" * 140)
print(f"\n📁 Archivo generado: {filename}")
print(f"📊 Total compras: {len(df_compras):,} líneas")
print(f"📊 Total ventas: {len(df_ventas):,} líneas")
