#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DRY RUN: Corrección en cadena de OC12288 - Precio $0.00 → $2.4 USD
Este script NO ejecuta cambios, solo muestra qué se modificaría
"""
import xmlrpc.client
from datetime import datetime
import json

# Conexión a Odoo
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# PRECIO CORRECTO
PRECIO_CORRECTO = 2.4

print("=" * 100)
print("DRY RUN: CORRECCIÓN EN CADENA OC12288")
print(f"PRECIO CORRECTO: ${PRECIO_CORRECTO} USD/kg")
print("=" * 100)
print("\n⚠️  MODO DRY-RUN: No se ejecutarán cambios reales\n")

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

if not uid:
    print("❌ Error de autenticación")
    exit(1)

print(f"✅ Conectado como UID: {uid}\n")

# ============================================================================
# PASO 1: OBTENER DATOS ACTUALES DE LA OC
# ============================================================================
print("\n" + "=" * 100)
print("PASO 1: DATOS ACTUALES DE OC12288")
print("=" * 100)

oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC12288']]],
    {'fields': ['id', 'name', 'state', 'amount_total', 'order_line'], 'limit': 1}
)

if not oc:
    print("❌ OC12288 no encontrada")
    exit(1)

oc = oc[0]
oc_id = oc['id']

print(f"\n📋 OC ID: {oc_id}")
print(f"   Estado: {oc['state']}")
print(f"   Total Actual: ${oc['amount_total']:,.2f}")

# ============================================================================
# PASO 2: LÍNEAS DE LA OC - SIMULACIÓN DE CORRECCIÓN
# ============================================================================
print("\n" + "=" * 100)
print("PASO 2: CORRECCIÓN DE LÍNEAS DE ORDEN DE COMPRA")
print("=" * 100)

lineas_oc = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
    [[['order_id', '=', oc_id]]],
    {'fields': [
        'id', 'product_id', 'name', 'product_qty', 'price_unit', 
        'price_subtotal', 'price_total', 'taxes_id'
    ]}
)

cambios_lineas = []
nuevo_total_oc = 0

print(f"\n📦 ENCONTRADAS {len(lineas_oc)} LÍNEAS A CORREGIR:\n")

for i, linea in enumerate(lineas_oc, 1):
    precio_actual = linea['price_unit']
    cantidad = linea['product_qty']
    
    # Calcular nuevos valores
    nuevo_subtotal = cantidad * PRECIO_CORRECTO
    
    # Calcular impuestos (asumiendo IVA 19% si tiene taxes)
    tax_rate = 0.0
    if linea.get('taxes_id'):
        # Obtener la tasa de impuesto
        taxes = models.execute_kw(db, uid, password, 'account.tax', 'search_read',
            [[['id', 'in', linea['taxes_id']]]],
            {'fields': ['amount']}
        )
        if taxes:
            tax_rate = taxes[0]['amount'] / 100.0
    
    nuevo_impuesto = nuevo_subtotal * tax_rate
    nuevo_total = nuevo_subtotal + nuevo_impuesto
    nuevo_total_oc += nuevo_total
    
    print(f"Línea #{i}: {linea['product_id'][1] if linea['product_id'] else 'N/A'}")
    print(f"  ID: {linea['id']}")
    print(f"  Cantidad: {cantidad} kg")
    print(f"  Precio Actual: ${precio_actual:,.2f} ❌")
    print(f"  Precio Nuevo: ${PRECIO_CORRECTO:,.2f} ✓")
    print(f"  Subtotal Actual: ${linea['price_subtotal']:,.2f}")
    print(f"  Subtotal Nuevo: ${nuevo_subtotal:,.2f}")
    print(f"  Total Actual: ${linea['price_total']:,.2f}")
    print(f"  Total Nuevo: ${nuevo_total:,.2f}")
    print(f"  Diferencia: ${nuevo_total - linea['price_total']:,.2f}")
    print()
    
    cambios_lineas.append({
        'id': linea['id'],
        'modelo': 'purchase.order.line',
        'campo': 'price_unit',
        'valor_actual': precio_actual,
        'valor_nuevo': PRECIO_CORRECTO,
        'producto': linea['product_id'][1] if linea['product_id'] else 'N/A'
    })

print(f"💰 TOTAL OC ACTUAL: ${oc['amount_total']:,.2f}")
print(f"💰 TOTAL OC NUEVO: ${nuevo_total_oc:,.2f}")
print(f"💰 DIFERENCIA: ${nuevo_total_oc - oc['amount_total']:,.2f}\n")

# ============================================================================
# PASO 3: MOVIMIENTOS DE STOCK - SIMULACIÓN DE CORRECCIÓN
# ============================================================================
print("\n" + "=" * 100)
print("PASO 3: CORRECCIÓN DE MOVIMIENTOS DE STOCK")
print("=" * 100)

# Buscar picking de la OC
pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
    [[['origin', '=', 'OC12288']]],
    {'fields': ['id', 'name', 'state', 'move_ids']}
)

cambios_moves = []

if pickings:
    print(f"\n📥 ENCONTRADOS {len(pickings)} ALBARANES:\n")
    
    for picking in pickings:
        print(f"Albarán: {picking['name']} (Estado: {picking['state']})")
        
        if picking.get('move_ids'):
            moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
                [[['id', 'in', picking['move_ids']]]],
                {'fields': [
                    'id', 'product_id', 'product_uom_qty', 'quantity_done',
                    'price_unit', 'state', 'purchase_line_id'
                ]}
            )
            
            print(f"  Movimientos: {len(moves)}\n")
            
            for move in moves:
                # Solo corregir movimientos relacionados con líneas de OC que tienen precio incorrecto
                needs_correction = False
                if move.get('purchase_line_id'):
                    pol_id = move['purchase_line_id'][0] if isinstance(move['purchase_line_id'], list) else move['purchase_line_id']
                    needs_correction = any(c['id'] == pol_id for c in cambios_lineas)
                else:
                    # Si no tiene purchase_line_id pero el precio es 0, también corregir
                    needs_correction = move.get('price_unit', 0) == 0.0
                
                if needs_correction:
                    precio_actual_move = move.get('price_unit', 0)
                    cantidad_realizada = move.get('quantity_done', 0)
                    
                    print(f"    ✓ Movimiento ID: {move['id']}")
                    print(f"      Producto: {move['product_id'][1] if move['product_id'] else 'N/A'}")
                    print(f"      Cantidad: {cantidad_realizada} kg")
                    print(f"      Precio Actual: ${precio_actual_move:,.2f} ❌")
                    print(f"      Precio Nuevo: ${PRECIO_CORRECTO:,.2f} ✓")
                    print(f"      Estado: {move['state']}")
                    print()
                    
                    cambios_moves.append({
                        'id': move['id'],
                        'modelo': 'stock.move',
                        'campo': 'price_unit',
                        'valor_actual': precio_actual_move,
                        'valor_nuevo': PRECIO_CORRECTO,
                        'producto': move['product_id'][1] if move['product_id'] else 'N/A',
                        'cantidad': cantidad_realizada
                    })
else:
    print("\n⚠️ No hay albaranes asociados")

# ============================================================================
# PASO 4: CAPAS DE VALORACIÓN - SIMULACIÓN DE CORRECCIÓN
# ============================================================================
print("\n" + "=" * 100)
print("PASO 4: CORRECCIÓN DE CAPAS DE VALORACIÓN DE INVENTARIO")
print("=" * 100)

# Buscar capas de valoración relacionadas con la OC por fecha y producto
product_ids = [l['product_id'][0] for l in lineas_oc if l.get('product_id')]

valuation_layers = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
    [[
        ['product_id', 'in', product_ids],
        ['create_date', '>=', '2026-01-28 00:00:00'],
        ['create_date', '<=', '2026-01-29 23:59:59'],
        ['unit_cost', '=', 0.0]  # Solo las que tienen costo 0
    ]],
    {'fields': [
        'id', 'product_id', 'quantity', 'unit_cost', 'value',
        'remaining_qty', 'remaining_value', 'description', 'create_date'
    ]}
)

cambios_valuation = []

if valuation_layers:
    print(f"\n📉 ENCONTRADAS {len(valuation_layers)} CAPAS DE VALORACIÓN CON COSTO $0:\n")
    
    for vl in valuation_layers:
        cantidad = vl['quantity']
        costo_actual = vl['unit_cost']
        valor_actual = vl['value']
        
        nuevo_valor = cantidad * PRECIO_CORRECTO
        
        print(f"Capa ID: {vl['id']}")
        print(f"  Producto: {vl['product_id'][1] if vl['product_id'] else 'N/A'}")
        print(f"  Fecha: {vl['create_date']}")
        print(f"  Descripción: {vl.get('description', 'N/A')}")
        print(f"  Cantidad: {cantidad} kg")
        print(f"  Costo Unit. Actual: ${costo_actual:,.2f} ❌")
        print(f"  Costo Unit. Nuevo: ${PRECIO_CORRECTO:,.2f} ✓")
        print(f"  Valor Actual: ${valor_actual:,.2f}")
        print(f"  Valor Nuevo: ${nuevo_valor:,.2f}")
        print(f"  Diferencia: ${nuevo_valor - valor_actual:,.2f}")
        print(f"  Remaining Qty: {vl.get('remaining_qty', 0)}")
        print()
        
        cambios_valuation.append({
            'id': vl['id'],
            'modelo': 'stock.valuation.layer',
            'campos': {
                'unit_cost': {'actual': costo_actual, 'nuevo': PRECIO_CORRECTO},
                'value': {'actual': valor_actual, 'nuevo': nuevo_valor}
            },
            'producto': vl['product_id'][1] if vl['product_id'] else 'N/A',
            'cantidad': cantidad
        })
else:
    print("\n⚠️ No hay capas de valoración con costo $0 en este rango de fecha")

# ============================================================================
# PASO 5: VERIFICACIÓN DE FACTURAS
# ============================================================================
print("\n" + "=" * 100)
print("PASO 5: VERIFICACIÓN DE FACTURAS (NO DEBEN EXISTIR PARA PODER CORREGIR)")
print("=" * 100)

facturas = models.execute_kw(db, uid, password, 'account.move', 'search_read',
    [[
        '|',
        ['ref', 'ilike', 'OC12288'],
        ['invoice_origin', 'ilike', 'OC12288']
    ]],
    {'fields': ['id', 'name', 'state', 'amount_total']}
)

if facturas:
    print(f"\n⚠️  ADVERTENCIA: EXISTEN {len(facturas)} FACTURAS RELACIONADAS")
    print("   Será necesario modificar también las facturas:\n")
    for f in facturas:
        print(f"   - {f['name']} (Estado: {f['state']}, Total: ${f['amount_total']:,.2f})")
    print("\n   ⚠️  La corrección será más compleja con facturas ya creadas")
else:
    print("\n✅ PERFECTO: No hay facturas creadas todavía")
    print("   La corrección puede hacerse de manera limpia")

# ============================================================================
# RESUMEN DE CAMBIOS
# ============================================================================
print("\n" + "=" * 100)
print("RESUMEN DE CAMBIOS PROPUESTOS (DRY-RUN)")
print("=" * 100)

print(f"""
📊 ESTADÍSTICAS:
   • Líneas de OC a modificar: {len(cambios_lineas)}
   • Movimientos de stock a modificar: {len(cambios_moves)}
   • Capas de valoración a modificar: {len(cambios_valuation)}
   • Facturas a revisar: {len(facturas)}

💰 IMPACTO FINANCIERO:
   • Total OC actual: ${oc['amount_total']:,.2f}
   • Total OC nuevo: ${nuevo_total_oc:,.2f}
   • Diferencia OC: ${nuevo_total_oc - oc['amount_total']:,.2f}
   
   • Valor inventario actual (capas): ${sum(v['campos']['value']['actual'] for v in cambios_valuation):,.2f}
   • Valor inventario nuevo: ${sum(v['campos']['value']['nuevo'] for v in cambios_valuation):,.2f}
   • Diferencia inventario: ${sum(v['campos']['value']['nuevo'] - v['campos']['value']['actual'] for v in cambios_valuation):,.2f}
""")

# ============================================================================
# PLAN DE EJECUCIÓN
# ============================================================================
print("\n" + "=" * 100)
print("PLAN DE EJECUCIÓN PARA CORRECCIÓN REAL")
print("=" * 100)

print("""
📋 ORDEN DE EJECUCIÓN RECOMENDADO:

1. ✓ LÍNEAS DE ORDEN DE COMPRA (purchase.order.line)
   - Actualizar campo 'price_unit' de $0.00 → $2.40
   - Odoo recalculará automáticamente subtotal y total

2. ✓ MOVIMIENTOS DE STOCK (stock.move)
   - Actualizar campo 'price_unit' de $0.00 → $2.40
   - Esto afecta la valoración de recepciones

3. ✓ CAPAS DE VALORACIÓN (stock.valuation.layer)
   - Actualizar 'unit_cost' de $0.00 → $2.40
   - Actualizar 'value' recalculado (cantidad × precio)
   - Si 'remaining_value' > 0, también recalcular

4. ⚠️  ASIENTOS CONTABLES (si existen)
   - Verificar si se generaron asientos automáticos
   - Pueden requerir ajustes manuales o reversa/recreación

5. ⚠️  FACTURAS (si existen)
   - Si hay facturas, se deben ajustar o crear notas de crédito/débito
   - En este caso: NO HAY FACTURAS ✓

⚠️  CONSIDERACIONES IMPORTANTES:
   • Hacer backup antes de ejecutar
   • Revisar permisos de escritura en modelos
   • Verificar si hay procesos automáticos que puedan interferir
   • Validar que el estado de la OC permita modificaciones
   • Estado actual de OC: {oc['state']} (debe ser editable)
""")

# ============================================================================
# DETALLE DE CAMBIOS JSON
# ============================================================================
print("\n" + "=" * 100)
print("DETALLE DE CAMBIOS EN FORMATO JSON")
print("=" * 100)

cambios_completos = {
    'oc_id': oc_id,
    'oc_nombre': 'OC12288',
    'precio_correcto': PRECIO_CORRECTO,
    'fecha_analisis': datetime.now().isoformat(),
    'cambios': {
        'purchase_order_lines': cambios_lineas,
        'stock_moves': cambios_moves,
        'stock_valuation_layers': cambios_valuation
    },
    'totales': {
        'oc_actual': oc['amount_total'],
        'oc_nuevo': nuevo_total_oc,
        'diferencia': nuevo_total_oc - oc['amount_total']
    },
    'facturas_existentes': len(facturas),
    'puede_ejecutarse_limpiamente': len(facturas) == 0
}

print("\n" + json.dumps(cambios_completos, indent=2, ensure_ascii=False))

# Guardar JSON
try:
    filename = f'oc12288_dryrun_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(cambios_completos, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Cambios guardados en: {filename}")
except Exception as e:
    print(f"\n⚠️ No se pudo guardar el JSON: {e}")

# ============================================================================
# SIGUIENTE PASO
# ============================================================================
print("\n" + "=" * 100)
print("¿DESEA PROCEDER CON LA CORRECCIÓN?")
print("=" * 100)

if len(facturas) == 0:
    print("""
✅ ESTADO: CORRECCIÓN FACTIBLE

El sistema está en estado óptimo para corrección:
• No hay facturas creadas
• Solo hay que actualizar OC, movimientos y valoración
• El impacto es claramente medible

SIGUIENTE PASO:
Crear script 'corregir_oc12288_EJECUTAR.py' que:
1. Implemente las actualizaciones en el orden correcto
2. Valide cada paso
3. Genere log de cambios realizados
4. Permita rollback en caso de error
""")
else:
    print("""
⚠️  ESTADO: CORRECCIÓN COMPLEJA

Existen facturas relacionadas. Se requiere:
1. Analizar el impacto en facturas
2. Decidir estrategia (notas de crédito vs corrección directa)
3. Validar asientos contables generados
4. Plan de corrección más elaborado
""")

print("\n" + "=" * 100)
print("FIN DEL DRY-RUN")
print("=" * 100)
