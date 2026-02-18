"""
Script de validación para 1.2.1 - Pagos a proveedores (vista semanal).
Verifica que los datos del dashboard sean correctos comparando con Odoo directo.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from collections import defaultdict
from datetime import datetime, timedelta
from shared.odoo_client import OdooClient

odoo = OdooClient()

# Rango de fechas: Ene-Feb 2026 (lo que muestra el dashboard)
FECHA_INICIO = '2026-01-01'
FECHA_FIN = '2026-02-28'

# Semanas del dashboard (S1-S9 visibles en screenshot)
# S1 = W01 (dic 29 - ene 4), S2 = W02, ... 
def fecha_a_semana(fecha_str):
    """Convierte fecha a semana ISO (2026-Wxx)"""
    if not fecha_str:
        return None
    try:
        dt = datetime.strptime(fecha_str, '%Y-%m-%d')
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    except:
        return None

print("=" * 100)
print("VALIDACIÓN 1.2.1 - PAGOS A PROVEEDORES (SEMANAL)")
print("=" * 100)

# PASO 1: Buscar facturas
facturas = odoo.search_read(
    'account.move',
    [
        ['move_type', 'in', ['in_invoice', 'in_refund']],
        ['journal_id', '=', 2],
        ['date', '>=', FECHA_INICIO],
        ['date', '<=', FECHA_FIN],
        ['state', '=', 'posted']
    ],
    ['id', 'name', 'move_type', 'date', 'invoice_date', 'invoice_date_due',
     'amount_total', 'amount_residual', 'payment_state', 'partner_id', 
     'x_studio_fecha_estimada_de_pago'],
    limit=5000
)

print(f"\nTotal facturas encontradas: {len(facturas)}")
facturas_normales = [f for f in facturas if f.get('move_type') == 'in_invoice']
notas_credito = [f for f in facturas if f.get('move_type') == 'in_refund']
print(f"  Facturas normales: {len(facturas_normales)}")
print(f"  Notas de crédito: {len(notas_credito)}")

# PASO 2: Buscar líneas de todas las facturas
factura_ids = [f['id'] for f in facturas]
todas_lineas = odoo.search_read(
    'account.move.line',
    [['move_id', 'in', factura_ids]],
    ['id', 'move_id', 'matching_number', 'date', 'debit', 'credit'],
    limit=50000
)
lineas_por_factura = defaultdict(list)
for linea in todas_lineas:
    move_id = linea.get('move_id')
    if isinstance(move_id, (list, tuple)):
        move_id = move_id[0]
    lineas_por_factura[move_id].append(linea)

# PASO 3: Partners con categoría
partner_ids = list(set([f.get('partner_id')[0] if isinstance(f.get('partner_id'), (list, tuple)) else f.get('partner_id') 
                       for f in facturas if f.get('partner_id')]))
partners_data = odoo.search_read(
    'res.partner',
    [['id', 'in', partner_ids]],
    ['id', 'name', 'x_studio_categora_de_contacto'],
    limit=10000
)
partners_info = {}
for p in partners_data:
    cat = p.get('x_studio_categora_de_contacto', False)
    if cat and isinstance(cat, (list, tuple)):
        cat = cat[1]
    elif not cat or cat == 'False':
        cat = 'Sin Categoría'
    partners_info[p['id']] = {'name': p.get('name', 'Sin nombre'), 'categoria': cat}

# PASO 4: Clasificar cada factura
estados_resumen = {
    'PAGADAS': {'count': 0, 'facturas': 0, 'nc': 0, 'monto_total': 0, 'por_semana': defaultdict(float), 'por_categoria': defaultdict(lambda: defaultdict(float)), 'categorias_total': defaultdict(float)},
    'PARCIALES': {'count': 0, 'facturas': 0, 'nc': 0, 'monto_total': 0, 'por_semana': defaultdict(float), 'por_categoria': defaultdict(lambda: defaultdict(float)), 'categorias_total': defaultdict(float)},
    'NO_PAGADAS': {'count': 0, 'facturas': 0, 'nc': 0, 'monto_total': 0, 'por_semana': defaultdict(float), 'por_categoria': defaultdict(lambda: defaultdict(float)), 'categorias_total': defaultdict(float)},
}

total_general = 0
total_por_semana = defaultdict(float)

for f in facturas:
    lineas = lineas_por_factura.get(f['id'], [])
    
    # Matching number
    matching_number = None
    for linea in lineas:
        match = linea.get('matching_number')
        if match and match not in ['False', False, '', None]:
            matching_number = match
            break
    
    amount_total = f.get('amount_total', 0) or 0
    amount_residual = f.get('amount_residual', 0) or 0
    move_type = f.get('move_type', '')
    signo = -1 if move_type == 'in_refund' else 1
    es_nc = (move_type == 'in_refund')
    
    partner_data = f.get('partner_id', [0, 'Sin proveedor'])
    partner_id = partner_data[0] if isinstance(partner_data, (list, tuple)) else partner_data
    partner_name = partner_data[1] if isinstance(partner_data, (list, tuple)) and len(partner_data) > 1 else 'Sin proveedor'
    categoria = partners_info.get(partner_id, {}).get('categoria', 'Sin Categoría')
    
    if matching_number and str(matching_number).startswith('A'):
        estado_key = 'PAGADAS'
        monto = -(amount_total - amount_residual) * signo
        
        # Fecha de pago real
        fecha_real = f.get('date', '')
        for linea in lineas:
            if linea.get('debit', 0) > 0:
                fecha_real = linea.get('date', fecha_real)
                break
        semana = fecha_a_semana(fecha_real)
        
    elif matching_number == 'P':
        estado_key = 'PARCIALES'
        monto_real = -(amount_total - amount_residual) * signo
        monto_proyectado = -amount_residual * signo
        monto = monto_real + monto_proyectado
        
        fecha_real = f.get('date', '')
        semana_real = fecha_a_semana(fecha_real)
        
        # Fecha proyectada
        fecha_estimada = f.get('x_studio_fecha_estimada_de_pago')
        invoice_date_due = f.get('invoice_date_due')
        invoice_date = f.get('invoice_date', '')
        
        if fecha_estimada:
            semana_proy = fecha_a_semana(fecha_estimada)
        elif invoice_date_due:
            semana_proy = fecha_a_semana(invoice_date_due)
        elif invoice_date:
            try:
                fecha_dt = datetime.strptime(invoice_date, '%Y-%m-%d')
                semana_proy = fecha_a_semana((fecha_dt + timedelta(days=30)).strftime('%Y-%m-%d'))
            except:
                semana_proy = semana_real
        else:
            semana_proy = semana_real
        
        # Acumular real y proyectado en sus semanas
        if semana_real:
            estados_resumen[estado_key]['por_semana'][semana_real] += monto_real
            estados_resumen[estado_key]['por_categoria'][categoria][semana_real] += monto_real
            total_por_semana[semana_real] += monto_real
        if semana_proy:
            estados_resumen[estado_key]['por_semana'][semana_proy] += monto_proyectado
            estados_resumen[estado_key]['por_categoria'][categoria][semana_proy] += monto_proyectado
            total_por_semana[semana_proy] += monto_proyectado
        
        estados_resumen[estado_key]['count'] += 1
        if es_nc:
            estados_resumen[estado_key]['nc'] += 1
        else:
            estados_resumen[estado_key]['facturas'] += 1
        estados_resumen[estado_key]['monto_total'] += monto
        estados_resumen[estado_key]['categorias_total'][categoria] += monto
        total_general += monto
        continue  # Ya acumulamos manualmente
        
    else:
        estado_key = 'NO_PAGADAS'
        monto = -amount_total * signo
        
        fecha_estimada = f.get('x_studio_fecha_estimada_de_pago')
        invoice_date_due = f.get('invoice_date_due')
        invoice_date = f.get('invoice_date', '')
        
        if fecha_estimada:
            semana = fecha_a_semana(fecha_estimada)
        elif invoice_date_due:
            semana = fecha_a_semana(invoice_date_due)
        elif invoice_date:
            try:
                fecha_dt = datetime.strptime(invoice_date, '%Y-%m-%d')
                semana = fecha_a_semana((fecha_dt + timedelta(days=30)).strftime('%Y-%m-%d'))
            except:
                semana = fecha_a_semana(invoice_date)
        else:
            semana = fecha_a_semana(f.get('date', ''))
    
    # Acumular
    estados_resumen[estado_key]['count'] += 1
    if es_nc:
        estados_resumen[estado_key]['nc'] += 1
    else:
        estados_resumen[estado_key]['facturas'] += 1
    estados_resumen[estado_key]['monto_total'] += monto
    estados_resumen[estado_key]['categorias_total'][categoria] += monto
    total_general += monto
    
    if semana:
        estados_resumen[estado_key]['por_semana'][semana] += monto
        estados_resumen[estado_key]['por_categoria'][categoria][semana] += monto
        total_por_semana[semana] += monto

# MOSTRAR RESULTADOS
semanas_orden = sorted(set(
    list(total_por_semana.keys()) + 
    [s for e in estados_resumen.values() for s in e['por_semana'].keys()]
))

# Filtrar solo semanas relevantes (Ene-Feb 2026)
semanas_orden = [s for s in semanas_orden if s.startswith('2026') or s.startswith('2025-W53')]

print(f"\n{'='*100}")
print(f"TOTAL GENERAL 1.2.1: ${total_general:,.0f}")
print(f"{'='*100}")

# Header de semanas
header = f"{'':>50}"
for s in semanas_orden:
    header += f" {s:>16}"
header += f" {'TOTAL':>16}"
print(header)

# Total por semana
row = f"{'TOTAL 1.2.1':>50}"
for s in semanas_orden:
    row += f" ${total_por_semana.get(s, 0):>14,.0f}"
row += f" ${total_general:>14,.0f}"
print(row)
print()

# Por estado
nombres_estado = {'PAGADAS': '✅ Facturas Pagadas', 'PARCIALES': '⏳ Facturas Parcialmente Pagadas', 'NO_PAGADAS': '❌ Facturas No Pagadas'}

for estado_key in ['PAGADAS', 'PARCIALES', 'NO_PAGADAS']:
    e = estados_resumen[estado_key]
    nombre = nombres_estado[estado_key]
    
    print(f"\n{'─'*100}")
    print(f"  {nombre} ({e['count']} docs: {e['facturas']} fact + {e['nc']} NC)")
    
    row = f"{'SUBTOTAL':>50}"
    for s in semanas_orden:
        row += f" ${e['por_semana'].get(s, 0):>14,.0f}"
    row += f" ${e['monto_total']:>14,.0f}"
    print(row)
    
    # Por categoría
    cats_sorted = sorted(e['categorias_total'].items(), key=lambda x: abs(x[1]), reverse=True)
    for cat_name, cat_total in cats_sorted:
        row = f"{'    📁 ' + cat_name:>50}"
        for s in semanas_orden:
            val = e['por_categoria'].get(cat_name, {}).get(s, 0)
            if val != 0:
                row += f" ${val:>14,.0f}"
            else:
                row += f" {'$0':>15}"
        row += f" ${cat_total:>14,.0f}"
        print(row)

# VALIDACIÓN: suma categorías vs subtotal
print(f"\n{'='*100}")
print("VALIDACIONES:")
print(f"{'='*100}")

for estado_key in ['PAGADAS', 'PARCIALES', 'NO_PAGADAS']:
    e = estados_resumen[estado_key]
    nombre = nombres_estado[estado_key]
    suma_cats = sum(e['categorias_total'].values())
    diff = e['monto_total'] - suma_cats
    ok = "✅" if abs(diff) < 1 else "❌"
    print(f"  {ok} {nombre}: subtotal=${e['monto_total']:,.0f} vs suma_cats=${suma_cats:,.0f} (diff=${diff:,.0f})")

# Suma estados vs total
suma_estados = sum(e['monto_total'] for e in estados_resumen.values())
diff_total = total_general - suma_estados
ok = "✅" if abs(diff_total) < 1 else "❌"
print(f"  {ok} Total 1.2.1: ${total_general:,.0f} vs suma_estados: ${suma_estados:,.0f} (diff=${diff_total:,.0f})")

# Validar por semana: suma de estados == total semana
print(f"\n  Validación por semana:")
for s in semanas_orden:
    suma = sum(e['por_semana'].get(s, 0) for e in estados_resumen.values())
    total = total_por_semana.get(s, 0)
    diff = total - suma
    ok = "✅" if abs(diff) < 1 else "❌"
    if diff != 0:
        print(f"    {ok} {s}: total=${total:,.0f} vs suma_estados=${suma:,.0f} (diff=${diff:,.0f})")

# Screenshot comparison
print(f"\n{'='*100}")
print("COMPARACIÓN CON SCREENSHOT (S5-S9):")
print(f"{'='*100}")
screenshot_vals = {
    '1.2.1 Total': {'2026-W05': -560700154, '2026-W06': -457444879, '2026-W07': -487783821, '2026-W08': -99550228, '2026-W09': -80983351},
    'Pagadas':     {'2026-W05': -404843875, '2026-W06': -419112760, '2026-W07': -118363617, '2026-W08': 19646900,  '2026-W09': 0},
    'Parciales':   {'2026-W05': -153271181, '2026-W06': -37547583,  '2026-W07': -338048741, '2026-W08': -83228379, '2026-W09': -54399549},
    'No Pagadas':  {'2026-W05': -2585098,   '2026-W06': -784536,    '2026-W07': -31371463,  '2026-W08': -35968749, '2026-W09': -26583802},
}

estado_map = {'Pagadas': 'PAGADAS', 'Parciales': 'PARCIALES', 'No Pagadas': 'NO_PAGADAS'}

for label, expected in screenshot_vals.items():
    print(f"\n  {label}:")
    for semana, expected_val in expected.items():
        if label == '1.2.1 Total':
            actual = total_por_semana.get(semana, 0)
        else:
            actual = estados_resumen[estado_map[label]]['por_semana'].get(semana, 0)
        diff = actual - expected_val
        ok = "✅" if abs(diff) < 100 else "❌"  # Tolerancia de $100 por redondeo
        if abs(diff) > 100:
            print(f"    {ok} {semana}: esperado=${expected_val:,.0f} actual=${actual:,.0f} diff=${diff:,.0f}")
        else:
            print(f"    {ok} {semana}: ${actual:,.0f}")

print(f"\n{'='*100}")
print("FIN VALIDACIÓN")
print(f"{'='*100}")
