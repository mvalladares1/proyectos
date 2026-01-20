"""
Script de debug para analizar compras en stock teórico
Objetivo: Entender por qué las compras son mucho menores de lo esperado
"""
import sys
import os
from datetime import datetime

# Agregar path del backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.odoo_client import OdooClient

def debug_compras():
    """Analiza compras con diferentes filtros para entender discrepancias."""
    
    # Credenciales
    username = input("Usuario Odoo: ")
    password = input("API Key: ")
    
    fecha_desde = "2022-11-01"
    fecha_hasta = "2026-01-20"
    
    odoo = OdooClient(username=username, password=password)
    
    print("\n" + "="*80)
    print("ANÁLISIS DE COMPRAS - STOCK TEÓRICO")
    print("="*80)
    print(f"Período: {fecha_desde} → {fecha_hasta}")
    print("="*80 + "\n")
    
    # =========================================================================
    # 1. TODAS LAS FACTURAS DE COMPRA (in_invoice) POSTED
    # =========================================================================
    print("\n1️⃣  TODAS LAS FACTURAS DE COMPRA (in_invoice posted)")
    print("-" * 80)
    
    todas_facturas = odoo.search_read(
        'account.move',
        [
            ['move_type', '=', 'in_invoice'],
            ['state', '=', 'posted'],
            ['invoice_date', '>=', fecha_desde],
            ['invoice_date', '<=', fecha_hasta]
        ],
        ['name', 'invoice_date', 'amount_total'],
        limit=100000
    )
    
    print(f"Total facturas: {len(todas_facturas)}")
    total_monto = sum(f.get('amount_total', 0) for f in todas_facturas)
    print(f"Monto total: ${total_monto:,.2f}")
    
    # =========================================================================
    # 2. LÍNEAS DE FACTURAS CON PRODUCTO
    # =========================================================================
    print("\n2️⃣  LÍNEAS DE FACTURAS CON PRODUCTO")
    print("-" * 80)
    
    lineas_con_producto = odoo.search_read(
        'account.move.line',
        [
            ['move_id.move_type', '=', 'in_invoice'],
            ['move_id.state', '=', 'posted'],
            ['product_id', '!=', False],
            ['date', '>=', fecha_desde],
            ['date', '<=', fecha_hasta]
        ],
        ['product_id', 'quantity', 'debit', 'credit', 'balance', 'price_unit', 'name'],
        limit=100000
    )
    
    print(f"Total líneas con producto: {len(lineas_con_producto)}")
    total_debit = sum(l.get('debit', 0) for l in lineas_con_producto)
    total_quantity = sum(l.get('quantity', 0) for l in lineas_con_producto)
    print(f"Total debit: ${total_debit:,.2f}")
    print(f"Total quantity: {total_quantity:,.2f}")
    
    # =========================================================================
    # 3. LÍNEAS CON PRODUCTO Y DEBIT > 0 (FILTRO ACTUAL)
    # =========================================================================
    print("\n3️⃣  LÍNEAS CON PRODUCTO, QUANTITY > 0 Y DEBIT > 0 (FILTRO ACTUAL)")
    print("-" * 80)
    
    lineas_filtradas = odoo.search_read(
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
        ['product_id', 'quantity', 'debit', 'account_id', 'name'],
        limit=100000
    )
    
    print(f"Total líneas filtradas: {len(lineas_filtradas)}")
    total_debit_filtrado = sum(l.get('debit', 0) for l in lineas_filtradas)
    total_qty_filtrado = sum(l.get('quantity', 0) for l in lineas_filtradas)
    print(f"Total debit: ${total_debit_filtrado:,.2f}")
    print(f"Total quantity: {total_qty_filtrado:,.2f}")
    
    # Ver distribución de cuentas
    cuentas_dist = {}
    for linea in lineas_filtradas:
        acc = linea.get('account_id')
        acc_code = acc[1] if isinstance(acc, (list, tuple)) else str(acc)
        cuentas_dist[acc_code] = cuentas_dist.get(acc_code, 0) + 1
    
    print(f"\nDistribución por cuenta contable (top 10):")
    for cuenta, count in sorted(cuentas_dist.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {cuenta}: {count} líneas")
    
    # =========================================================================
    # 4. PRODUCTOS CON x_studio FIELDS
    # =========================================================================
    print("\n4️⃣  ANÁLISIS DE PRODUCTOS CON CAMPOS x_studio")
    print("-" * 80)
    
    prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas_filtradas if l.get('product_id')]))
    print(f"Productos únicos en líneas filtradas: {len(prod_ids)}")
    
    productos = odoo.search_read(
        'product.product',
        [['id', 'in', prod_ids]],
        ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo', 'categ_id'],
        limit=100000
    )
    
    con_tipo = 0
    con_manejo = 0
    con_ambos = 0
    sin_tipo = []
    sin_manejo = []
    sin_ambos = []
    
    for prod in productos:
        tipo = prod.get('x_studio_sub_categora')
        manejo = prod.get('x_studio_categora_tipo_de_manejo')
        
        # Normalizar tipo
        if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
            tipo_str = tipo[1]
        elif isinstance(tipo, str) and tipo:
            tipo_str = tipo
        else:
            tipo_str = None
        
        # Normalizar manejo
        if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
            manejo_str = manejo[1]
        elif isinstance(manejo, str) and manejo:
            manejo_str = manejo
        else:
            manejo_str = None
        
        if tipo_str:
            con_tipo += 1
        else:
            sin_tipo.append(prod.get('name', 'N/A'))
        
        if manejo_str:
            con_manejo += 1
        else:
            sin_manejo.append(prod.get('name', 'N/A'))
        
        if tipo_str and manejo_str:
            con_ambos += 1
        else:
            sin_ambos.append(prod.get('name', 'N/A'))
    
    print(f"Productos con tipo de fruta: {con_tipo} ({con_tipo/len(productos)*100:.1f}%)")
    print(f"Productos con tipo de manejo: {con_manejo} ({con_manejo/len(productos)*100:.1f}%)")
    print(f"Productos con AMBOS campos: {con_ambos} ({con_ambos/len(productos)*100:.1f}%)")
    print(f"Productos sin algún campo: {len(productos) - con_ambos}")
    
    # Mostrar ejemplos de productos CON ambos campos
    print(f"\n📋 LISTA DE PRODUCTOS CON TIPO Y MANEJO ({con_ambos} productos):")
    print("-" * 80)
    
    productos_con_ambos = []
    for prod in productos:
        tipo = prod.get('x_studio_sub_categora')
        manejo = prod.get('x_studio_categora_tipo_de_manejo')
        
        if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
            tipo_str = tipo[1]
        elif isinstance(tipo, str) and tipo:
            tipo_str = tipo
        else:
            tipo_str = None
        
        if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
            manejo_str = manejo[1]
        elif isinstance(manejo, str) and manejo:
            manejo_str = manejo
        else:
            manejo_str = None
        
        if tipo_str and manejo_str:
            productos_con_ambos.append({
                'id': prod['id'],
                'nombre': prod.get('name', 'N/A'),
                'tipo': tipo_str,
                'manejo': manejo_str,
                'categoria': prod.get('categ_id', ['', ''])[1] if isinstance(prod.get('categ_id'), (list, tuple)) else str(prod.get('categ_id', ''))
            })
    
    # Calcular kg y monto por producto
    stats_productos_con_ambos = {}
    for linea in lineas_filtradas:
        prod_id = linea.get('product_id', [None])[0]
        prod_match = next((p for p in productos_con_ambos if p['id'] == prod_id), None)
        if prod_match:
            if prod_id not in stats_productos_con_ambos:
                stats_productos_con_ambos[prod_id] = {
                    **prod_match,
                    'kg': 0,
                    'monto': 0
                }
            stats_productos_con_ambos[prod_id]['kg'] += linea.get('quantity', 0)
            stats_productos_con_ambos[prod_id]['monto'] += linea.get('debit', 0)
    
    # Ordenar por monto
    productos_ordenados = sorted(stats_productos_con_ambos.values(), key=lambda x: x['monto'], reverse=True)
    
    for i, prod in enumerate(productos_ordenados, 1):
        print(f"{i:2d}. {prod['nombre'][:45]:<45} | {prod['tipo']:<15} | {prod['manejo']:<15}")
        print(f"    Kg: {prod['kg']:>12,.2f} | Monto: ${prod['monto']:>15,.2f}")
        print(f"    Categoría: {prod['categoria']}")
        print()
    
    # =========================================================================
    # 5. CALCULAR MONTO/KG DE PRODUCTOS FILTRADOS
    # =========================================================================
    print("\n5️⃣  MONTO Y KG DE PRODUCTOS CON/SIN x_studio FIELDS")
    print("-" * 80)
    
    productos_map = {}
    for prod in productos:
        tipo = prod.get('x_studio_sub_categora')
        manejo = prod.get('x_studio_categora_tipo_de_manejo')
        
        if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
            tipo_str = tipo[1]
        elif isinstance(tipo, str) and tipo:
            tipo_str = tipo
        else:
            tipo_str = None
        
        if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
            manejo_str = manejo[1]
        elif isinstance(manejo, str) and manejo:
            manejo_str = manejo
        else:
            manejo_str = None
        
        productos_map[prod['id']] = {
            'tiene_tipo': bool(tipo_str),
            'tiene_manejo': bool(manejo_str),
            'tiene_ambos': bool(tipo_str and manejo_str)
        }
    
    # Calcular totales por categoría
    kg_con_ambos = 0
    monto_con_ambos = 0
    kg_sin_ambos = 0
    monto_sin_ambos = 0
    
    for linea in lineas_filtradas:
        prod_id = linea.get('product_id', [None])[0]
        if prod_id in productos_map:
            qty = linea.get('quantity', 0)
            debit = linea.get('debit', 0)
            
            if productos_map[prod_id]['tiene_ambos']:
                kg_con_ambos += qty
                monto_con_ambos += debit
            else:
                kg_sin_ambos += qty
                monto_sin_ambos += debit
    
    print(f"CON tipo y manejo:")
    print(f"  Kg: {kg_con_ambos:,.2f}")
    print(f"  Monto: ${monto_con_ambos:,.2f}")
    
    print(f"\nSIN tipo o manejo:")
    print(f"  Kg: {kg_sin_ambos:,.2f}")
    print(f"  Monto: ${monto_sin_ambos:,.2f}")
    
    print(f"\n⚠️  SE ESTÁ PERDIENDO:")
    print(f"  {kg_sin_ambos:,.2f} kg (${monto_sin_ambos:,.2f})")
    print(f"  Esto representa {kg_sin_ambos/(kg_con_ambos+kg_sin_ambos)*100:.1f}% del total")
    
    # =========================================================================
    # 6. EJEMPLOS DE PRODUCTOS SIN CAMPOS
    # =========================================================================
    print("\n6️⃣  EJEMPLOS DE PRODUCTOS SIN TIPO/MANEJO (Top 10 por monto)")
    print("-" * 80)
    
    productos_sin_ambos_stats = {}
    
    for linea in lineas_filtradas:
        prod_id = linea.get('product_id', [None])[0]
        if prod_id in productos_map and not productos_map[prod_id]['tiene_ambos']:
            if prod_id not in productos_sin_ambos_stats:
                prod_obj = next((p for p in productos if p['id'] == prod_id), None)
                productos_sin_ambos_stats[prod_id] = {
                    'nombre': prod_obj.get('name', 'N/A') if prod_obj else 'N/A',
                    'kg': 0,
                    'monto': 0
                }
            
            productos_sin_ambos_stats[prod_id]['kg'] += linea.get('quantity', 0)
            productos_sin_ambos_stats[prod_id]['monto'] += linea.get('debit', 0)
    
    top_sin_campos = sorted(productos_sin_ambos_stats.items(), key=lambda x: x[1]['monto'], reverse=True)[:10]
    
    for prod_id, stats in top_sin_campos:
        print(f"  {stats['nombre'][:50]}")
        print(f"    Kg: {stats['kg']:,.2f} | Monto: ${stats['monto']:,.2f}")
    
    # =========================================================================
    # RESUMEN FINAL
    # =========================================================================
    print("\n" + "="*80)
    print("RESUMEN")
    print("="*80)
    print(f"Facturas totales: {len(todas_facturas)} (${total_monto:,.2f})")
    print(f"Líneas con producto: {len(lineas_con_producto)} ({total_quantity:,.2f} kg, ${total_debit:,.2f})")
    print(f"Líneas filtradas (qty>0, debit>0): {len(lineas_filtradas)} ({total_qty_filtrado:,.2f} kg, ${total_debit_filtrado:,.2f})")
    print(f"")
    print(f"Productos con tipo Y manejo: {con_ambos}/{len(productos)} ({con_ambos/len(productos)*100:.1f}%)")
    print(f"  → {kg_con_ambos:,.2f} kg (${monto_con_ambos:,.2f})")
    print(f"")
    print(f"Productos SIN tipo O manejo: {len(productos)-con_ambos}/{len(productos)} ({(len(productos)-con_ambos)/len(productos)*100:.1f}%)")
    print(f"  → {kg_sin_ambos:,.2f} kg (${monto_sin_ambos:,.2f}) ⚠️  PERDIDOS")
    print("="*80)
    
    print("\n💡 RECOMENDACIÓN:")
    if kg_sin_ambos > kg_con_ambos * 0.1:
        print("   Hay una cantidad significativa de compras sin clasificar.")
        print("   Deberías asignar tipo de fruta y manejo a estos productos en Odoo.")
    else:
        print("   La mayoría de las compras están clasificadas correctamente.")

if __name__ == "__main__":
    debug_compras()
