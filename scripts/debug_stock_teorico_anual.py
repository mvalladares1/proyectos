"""
Debug: Análisis de Stock Teórico Anual
Diagnostica por qué no se encuentran datos en compras y ventas
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

# Configuración
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Años a probar
ANIOS = [2024, 2025, 2026]
FECHA_CORTE = "10-31"

print("=" * 140)
print("DEBUG: STOCK TEÓRICO ANUAL - DIAGNÓSTICO COMPLETO")
print("=" * 140)

odoo = OdooClient(username=USERNAME, password=PASSWORD)

for anio in ANIOS:
    print(f"\n{'=' * 140}")
    print(f"AÑO {anio}")
    print("=" * 140)
    
    fecha_desde = f"{anio}-01-01"
    
    # Determinar fecha hasta según el año
    if anio < datetime.now().year:
        fecha_hasta = f"{anio}-{FECHA_CORTE}"
    elif anio == datetime.now().year:
        fecha_corte_completa = f"{anio}-{FECHA_CORTE}"
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        fecha_hasta = min(fecha_corte_completa, fecha_hoy)
    else:
        fecha_hasta = f"{anio}-{FECHA_CORTE}"
    
    print(f"\nPeríodo: {fecha_desde} hasta {fecha_hasta}")
    
    # ============================================================================
    # 1. ANÁLISIS DE COMPRAS (FACTURAS DE PROVEEDOR)
    # ============================================================================
    print(f"\n{'─' * 140}")
    print("1. ANÁLISIS DE COMPRAS (Facturas de Proveedor)")
    print("─" * 140)
    
    # Buscar líneas de factura de proveedor
    lineas_compra = odoo.search_read(
        'account.move.line',
        [
            ['move_id.move_type', '=', 'in_invoice'],
            ['move_id.state', '=', 'posted'],
            ['product_id', '!=', False],
            ['date', '>=', fecha_desde],
            ['date', '<=', fecha_hasta],
            ['quantity', '>', 0],
            ['debit', '>', 0]
        ],
        ['product_id', 'quantity', 'debit', 'account_id', 'date'],
        limit=100000
    )
    
    print(f"✓ Líneas de factura encontradas: {len(lineas_compra)}")
    
    if lineas_compra:
        # Mostrar primeras 3 líneas
        print(f"\n  Muestra de líneas (primeras 3):")
        for i, linea in enumerate(lineas_compra[:3]):
            print(f"    Línea {i+1}:")
            print(f"      - Producto ID: {linea.get('product_id', [None])[0]}")
            print(f"      - Cantidad: {linea.get('quantity', 0):.2f} kg")
            print(f"      - Monto: ${linea.get('debit', 0):,.2f}")
            print(f"      - Fecha: {linea.get('date')}")
            account = linea.get('account_id')
            if account:
                print(f"      - Cuenta: {account[1] if isinstance(account, (list, tuple)) else account}")
        
        # Obtener productos únicos
        prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas_compra if l.get('product_id')]))
        
        productos = odoo.search_read(
            'product.product',
            [['id', 'in', prod_ids]],
            ['id', 'name', 'default_code', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo', 'categ_id'],
            limit=100000
        )
        
        print(f"\n✓ Productos únicos encontrados: {len(productos)}")
        
        # Analizar clasificación de productos
        productos_con_tipo = 0
        productos_con_manejo = 0
        productos_completos = 0
        categorias = {}
        
        print(f"\n  Análisis de clasificación:")
        
        for prod in productos:
            categ = prod.get('categ_id')
            categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
            
            categorias[categ_name] = categorias.get(categ_name, 0) + 1
            
            tipo = prod.get('x_studio_sub_categora')
            tipo_str = tipo[1] if isinstance(tipo, (list, tuple)) and len(tipo) > 1 else None
            
            manejo = prod.get('x_studio_categora_tipo_de_manejo')
            manejo_str = manejo[1] if isinstance(manejo, (list, tuple)) and len(manejo) > 1 else None
            
            if tipo_str:
                productos_con_tipo += 1
            if manejo_str:
                productos_con_manejo += 1
            if tipo_str and manejo_str:
                productos_completos += 1
        
        print(f"    - Productos con Tipo de Fruta: {productos_con_tipo} ({productos_con_tipo/len(productos)*100:.1f}%)")
        print(f"    - Productos con Tipo de Manejo: {productos_con_manejo} ({productos_con_manejo/len(productos)*100:.1f}%)")
        print(f"    - Productos COMPLETOS (tipo + manejo): {productos_completos} ({productos_completos/len(productos)*100:.1f}%)")
        
        print(f"\n  Distribución por Categoría:")
        for cat, count in sorted(categorias.items(), key=lambda x: -x[1])[:10]:
            print(f"    - {cat}: {count} productos")
        
        # Mostrar ejemplos de productos completos
        if productos_completos > 0:
            print(f"\n  Ejemplos de productos COMPLETOS (primeros 5):")
            count = 0
            for prod in productos:
                if count >= 5:
                    break
                
                tipo = prod.get('x_studio_sub_categora')
                tipo_str = tipo[1] if isinstance(tipo, (list, tuple)) and len(tipo) > 1 else None
                
                manejo = prod.get('x_studio_categora_tipo_de_manejo')
                manejo_str = manejo[1] if isinstance(manejo, (list, tuple)) and len(manejo) > 1 else None
                
                if tipo_str and manejo_str:
                    categ = prod.get('categ_id')
                    categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
                    
                    print(f"    {count+1}. {prod.get('name', 'Sin nombre')}")
                    print(f"       - Código: {prod.get('default_code', 'N/A')}")
                    print(f"       - Tipo: {tipo_str}")
                    print(f"       - Manejo: {manejo_str}")
                    print(f"       - Categoría: {categ_name}")
                    count += 1
        
        # Calcular totales
        total_kg = sum([l.get('quantity', 0) for l in lineas_compra])
        total_monto = sum([l.get('debit', 0) for l in lineas_compra])
        
        print(f"\n  TOTALES de COMPRAS:")
        print(f"    - Total kg: {total_kg:,.2f}")
        print(f"    - Total monto: ${total_monto:,.2f}")
        print(f"    - Precio promedio: ${total_monto/total_kg:,.2f}/kg" if total_kg > 0 else "N/A")
    
    else:
        print("  ⚠️ No se encontraron líneas de factura de compra")
    
    # ============================================================================
    # 2. ANÁLISIS DE VENTAS (FACTURAS DE CLIENTE)
    # ============================================================================
    print(f"\n{'─' * 140}")
    print("2. ANÁLISIS DE VENTAS (Facturas de Cliente)")
    print("─" * 140)
    
    lineas_venta = odoo.search_read(
        'account.move.line',
        [
            ['move_id.move_type', '=', 'out_invoice'],
            ['move_id.state', '=', 'posted'],
            ['product_id', '!=', False],
            ['date', '>=', fecha_desde],
            ['date', '<=', fecha_hasta],
            ['quantity', '>', 0],
            ['credit', '>', 0]
        ],
        ['product_id', 'quantity', 'credit', 'date'],
        limit=100000
    )
    
    print(f"✓ Líneas de factura encontradas: {len(lineas_venta)}")
    
    if lineas_venta:
        # Mostrar primeras 3 líneas
        print(f"\n  Muestra de líneas (primeras 3):")
        for i, linea in enumerate(lineas_venta[:3]):
            print(f"    Línea {i+1}:")
            print(f"      - Producto ID: {linea.get('product_id', [None])[0]}")
            print(f"      - Cantidad: {linea.get('quantity', 0):.2f} kg")
            print(f"      - Monto: ${linea.get('credit', 0):,.2f}")
            print(f"      - Fecha: {linea.get('date')}")
        
        # Obtener productos únicos
        prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas_venta if l.get('product_id')]))
        
        productos = odoo.search_read(
            'product.product',
            [['id', 'in', prod_ids]],
            ['id', 'name', 'default_code', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo', 'categ_id'],
            limit=100000
        )
        
        print(f"\n✓ Productos únicos encontrados: {len(productos)}")
        
        # Analizar clasificación
        productos_con_tipo = 0
        productos_con_manejo = 0
        productos_completos = 0
        categorias = {}
        
        print(f"\n  Análisis de clasificación:")
        
        for prod in productos:
            categ = prod.get('categ_id')
            categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
            
            categorias[categ_name] = categorias.get(categ_name, 0) + 1
            
            tipo = prod.get('x_studio_sub_categora')
            tipo_str = tipo[1] if isinstance(tipo, (list, tuple)) and len(tipo) > 1 else None
            
            manejo = prod.get('x_studio_categora_tipo_de_manejo')
            manejo_str = manejo[1] if isinstance(manejo, (list, tuple)) and len(manejo) > 1 else None
            
            if tipo_str:
                productos_con_tipo += 1
            if manejo_str:
                productos_con_manejo += 1
            if tipo_str and manejo_str:
                productos_completos += 1
        
        print(f"    - Productos con Tipo de Fruta: {productos_con_tipo} ({productos_con_tipo/len(productos)*100:.1f}%)")
        print(f"    - Productos con Tipo de Manejo: {productos_con_manejo} ({productos_con_manejo/len(productos)*100:.1f}%)")
        print(f"    - Productos COMPLETOS (tipo + manejo): {productos_completos} ({productos_completos/len(productos)*100:.1f}%)")
        
        print(f"\n  Distribución por Categoría:")
        for cat, count in sorted(categorias.items(), key=lambda x: -x[1])[:10]:
            print(f"    - {cat}: {count} productos")
        
        # Calcular totales
        total_kg = sum([l.get('quantity', 0) for l in lineas_venta])
        total_monto = sum([l.get('credit', 0) for l in lineas_venta])
        
        print(f"\n  TOTALES de VENTAS:")
        print(f"    - Total kg: {total_kg:,.2f}")
        print(f"    - Total monto: ${total_monto:,.2f}")
        print(f"    - Precio promedio: ${total_monto/total_kg:,.2f}/kg" if total_kg > 0 else "N/A")
    
    else:
        print("  ⚠️ No se encontraron líneas de factura de venta")

print(f"\n{'=' * 140}")
print("RESUMEN DIAGNÓSTICO")
print("=" * 140)
print("""
Acciones recomendadas:

1. Si NO hay líneas de factura:
   - Verificar que las facturas estén en estado 'posted' 
   - Revisar que tengan productos asociados
   - Confirmar que las fechas sean correctas

2. Si hay líneas pero pocos productos completos:
   - Revisar que los productos tengan campo 'x_studio_sub_categora' (Tipo de Fruta)
   - Revisar que los productos tengan campo 'x_studio_categora_tipo_de_manejo' (Tipo de Manejo)
   - Considerar relajar filtros en el servicio

3. Si todo parece bien pero el servicio no funciona:
   - Verificar que el servicio esté usando los mismos filtros
   - Revisar logs del backend API
   - Confirmar que las fechas se estén parseando correctamente
""")

print("=" * 140)
