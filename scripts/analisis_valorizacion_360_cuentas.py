"""
Análisis de Valorización 360 - Cuentas Contables
Compara las cuentas involucradas en:
1. Compras (Facturas de Proveedores)
2. Ventas (Facturas de Cliente)
3. Insumos/Servicios (Consumos en Fabricaciones)
"""
import sys
import os
from datetime import datetime
import pandas as pd
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*160)
print("ANÁLISIS DE VALORIZACIÓN 360 - CUENTAS CONTABLES")
print("="*160)
print("Fabricaciones: Solo insumos/servicios de órdenes que procesaron fruta")
print("="*160)
print()

# ============================================================================
# 1. COMPRAS - Facturas de Proveedores
# ============================================================================
print("📥 ANALIZANDO COMPRAS (Facturas de Proveedores)...")

compras_lineas = odoo.search_read(
    'account.move.line',
    [
        ['parent_state', '=', 'posted'],
        ['move_id.journal_id.name', '=', 'Facturas de Proveedores'],
        ['move_id.move_type', '=', 'in_invoice'],
        ['display_type', '=', 'product']
    ],
    ['id', 'account_id', 'product_id', 'debit', 'credit', 'balance', 'date', 'move_id'],
    limit=10000,
    order='date desc'
)

print(f"✓ Líneas de compras obtenidas: {len(compras_lineas):,}")

# Agrupar por cuenta
compras_por_cuenta = defaultdict(lambda: {'debito': 0, 'credito': 0, 'balance': 0, 'lineas': 0, 'nombre': ''})

for linea in compras_lineas:
    cuenta_id = linea.get('account_id', [None])[0]
    cuenta_nombre = linea.get('account_id', [None, 'N/A'])[1] if linea.get('account_id') else 'N/A'
    
    debito = linea.get('debit', 0) or 0
    credito = linea.get('credit', 0) or 0
    balance = linea.get('balance', 0) or 0
    
    compras_por_cuenta[cuenta_id]['nombre'] = cuenta_nombre
    compras_por_cuenta[cuenta_id]['debito'] += debito
    compras_por_cuenta[cuenta_id]['credito'] += credito
    compras_por_cuenta[cuenta_id]['balance'] += balance
    compras_por_cuenta[cuenta_id]['lineas'] += 1

print(f"✓ Cuentas únicas en compras: {len(compras_por_cuenta)}")

# ============================================================================
# 2. VENTAS - Facturas de Cliente
# ============================================================================
print("\n📤 ANALIZANDO VENTAS (Facturas de Cliente)...")

ventas_lineas = odoo.search_read(
    'account.move.line',
    [
        ['parent_state', '=', 'posted'],
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.payment_state', '!=', 'reversed'],
        ['display_type', '=', 'product']
    ],
    ['id', 'account_id', 'product_id', 'debit', 'credit', 'balance', 'date', 'move_id'],
    limit=10000,
    order='date desc'
)

print(f"✓ Líneas de ventas obtenidas: {len(ventas_lineas):,}")

# Agrupar por cuenta
ventas_por_cuenta = defaultdict(lambda: {'debito': 0, 'credito': 0, 'balance': 0, 'lineas': 0, 'nombre': ''})

for linea in ventas_lineas:
    cuenta_id = linea.get('account_id', [None])[0]
    cuenta_nombre = linea.get('account_id', [None, 'N/A'])[1] if linea.get('account_id') else 'N/A'
    
    debito = linea.get('debit', 0) or 0
    credito = linea.get('credit', 0) or 0
    balance = linea.get('balance', 0) or 0
    
    ventas_por_cuenta[cuenta_id]['nombre'] = cuenta_nombre
    ventas_por_cuenta[cuenta_id]['debito'] += debito
    ventas_por_cuenta[cuenta_id]['credito'] += credito
    ventas_por_cuenta[cuenta_id]['balance'] += balance
    ventas_por_cuenta[cuenta_id]['lineas'] += 1

print(f"✓ Cuentas únicas en ventas: {len(ventas_por_cuenta)}")

# ============================================================================
# 3. INSUMOS/SERVICIOS - Consumos en Fabricaciones con Fruta
# ============================================================================
print("\n🏭 ANALIZANDO INSUMOS/SERVICIOS (Solo fabricaciones con fruta)...")

# Paso 1: Obtener todos los consumos de fabricaciones
print("\n🔍 Paso 1: Obtener consumos de fabricaciones...")
consumos_todos = odoo.search_read(
    'stock.move',
    [
        ['raw_material_production_id', '!=', False],
        ['state', '=', 'done']
    ],
    ['id', 'product_id', 'quantity_done', 'price_unit', 'raw_material_production_id', 'account_move_ids'],
    limit=20000,
    order='date desc'
)

print(f"✓ Total consumos obtenidos: {len(consumos_todos):,}")

# Paso 2: Identificar productos de MP vs Insumos
print("\n📦 Paso 2: Clasificar productos (MP vs Insumos)...")
producto_ids_todos = list(set([c.get('product_id', [None])[0] for c in consumos_todos if c.get('product_id')]))
producto_ids_todos = [x for x in producto_ids_todos if x]

productos_todos = odoo.search_read(
    'product.product',
    [['id', 'in', producto_ids_todos]],
    ['id', 'categ_id'],
    limit=10000
)

productos_mp_ids = set([
    p['id'] for p in productos_todos 
    if p.get('categ_id') and 'PRODUCTOS' in (p.get('categ_id', [None, ''])[1] or '').upper()
])

print(f"✓ Productos de MP (fruta): {len(productos_mp_ids):,}")
print(f"✓ Productos de insumos/servicios: {len(producto_ids_todos) - len(productos_mp_ids):,}")

# Paso 3: Identificar fabricaciones que procesaron fruta
print("\n🏭 Paso 3: Identificar fabricaciones con fruta...")
fabricaciones_con_fruta = set()

for consumo in consumos_todos:
    prod_id = consumo.get('product_id', [None])[0]
    if prod_id in productos_mp_ids:
        orden_id = consumo.get('raw_material_production_id', [None])[0]
        if orden_id:
            fabricaciones_con_fruta.add(orden_id)

print(f"✓ Fabricaciones que procesaron fruta: {len(fabricaciones_con_fruta):,}")

# Paso 4: Filtrar consumos de INSUMOS en fabricaciones con fruta
print("\n💰 Paso 4: Filtrar insumos en fabricaciones con fruta...")
consumos_insumos_fruta = [
    c for c in consumos_todos 
    if c.get('product_id', [None])[0] not in productos_mp_ids  # NO es MP
    and c.get('raw_material_production_id', [None])[0] in fabricaciones_con_fruta  # Está en fabricación con fruta
]

print(f"✓ Consumos de insumos en fabricaciones con fruta: {len(consumos_insumos_fruta):,}")

# Paso 5: Obtener movimientos contables de estos insumos
print("\n📊 Paso 5: Obtener asientos contables de insumos...")
account_move_ids_insumos = []
for consumo in consumos_insumos_fruta:
    account_move_ids = consumo.get('account_move_ids', [])
    if account_move_ids:
        account_move_ids_insumos.extend(account_move_ids)

account_move_ids_insumos = list(set(account_move_ids_insumos))
print(f"✓ Account moves de insumos: {len(account_move_ids_insumos):,}")

# Obtener las líneas contables de estos movimientos de insumos
if account_move_ids_insumos:
    print("\n📊 Obteniendo líneas contables de insumos...")
    
    insumos_lineas = []
    batch_size = 1000
    
    for i in range(0, len(account_move_ids_insumos), batch_size):
        batch = account_move_ids_insumos[i:i+batch_size]
        print(f"   Lote {i//batch_size + 1}/{(len(account_move_ids_insumos)-1)//batch_size + 1}...", end='\r')
        
        batch_lineas = odoo.search_read(
            'account.move.line',
            [['move_id', 'in', batch]],
            ['id', 'account_id', 'product_id', 'debit', 'credit', 'balance', 'date'],
            limit=20000
        )
        
        insumos_lineas.extend(batch_lineas)
    
    print(f"\n✓ Líneas contables de insumos: {len(insumos_lineas):,}")
else:
    insumos_lineas = []
    print("⚠️ No se encontraron movimientos contables de insumos")

# Agrupar por cuenta
insumos_por_cuenta = defaultdict(lambda: {'debito': 0, 'credito': 0, 'balance': 0, 'lineas': 0, 'nombre': ''})

for linea in insumos_lineas:
    cuenta_id = linea.get('account_id', [None])[0]
    cuenta_nombre = linea.get('account_id', [None, 'N/A'])[1] if linea.get('account_id') else 'N/A'
    
    debito = linea.get('debit', 0) or 0
    credito = linea.get('credit', 0) or 0
    balance = linea.get('balance', 0) or 0
    
    insumos_por_cuenta[cuenta_id]['nombre'] = cuenta_nombre
    insumos_por_cuenta[cuenta_id]['debito'] += debito
    insumos_por_cuenta[cuenta_id]['credito'] += credito
    insumos_por_cuenta[cuenta_id]['balance'] += balance
    insumos_por_cuenta[cuenta_id]['lineas'] += 1

print(f"✓ Cuentas únicas en fabricaciones: {len(insumos_por_cuenta)}")

# ============================================================================
# 4. ANÁLISIS COMPARATIVO
# ============================================================================
print("\n" + "="*160)
print("GENERANDO ANÁLISIS COMPARATIVO")
print("="*160)

# Obtener todas las cuentas únicas
todas_cuentas = set(compras_por_cuenta.keys()) | set(ventas_por_cuenta.keys()) | set(insumos_por_cuenta.keys())
todas_cuentas = [c for c in todas_cuentas if c]

print(f"\n✓ Total cuentas únicas involucradas: {len(todas_cuentas)}")

# Crear DataFrame comparativo
data_comparativo = []

for cuenta_id in todas_cuentas:
    # Datos de compras
    compra = compras_por_cuenta.get(cuenta_id, {})
    # Datos de ventas
    venta = ventas_por_cuenta.get(cuenta_id, {})
    # Datos de insumos
    insumo = insumos_por_cuenta.get(cuenta_id, {})
    
    # Nombre de cuenta (tomar el primero disponible)
    nombre_cuenta = compra.get('nombre') or venta.get('nombre') or insumo.get('nombre') or 'N/A'
    
    fila = {
        'Cuenta': nombre_cuenta,
        'En Compras': 'Sí' if cuenta_id in compras_por_cuenta else 'No',
        'En Ventas': 'Sí' if cuenta_id in ventas_por_cuenta else 'No',
        'En Fabricaciones': 'Sí' if cuenta_id in insumos_por_cuenta else 'No',
        'Compras Débito': compra.get('debito', 0),
        'Compras Crédito': compra.get('credito', 0),
        'Compras Balance': compra.get('balance', 0),
        'Compras Líneas': compra.get('lineas', 0),
        'Ventas Débito': venta.get('debito', 0),
        'Ventas Crédito': venta.get('credito', 0),
        'Ventas Balance': venta.get('balance', 0),
        'Ventas Líneas': venta.get('lineas', 0),
        'Fabricaciones Débito': insumo.get('debito', 0),
        'Fabricaciones Crédito': insumo.get('credito', 0),
        'Fabricaciones Balance': insumo.get('balance', 0),
        'Fabricaciones Líneas': insumo.get('lineas', 0),
        'Total Débito': compra.get('debito', 0) + venta.get('debito', 0) + insumo.get('debito', 0),
        'Total Crédito': compra.get('credito', 0) + venta.get('credito', 0) + insumo.get('credito', 0),
        'Total Balance': compra.get('balance', 0) + venta.get('balance', 0) + insumo.get('balance', 0)
    }
    
    data_comparativo.append(fila)

df_comparativo = pd.DataFrame(data_comparativo)

# Ordenar por total balance (valor absoluto)
df_comparativo['Total Balance Abs'] = df_comparativo['Total Balance'].abs()
df_comparativo = df_comparativo.sort_values('Total Balance Abs', ascending=False)
df_comparativo = df_comparativo.drop('Total Balance Abs', axis=1)

# ============================================================================
# 5. EXPORTAR A EXCEL
# ============================================================================
print("\n💾 Exportando a Excel...")

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f"valorizacion_360_cuentas_{timestamp}.xlsx"

with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    # Hoja 1: Resumen comparativo
    df_resumen = pd.DataFrame([
        {'Métrica': 'Total Compras (Balance)', 'Valor': f"${sum([c['balance'] for c in compras_por_cuenta.values()]):,.0f}"},
        {'Métrica': 'Total Ventas (Balance)', 'Valor': f"${sum([v['balance'] for v in ventas_por_cuenta.values()]):,.0f}"},
        {'Métrica': 'Total Fabricaciones (Balance)', 'Valor': f"${sum([i['balance'] for i in insumos_por_cuenta.values()]):,.0f}"},
        {'Métrica': 'Líneas Compras', 'Valor': f"{len(compras_lineas):,}"},
        {'Métrica': 'Líneas Ventas', 'Valor': f"{len(ventas_lineas):,}"},
        {'Métrica': 'Líneas Fabricaciones', 'Valor': f"{len(insumos_lineas):,}"},
        {'Métrica': 'Cuentas en Compras', 'Valor': len(compras_por_cuenta)},
        {'Métrica': 'Cuentas en Ventas', 'Valor': len(ventas_por_cuenta)},
        {'Métrica': 'Cuentas en Fabricaciones', 'Valor': len(insumos_por_cuenta)},
        {'Métrica': 'Total Cuentas Únicas', 'Valor': len(todas_cuentas)},
    ])
    df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
    
    # Hoja 2: Análisis comparativo completo
    df_comparativo.to_excel(writer, sheet_name='Comparativo Cuentas', index=False)
    
    # Hoja 3: Solo cuentas de compras
    df_compras = pd.DataFrame([
        {
            'Cuenta': stats['nombre'],
            'Débito': stats['debito'],
            'Crédito': stats['credito'],
            'Balance': stats['balance'],
            'Nº Líneas': stats['lineas']
        }
        for cuenta_id, stats in sorted(compras_por_cuenta.items(), key=lambda x: abs(x[1]['balance']), reverse=True)
    ])
    df_compras.to_excel(writer, sheet_name='Cuentas Compras', index=False)
    
    # Hoja 4: Solo cuentas de ventas
    df_ventas = pd.DataFrame([
        {
            'Cuenta': stats['nombre'],
            'Débito': stats['debito'],
            'Crédito': stats['credito'],
            'Balance': stats['balance'],
            'Nº Líneas': stats['lineas']
        }
        for cuenta_id, stats in sorted(ventas_por_cuenta.items(), key=lambda x: abs(x[1]['balance']), reverse=True)
    ])
    df_ventas.to_excel(writer, sheet_name='Cuentas Ventas', index=False)
    
    # Hoja 5: Solo cuentas de fabricaciones
    df_fabricaciones = pd.DataFrame([
        {
            'Cuenta': stats['nombre'],
            'Débito': stats['debito'],
            'Crédito': stats['credito'],
            'Balance': stats['balance'],
            'Nº Líneas': stats['lineas']
        }
        for cuenta_id, stats in sorted(insumos_por_cuenta.items(), key=lambda x: abs(x[1]['balance']), reverse=True)
    ])
    df_fabricaciones.to_excel(writer, sheet_name='Cuentas Fabricaciones', index=False)

print(f"✅ Archivo exportado: {filename}")

# ============================================================================
# 6. MOSTRAR RESUMEN EN CONSOLA
# ============================================================================
print("\n" + "="*160)
print("RESUMEN EJECUTIVO - VALORIZACIÓN 360")
print("="*160)
print("Fabricaciones: Solo valorización de insumos/servicios en órdenes con fruta")
print("="*160)
print()

print("💰 TOTALES POR PROCESO:")
print(f"  Compras:       ${sum([c['balance'] for c in compras_por_cuenta.values()]):>20,.0f} ({len(compras_lineas):,} líneas)")
print(f"  Ventas:        ${sum([v['balance'] for v in ventas_por_cuenta.values()]):>20,.0f} ({len(ventas_lineas):,} líneas)")
print(f"  Fabricaciones: ${sum([i['balance'] for i in insumos_por_cuenta.values()]):>20,.0f} ({len(insumos_lineas):,} líneas)")

print(f"\n📊 CUENTAS CONTABLES:")
print(f"  Cuentas en Compras:       {len(compras_por_cuenta):3d}")
print(f"  Cuentas en Ventas:        {len(ventas_por_cuenta):3d}")
print(f"  Cuentas en Fabricaciones: {len(insumos_por_cuenta):3d}")
print(f"  Total Cuentas Únicas:     {len(todas_cuentas):3d}")

print("\n" + "="*160)
print("TOP 10 CUENTAS POR MOVIMIENTO TOTAL (VALOR ABSOLUTO)")
print("="*160)
print(f"{'Cuenta':<70s} | {'Compras':>12s} | {'Ventas':>12s} | {'Fabricac.':>12s} | {'Total':>15s}")
print("-" * 160)

for _, row in df_comparativo.head(10).iterrows():
    print(f"{row['Cuenta'][:70]:70s} | {row['En Compras']:>12s} | {row['En Ventas']:>12s} | {row['En Fabricaciones']:>12s} | ${abs(row['Total Balance']):>14,.0f}")

print("\n" + "="*160)
print("CUENTAS EXCLUSIVAS POR PROCESO")
print("="*160)

# Cuentas solo en compras
solo_compras = [c for c in todas_cuentas if c in compras_por_cuenta and c not in ventas_por_cuenta and c not in insumos_por_cuenta]
print(f"\n📥 Solo en Compras ({len(solo_compras)} cuentas):")
for cuenta_id in solo_compras[:5]:
    print(f"  - {compras_por_cuenta[cuenta_id]['nombre'][:80]}")

# Cuentas solo en ventas
solo_ventas = [c for c in todas_cuentas if c not in compras_por_cuenta and c in ventas_por_cuenta and c not in insumos_por_cuenta]
print(f"\n📤 Solo en Ventas ({len(solo_ventas)} cuentas):")
for cuenta_id in solo_ventas[:5]:
    print(f"  - {ventas_por_cuenta[cuenta_id]['nombre'][:80]}")

# Cuentas solo en fabricaciones
solo_fabricaciones = [c for c in todas_cuentas if c not in compras_por_cuenta and c not in ventas_por_cuenta and c in insumos_por_cuenta]
print(f"\n🏭 Solo en Fabricaciones ({len(solo_fabricaciones)} cuentas):")
for cuenta_id in solo_fabricaciones[:5]:
    print(f"  - {insumos_por_cuenta[cuenta_id]['nombre'][:80]}")

# Cuentas compartidas
compartidas_3 = [c for c in todas_cuentas if c in compras_por_cuenta and c in ventas_por_cuenta and c in insumos_por_cuenta]
print(f"\n🔄 En los 3 procesos ({len(compartidas_3)} cuentas):")
for cuenta_id in compartidas_3[:5]:
    nombre = compras_por_cuenta[cuenta_id]['nombre'] or ventas_por_cuenta[cuenta_id]['nombre'] or insumos_por_cuenta[cuenta_id]['nombre']
    print(f"  - {nombre[:80]}")

print("\n" + "="*160)
print("✅ PROCESO COMPLETADO")
print("="*160)
print(f"\n📁 Archivo: {filename}")
print(f"📊 Análisis completo de {len(todas_cuentas)} cuentas contables")
print(f"📈 Listo para valorización 360 y comparativa de flujos")
