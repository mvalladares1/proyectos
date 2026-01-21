"""
DEBUG: Filtrado de Diarios - Facturas Clientes y Proveedores
Filtrar solo asientos contables donde la categoría producto contenga "Producto"
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

# Configuración
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Período de análisis (puedes ajustar)
FECHA_DESDE = "2024-01-01"
FECHA_HASTA = "2024-12-31"

print("=" * 140)
print("DEBUG: DIARIOS FILTRADOS - FACTURAS CLIENTES Y PROVEEDORES")
print("=" * 140)
print(f"Período: {FECHA_DESDE} a {FECHA_HASTA}")
print("=" * 140)

odoo = OdooClient(username=USERNAME, password=PASSWORD)

# ============================================================================
# 1. ANÁLISIS DE FACTURAS DE PROVEEDORES
# ============================================================================
print(f"\n{'=' * 140}")
print("1. FACTURAS DE PROVEEDORES (Compras)")
print("=" * 140)

# Buscar líneas de factura de proveedor con categoría PRODUCTO
lineas_proveedores = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'in_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.journal_id.name', '=', 'Facturas de Proveedores'],
        ['product_id', '!=', False],
        ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTO'],
        ['date', '>=', FECHA_DESDE],
        ['date', '<=', FECHA_HASTA]
    ],
    ['product_id', 'quantity', 'debit', 'credit', 'account_id', 'date', 'move_id'],
    limit=100000
)

print(f"\n✓ Total líneas encontradas: {len(lineas_proveedores)}")

if lineas_proveedores:
    # Estadísticas generales
    total_debit = sum(l.get('debit', 0) for l in lineas_proveedores)
    total_credit = sum(l.get('credit', 0) for l in lineas_proveedores)
    total_quantity = sum(l.get('quantity', 0) for l in lineas_proveedores)
    
    print(f"\n📊 RESUMEN GENERAL:")
    print(f"   - Total Débito: ${total_debit:,.2f}")
    print(f"   - Total Crédito: ${total_credit:,.2f}")
    print(f"   - Cantidad total: {total_quantity:,.2f} kg")
    print(f"   - Precio promedio: ${(total_debit/total_quantity):,.2f}/kg" if total_quantity > 0 else "")
    
    # Obtener productos únicos
    prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas_proveedores if l.get('product_id')]))
    print(f"\n✓ Productos únicos: {len(prod_ids)}")
    
    # Obtener información de productos
    productos = odoo.search_read(
        'product.product',
        [['id', 'in', prod_ids]],
        ['id', 'name', 'default_code', 'product_tmpl_id', 'categ_id'],
        limit=100000
    )
    
    # Analizar categorías
    categorias = {}
    for prod in productos:
        categ = prod.get('categ_id')
        categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
        categorias[categ_name] = categorias.get(categ_name, 0) + 1
    
    print(f"\n📁 DISTRIBUCIÓN POR CATEGORÍA:")
    for cat, count in sorted(categorias.items(), key=lambda x: -x[1]):
        pct = (count / len(productos)) * 100
        print(f"   - {cat}: {count} productos ({pct:.1f}%)")
    
    # Crear mapeo de product.product a template
    product_to_template = {}
    for prod in productos:
        prod_id = prod['id']
        tmpl = prod.get('product_tmpl_id')
        if tmpl:
            tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
            product_to_template[prod_id] = tmpl_id
    
    # Obtener templates únicos
    template_ids = list(set(product_to_template.values()))
    
    templates = odoo.search_read(
        'product.template',
        [['id', 'in', template_ids]],
        ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
        limit=100000
    )
    
    print(f"\n🔍 ANÁLISIS DETALLADO DE CAMPOS:")
    print(f"   Templates obtenidos: {len(templates)}")
    
    # Mapear templates con ANÁLISIS DETALLADO
    template_map = {}
    clasificados_completos = 0
    clasificados_parciales = 0
    sin_clasificar = 0
    
    for tmpl in templates:
        tipo = tmpl.get('x_studio_sub_categora')
        manejo = tmpl.get('x_studio_categora_tipo_de_manejo')
        
        # Analizar tipo
        if tipo:
            if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
                tipo_str = tipo[1]
            elif isinstance(tipo, str):
                tipo_str = tipo
            elif isinstance(tipo, (list, tuple)) and len(tipo) == 1:
                tipo_str = str(tipo[0])
            else:
                tipo_str = None
        else:
            tipo_str = None
        
        # Analizar manejo
        if manejo:
            if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
                manejo_str = manejo[1]
            elif isinstance(manejo, str):
                manejo_str = manejo
            elif isinstance(manejo, (list, tuple)) and len(manejo) == 1:
                manejo_str = str(manejo[0])
            else:
                manejo_str = None
        else:
            manejo_str = None
        
        template_map[tmpl['id']] = {
            'nombre': tmpl.get('name', ''),
            'tipo': tipo_str,
            'manejo': manejo_str,
            'tipo_raw': tipo,
            'manejo_raw': manejo
        }
        
        if tipo_str and manejo_str:
            clasificados_completos += 1
        elif tipo_str or manejo_str:
            clasificados_parciales += 1
        else:
            sin_clasificar += 1
    
    print(f"\n🏷️  CLASIFICACIÓN TIPO/MANEJO:")
    print(f"   - Completos (tipo + manejo): {clasificados_completos} ({clasificados_completos/len(templates)*100:.1f}%)")
    print(f"   - Parciales (solo tipo o manejo): {clasificados_parciales} ({clasificados_parciales/len(templates)*100:.1f}%)")
    print(f"   - Sin clasificar: {sin_clasificar} ({sin_clasificar/len(templates)*100:.1f}%)")
    
    # Mostrar ejemplos de productos CON clasificación (si existen)
    if clasificados_completos > 0:
        print(f"\n✅ EJEMPLOS CON CLASIFICACIÓN COMPLETA (primeros 5):")
        count = 0
        for tmpl_id, tmpl_data in template_map.items():
            if count >= 5:
                break
            if tmpl_data['tipo'] and tmpl_data['manejo']:
                print(f"   {count+1}. {tmpl_data['nombre']}")
                print(f"      - Tipo: {tmpl_data['tipo']}")
                print(f"      - Manejo: {tmpl_data['manejo']}")
                count += 1
    
    # Mostrar ejemplos de productos SIN clasificación completa
    if sin_clasificar > 0 or clasificados_parciales > 0:
        print(f"\n⚠️  EJEMPLOS SIN CLASIFICACIÓN COMPLETA (primeros 3):")
        count = 0
        for tmpl_id, tmpl_data in template_map.items():
            if count >= 3:
                break
            if not (tmpl_data['tipo'] and tmpl_data['manejo']):
                print(f"   {count+1}. {tmpl_data['nombre']}")
                print(f"      - Tipo: {tmpl_data['tipo'] or '❌ FALTA'}")
                print(f"      - Manejo: {tmpl_data['manejo'] or '❌ FALTA'}")
                print(f"      - Tipo (raw): {tmpl_data['tipo_raw']}")
                print(f"      - Manejo (raw): {tmpl_data['manejo_raw']}")
                count += 1
    
    # Mostrar muestra de datos
    print(f"\n📋 MUESTRA DE LÍNEAS (primeras 5):")
    for i, linea in enumerate(lineas_proveedores[:5]):
        prod_id = linea.get('product_id', [None, 'Desconocido'])
        prod_name = prod_id[1] if isinstance(prod_id, (list, tuple)) else str(prod_id)
        
        print(f"\n   Línea {i+1}:")
        print(f"      - Producto: {prod_name}")
        print(f"      - Cantidad: {linea.get('quantity', 0):,.2f} kg")
        print(f"      - Débito: ${linea.get('debit', 0):,.2f}")
        print(f"      - Crédito: ${linea.get('credit', 0):,.2f}")
        print(f"      - Fecha: {linea.get('date')}")
        
        account = linea.get('account_id')
        if account:
            account_name = account[1] if isinstance(account, (list, tuple)) else str(account)
            print(f"      - Cuenta: {account_name}")

else:
    print("\n⚠️  NO se encontraron líneas de facturas de proveedor")

# ============================================================================
# 2. ANÁLISIS DE FACTURAS DE CLIENTES
# ============================================================================
print(f"\n\n{'=' * 140}")
print("2. FACTURAS DE CLIENTES (Ventas)")
print("=" * 140)

# Buscar líneas de factura de cliente con categoría PRODUCTO
lineas_clientes = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.journal_id.name', 'ilike', 'Facturas de Cliente'],
        ['product_id', '!=', False],
        ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTO'],
        ['date', '>=', FECHA_DESDE],
        ['date', '<=', FECHA_HASTA]
    ],
    ['product_id', 'quantity', 'debit', 'credit', 'account_id', 'date', 'move_id'],
    limit=100000
)

print(f"\n✓ Total líneas encontradas: {len(lineas_clientes)}")

if lineas_clientes:
    # Estadísticas generales
    total_debit = sum(l.get('debit', 0) for l in lineas_clientes)
    total_credit = sum(l.get('credit', 0) for l in lineas_clientes)
    total_quantity = sum(l.get('quantity', 0) for l in lineas_clientes)
    
    print(f"\n📊 RESUMEN GENERAL:")
    print(f"   - Total Débito: ${total_debit:,.2f}")
    print(f"   - Total Crédito: ${total_credit:,.2f}")
    print(f"   - Cantidad total: {total_quantity:,.2f} kg")
    print(f"   - Precio promedio: ${(total_credit/abs(total_quantity) if total_quantity != 0 else 0):,.2f}/kg")
    
    # Obtener productos únicos
    prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas_clientes if l.get('product_id')]))
    print(f"\n✓ Productos únicos: {len(prod_ids)}")
    
    # Obtener información de productos
    productos = odoo.search_read(
        'product.product',
        [['id', 'in', prod_ids]],
        ['id', 'name', 'default_code', 'product_tmpl_id', 'categ_id'],
        limit=100000
    )
    
    # Analizar categorías
    categorias = {}
    for prod in productos:
        categ = prod.get('categ_id')
        categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
        categorias[categ_name] = categorias.get(categ_name, 0) + 1
    
    print(f"\n📁 DISTRIBUCIÓN POR CATEGORÍA:")
    for cat, count in sorted(categorias.items(), key=lambda x: -x[1]):
        pct = (count / len(productos)) * 100
        print(f"   - {cat}: {count} productos ({pct:.1f}%)")
    
    # Crear mapeo de product.product a template
    product_to_template = {}
    for prod in productos:
        prod_id = prod['id']
        tmpl = prod.get('product_tmpl_id')
        if tmpl:
            tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
            product_to_template[prod_id] = tmpl_id
    
    # Obtener templates únicos
    template_ids = list(set(product_to_template.values()))
    
    templates = odoo.search_read(
        'product.template',
        [['id', 'in', template_ids]],
        ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
        limit=100000
    )
    
    print(f"\n🔍 ANÁLISIS DETALLADO DE CAMPOS:")
    print(f"   Templates obtenidos: {len(templates)}")
    
    # Mapear templates con ANÁLISIS DETALLADO
    template_map = {}
    clasificados_completos = 0
    clasificados_parciales = 0
    sin_clasificar = 0
    
    for tmpl in templates:
        tipo = tmpl.get('x_studio_sub_categora')
        manejo = tmpl.get('x_studio_categora_tipo_de_manejo')
        
        # Analizar tipo
        if tipo:
            if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
                tipo_str = tipo[1]
            elif isinstance(tipo, str):
                tipo_str = tipo
            elif isinstance(tipo, (list, tuple)) and len(tipo) == 1:
                tipo_str = str(tipo[0])
            else:
                tipo_str = None
        else:
            tipo_str = None
        
        # Analizar manejo
        if manejo:
            if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
                manejo_str = manejo[1]
            elif isinstance(manejo, str):
                manejo_str = manejo
            elif isinstance(manejo, (list, tuple)) and len(manejo) == 1:
                manejo_str = str(manejo[0])
            else:
                manejo_str = None
        else:
            manejo_str = None
        
        template_map[tmpl['id']] = {
            'nombre': tmpl.get('name', ''),
            'tipo': tipo_str,
            'manejo': manejo_str,
            'tipo_raw': tipo,
            'manejo_raw': manejo
        }
        
        if tipo_str and manejo_str:
            clasificados_completos += 1
        elif tipo_str or manejo_str:
            clasificados_parciales += 1
        else:
            sin_clasificar += 1
    
    print(f"\n🏷️  CLASIFICACIÓN TIPO/MANEJO:")
    print(f"   - Completos (tipo + manejo): {clasificados_completos} ({clasificados_completos/len(templates)*100:.1f}%)")
    print(f"   - Parciales (solo tipo o manejo): {clasificados_parciales} ({clasificados_parciales/len(templates)*100:.1f}%)")
    print(f"   - Sin clasificar: {sin_clasificar} ({sin_clasificar/len(templates)*100:.1f}%)")
    
    # Mostrar ejemplos de productos CON clasificación (si existen)
    if clasificados_completos > 0:
        print(f"\n✅ EJEMPLOS CON CLASIFICACIÓN COMPLETA (primeros 5):")
        count = 0
        for tmpl_id, tmpl_data in template_map.items():
            if count >= 5:
                break
            if tmpl_data['tipo'] and tmpl_data['manejo']:
                print(f"   {count+1}. {tmpl_data['nombre']}")
                print(f"      - Tipo: {tmpl_data['tipo']}")
                print(f"      - Manejo: {tmpl_data['manejo']}")
                count += 1
    
    # Mostrar ejemplos de productos SIN clasificación completa
    if sin_clasificar > 0 or clasificados_parciales > 0:
        print(f"\n⚠️  EJEMPLOS SIN CLASIFICACIÓN COMPLETA (primeros 3):")
        count = 0
        for tmpl_id, tmpl_data in template_map.items():
            if count >= 3:
                break
            if not (tmpl_data['tipo'] and tmpl_data['manejo']):
                print(f"   {count+1}. {tmpl_data['nombre']}")
                print(f"      - Tipo: {tmpl_data['tipo'] or '❌ FALTA'}")
                print(f"      - Manejo: {tmpl_data['manejo'] or '❌ FALTA'}")
                print(f"      - Tipo (raw): {tmpl_data['tipo_raw']}")
                print(f"      - Manejo (raw): {tmpl_data['manejo_raw']}")
                count += 1
    
    # Mostrar muestra de datos
    print(f"\n📋 MUESTRA DE LÍNEAS (primeras 5):")
    for i, linea in enumerate(lineas_clientes[:5]):
        prod_id = linea.get('product_id', [None, 'Desconocido'])
        prod_name = prod_id[1] if isinstance(prod_id, (list, tuple)) else str(prod_id)
        
        print(f"\n   Línea {i+1}:")
        print(f"      - Producto: {prod_name}")
        print(f"      - Cantidad: {linea.get('quantity', 0):,.2f} kg")
        print(f"      - Débito: ${linea.get('debit', 0):,.2f}")
        print(f"      - Crédito: ${linea.get('credit', 0):,.2f}")
        print(f"      - Fecha: {linea.get('date')}")
        
        account = linea.get('account_id')
        if account:
            account_name = account[1] if isinstance(account, (list, tuple)) else str(account)
            print(f"      - Cuenta: {account_name}")

else:
    print("\n⚠️  NO se encontraron líneas de facturas de cliente")

# ============================================================================
# 3. COMPARATIVA
# ============================================================================
print(f"\n\n{'=' * 140}")
print("3. COMPARATIVA GENERAL")
print("=" * 140)

print(f"\nFacturas Proveedores (Compras):")
print(f"   - Líneas: {len(lineas_proveedores):,}")
print(f"   - Productos únicos: {len(set([l.get('product_id', [None])[0] for l in lineas_proveedores if l.get('product_id')])) if lineas_proveedores else 0}")

print(f"\nFacturas Clientes (Ventas):")
print(f"   - Líneas: {len(lineas_clientes):,}")
print(f"   - Productos únicos: {len(set([l.get('product_id', [None])[0] for l in lineas_clientes if l.get('product_id')])) if lineas_clientes else 0}")

print(f"\n{'=' * 140}")
print("DEBUG COMPLETADO")
print("=" * 140)
