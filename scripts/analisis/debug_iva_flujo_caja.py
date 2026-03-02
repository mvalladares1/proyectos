"""
DEBUG: Análisis de IVA en Flujo de Caja
=========================================
Investiga dónde aparece (o no) el IVA en las facturas del flujo de caja.

1. Analiza la factura #297907 (AGRICOLA COX - CLP$ 1,785,000,000)
2. Muestra todas las move lines con sus cuentas, balances, IFRS3
3. Calcula los ponderadores como lo hace el código
4. Verifica si el IVA queda incluido o excluido
5. Analiza el mapeo general: ¿qué cuentas de IVA no se mapean?
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from shared.odoo_client import OdooClient

odoo = OdooClient()

print("=" * 100)
print("🔍 DEBUG: ANÁLISIS DE IVA EN FLUJO DE CAJA")
print("=" * 100)

# ═══════════════════════════════════════════════════════════════
# PARTE 1: Buscar la factura 297907 de AGRICOLA COX
# ═══════════════════════════════════════════════════════════════
print("\n" + "═" * 80)
print("PARTE 1: FACTURA #297907 - AGRICOLA COX LTDA")
print("═" * 80)

# Buscar por nombre que contenga 297907
factura = odoo.search_read(
    'account.move',
    [['id', '=', 297907]],
    ['id', 'name', 'partner_id', 'amount_total', 'amount_untaxed', 'amount_tax',
     'amount_residual', 'date', 'invoice_date', 'invoice_date_due',
     'state', 'payment_state', 'move_type', 'journal_id', 'currency_id'],
    limit=1
)

if not factura:
    # Intentar buscar por nombre
    factura = odoo.search_read(
        'account.move',
        [['name', 'ilike', '297907']],
        ['id', 'name', 'partner_id', 'amount_total', 'amount_untaxed', 'amount_tax',
         'amount_residual', 'date', 'invoice_date', 'invoice_date_due',
         'state', 'payment_state', 'move_type', 'journal_id', 'currency_id'],
        limit=5
    )

if not factura:
    print("❌ No se encontró la factura 297907. Buscando facturas en diario Proyecciones Futuras...")
    factura = odoo.search_read(
        'account.move',
        [
            ['journal_id', '=', 130],
            ['move_type', 'in', ['in_invoice', 'in_refund']],
            ['partner_id.name', 'ilike', 'COX']
        ],
        ['id', 'name', 'partner_id', 'amount_total', 'amount_untaxed', 'amount_tax',
         'amount_residual', 'date', 'invoice_date', 'invoice_date_due',
         'state', 'payment_state', 'move_type', 'journal_id', 'currency_id'],
        limit=5
    )

if factura:
    f = factura[0]
    print(f"\n  📄 Factura: {f.get('name')} (ID: {f.get('id')})")
    print(f"  👤 Partner: {f.get('partner_id')}")
    print(f"  📋 Diario: {f.get('journal_id')}")
    print(f"  📝 Tipo: {f.get('move_type')}")
    print(f"  📊 Estado: {f.get('state')} | Pago: {f.get('payment_state')}")
    print(f"  💰 Moneda: {f.get('currency_id')}")
    print(f"  📅 Fecha: {f.get('date')} | Factura: {f.get('invoice_date')} | Vencimiento: {f.get('invoice_date_due')}")
    print(f"\n  💵 MONTOS:")
    print(f"     amount_untaxed (Base Imponible): ${f.get('amount_untaxed', 0):>20,.0f}")
    print(f"     amount_tax     (IVA):            ${f.get('amount_tax', 0):>20,.0f}")
    print(f"     amount_total   (Total):          ${f.get('amount_total', 0):>20,.0f}")
    print(f"     amount_residual (Residual):      ${f.get('amount_residual', 0):>20,.0f}")
    
    move_id = f['id']
else:
    print("❌ No se encontró la factura. Continuando con análisis general...")
    move_id = None

# ═══════════════════════════════════════════════════════════════
# PARTE 2: Analizar TODAS las líneas de la factura
# ═══════════════════════════════════════════════════════════════
if move_id:
    print("\n" + "═" * 80)
    print(f"PARTE 2: LÍNEAS DE LA FACTURA {move_id}")
    print("═" * 80)
    
    lineas = odoo.search_read(
        'account.move.line',
        [['move_id', '=', move_id]],
        ['id', 'name', 'account_id', 'balance', 'debit', 'credit',
         'display_type', 'analytic_distribution', 'tax_ids', 'tax_line_id'],
        limit=100
    )
    
    print(f"\n  Total líneas: {len(lineas)}")
    
    # Obtener IDs de cuentas
    account_ids = set()
    for l in lineas:
        acc = l.get('account_id')
        if acc and isinstance(acc, (list, tuple)):
            account_ids.add(acc[0])
    
    # Obtener IFRS3 de cada cuenta
    ifrs3_map = {}
    if account_ids:
        cuentas = odoo.read('account.account', list(account_ids), ['id', 'code', 'name', 'x_studio_cat_ifrs_3'])
        for c in cuentas:
            ifrs3_map[c['id']] = {
                'code': c.get('code', ''),
                'name': c.get('name', ''),
                'ifrs3': (c.get('x_studio_cat_ifrs_3') or '').strip()
            }
    
    print(f"\n  {'#':>3} {'display_type':>14} {'Cuenta':>12} {'Nombre Cuenta':>40} {'Balance':>20} {'IFRS3':>25} {'Analítico'}")
    print("  " + "-" * 160)
    
    total_balance = 0
    total_con_ifrs3 = 0
    total_sin_ifrs3 = 0
    total_payment_term = 0
    total_iva_lines = 0
    
    for l in lineas:
        acc = l.get('account_id', [0, ''])
        acc_id = acc[0] if isinstance(acc, (list, tuple)) else acc
        acc_info = ifrs3_map.get(acc_id, {'code': '?', 'name': '?', 'ifrs3': ''})
        
        display_type = l.get('display_type') or 'product'
        balance = float(l.get('balance') or 0)
        analytic = l.get('analytic_distribution') or {}
        tax_line = l.get('tax_line_id')
        ifrs3 = acc_info['ifrs3']
        
        # Clasificar
        es_payment_term = display_type == 'payment_term'
        es_iva = bool(tax_line)
        
        marker = ""
        if es_payment_term:
            marker = " ⚠️ CONTRAPARTIDA"
            total_payment_term += abs(balance)
        elif es_iva:
            marker = " 🔶 LÍNEA IVA"
            total_iva_lines += abs(balance)
        
        if ifrs3 and not es_payment_term:
            total_con_ifrs3 += abs(balance)
        elif not es_payment_term and not es_iva:
            total_sin_ifrs3 += abs(balance)
        
        total_balance += balance
        
        analytic_str = json.dumps(analytic) if analytic else '-'
        
        print(f"  {l['id']:>3} {display_type:>14} {acc_info['code']:>12} {acc_info['name'][:40]:>40} {balance:>20,.0f} {ifrs3[:25]:>25} {analytic_str[:50]}{marker}")
    
    print("  " + "-" * 160)
    print(f"  {'':>3} {'':>14} {'':>12} {'TOTAL':>40} {total_balance:>20,.0f}")
    
    print(f"\n  📊 RESUMEN DE LÍNEAS:")
    print(f"     Línea Contrapartida (payment_term): ${total_payment_term:>20,.0f}")
    print(f"     Líneas IVA (tax_line_id):           ${total_iva_lines:>20,.0f}")
    print(f"     Líneas con IFRS3 (gastos):          ${total_con_ifrs3:>20,.0f}")
    print(f"     Líneas sin IFRS3 ni IVA:            ${total_sin_ifrs3:>20,.0f}")

    # ═══════════════════════════════════════════════════════════════
    # PARTE 3: Simular el cálculo de PONDERADORES (como real_proyectado.py)
    # ═══════════════════════════════════════════════════════════════
    print("\n" + "═" * 80)
    print("PARTE 3: SIMULACIÓN DE PONDERADORES")
    print("═" * 80)
    
    from collections import defaultdict
    
    # Obtener nombres analíticos
    analytic_ids = set()
    for l in lineas:
        ad = l.get('analytic_distribution') or {}
        if isinstance(ad, str):
            try: ad = json.loads(ad)
            except: ad = {}
        for k in (ad or {}).keys():
            try: analytic_ids.add(int(str(k)))
            except: pass
    
    nombre_analitico = {}
    if analytic_ids:
        analiticos = odoo.read('account.analytic.account', list(analytic_ids), ['id', 'name'])
        for a in analiticos:
            nombre_analitico[a['id']] = a.get('name', f'Analítico {a["id"]}')
    
    amount_total = float(f.get('amount_total', 0))
    monto_proyectado = -amount_total  # signo negativo para CxP (in_invoice)
    
    print(f"\n  amount_total del header: ${amount_total:,.0f}")
    print(f"  monto_proyectado (-amount_total): ${monto_proyectado:,.0f}")
    
    # === Escenario A: Sin filtro (código ANTERIOR al fix) ===
    print(f"\n  --- Escenario A: SIN excluir payment_term (código viejo) ---")
    ponderadores_A = defaultdict(float)
    for l in lineas:
        acc_id = l.get('account_id', [0])[0] if isinstance(l.get('account_id'), (list, tuple)) else 0
        ifrs3 = (ifrs3_map.get(acc_id, {}).get('ifrs3') or '').strip()
        if not ifrs3:
            continue
        balance = abs(float(l.get('balance') or 0))
        peso_base = balance if balance > 0 else 1.0
        
        ad = l.get('analytic_distribution') or {}
        if isinstance(ad, str):
            try: ad = json.loads(ad)
            except: ad = {}
        
        if isinstance(ad, dict) and len(ad) > 0:
            for k, pct in ad.items():
                try: aid = int(str(k))
                except: aid = None
                pct_val = float(pct) if pct else 0
                if pct_val <= 0: continue
                nom = nombre_analitico.get(aid, f'Analítico {k}')
                ponderadores_A[(ifrs3, nom)] += peso_base * (pct_val / 100)
        else:
            ponderadores_A[(ifrs3, 'Sin Analítico')] += peso_base
    
    total_peso_A = sum(ponderadores_A.values())
    print(f"  Total peso: {total_peso_A:,.0f}")
    for (cat, analitico), peso in sorted(ponderadores_A.items()):
        proporcion = peso / total_peso_A if total_peso_A > 0 else 0
        monto = monto_proyectado * proporcion
        print(f"    {cat:30s} | {analitico:20s} | peso={peso:>15,.0f} | prop={proporcion:>8.2%} | monto=${monto:>20,.0f}")
    print(f"  TOTAL asignado: ${sum(monto_proyectado * (p/total_peso_A) for p in ponderadores_A.values()) if total_peso_A > 0 else 0:,.0f}")
    
    # === Escenario B: CON filtro payment_term (fix actual) ===
    print(f"\n  --- Escenario B: CON excluir payment_term (fix actual) ---")
    ponderadores_B = defaultdict(float)
    for l in lineas:
        if l.get('display_type') == 'payment_term':
            continue
        acc_id = l.get('account_id', [0])[0] if isinstance(l.get('account_id'), (list, tuple)) else 0
        ifrs3 = (ifrs3_map.get(acc_id, {}).get('ifrs3') or '').strip()
        if not ifrs3:
            continue
        balance = abs(float(l.get('balance') or 0))
        peso_base = balance if balance > 0 else 1.0
        
        ad = l.get('analytic_distribution') or {}
        if isinstance(ad, str):
            try: ad = json.loads(ad)
            except: ad = {}
        
        if isinstance(ad, dict) and len(ad) > 0:
            for k, pct in ad.items():
                try: aid = int(str(k))
                except: aid = None
                pct_val = float(pct) if pct else 0
                if pct_val <= 0: continue
                nom = nombre_analitico.get(aid, f'Analítico {k}')
                ponderadores_B[(ifrs3, nom)] += peso_base * (pct_val / 100)
        else:
            ponderadores_B[(ifrs3, 'Sin Analítico')] += peso_base
    
    total_peso_B = sum(ponderadores_B.values())
    print(f"  Total peso: {total_peso_B:,.0f}")
    for (cat, analitico), peso in sorted(ponderadores_B.items()):
        proporcion = peso / total_peso_B if total_peso_B > 0 else 0
        monto = monto_proyectado * proporcion
        print(f"    {cat:30s} | {analitico:20s} | peso={peso:>15,.0f} | prop={proporcion:>8.2%} | monto=${monto:>20,.0f}")
    print(f"  TOTAL asignado: ${sum(monto_proyectado * (p/total_peso_B) for p in ponderadores_B.values()) if total_peso_B > 0 else 0:,.0f}")
    
    # === Escenario C: Excluir payment_term Y excluir IVA lines ===
    print(f"\n  --- Escenario C: Excluir payment_term Y excluir líneas IVA (solo base) ---")
    ponderadores_C = defaultdict(float)
    for l in lineas:
        if l.get('display_type') == 'payment_term':
            continue
        if l.get('tax_line_id'):  # Es línea de IVA
            continue
        acc_id = l.get('account_id', [0])[0] if isinstance(l.get('account_id'), (list, tuple)) else 0
        ifrs3 = (ifrs3_map.get(acc_id, {}).get('ifrs3') or '').strip()
        if not ifrs3:
            continue
        balance = abs(float(l.get('balance') or 0))
        peso_base = balance if balance > 0 else 1.0
        
        ad = l.get('analytic_distribution') or {}
        if isinstance(ad, str):
            try: ad = json.loads(ad)
            except: ad = {}
        
        if isinstance(ad, dict) and len(ad) > 0:
            for k, pct in ad.items():
                try: aid = int(str(k))
                except: aid = None
                pct_val = float(pct) if pct else 0
                if pct_val <= 0: continue
                nom = nombre_analitico.get(aid, f'Analítico {k}')
                ponderadores_C[(ifrs3, nom)] += peso_base * (pct_val / 100)
        else:
            ponderadores_C[(ifrs3, 'Sin Analítico')] += peso_base
    
    total_peso_C = sum(ponderadores_C.values())
    print(f"  Total peso: {total_peso_C:,.0f}")
    for (cat, analitico), peso in sorted(ponderadores_C.items()):
        proporcion = peso / total_peso_C if total_peso_C > 0 else 0
        monto = monto_proyectado * proporcion
        print(f"    {cat:30s} | {analitico:20s} | peso={peso:>15,.0f} | prop={proporcion:>8.2%} | monto=${monto:>20,.0f}")
    print(f"  TOTAL asignado: ${sum(monto_proyectado * (p/total_peso_C) for p in ponderadores_C.values()) if total_peso_C > 0 else 0:,.0f}")

# ═══════════════════════════════════════════════════════════════
# PARTE 4: Análisis global - ¿Cómo se trata IVA en todo OPERACIÓN?
# ═══════════════════════════════════════════════════════════════
print("\n" + "═" * 80)
print("PARTE 4: MAPEO GLOBAL - ¿QUÉ PASA CON CUENTAS DE IVA?")
print("═" * 80)

# Buscar cuentas de IVA comunes en Chile
cuentas_iva = odoo.search_read(
    'account.account',
    [['code', 'like', '1106']],  # IVA Crédito Fiscal típicamente
    ['id', 'code', 'name', 'x_studio_cat_ifrs_3'],
    limit=50
)

# Mapeo de prefijos del flujo de caja
mapeo_prefijos = {
    '41': 'OP01 - Cobros ventas',
    '51': 'OP02 - Pagos proveedores',
    '52': 'OP02 - Pagos proveedores',
    '53': 'OP02 - Pagos proveedores',
    '61': 'OP03 - Remuneraciones',
    '62': 'OP03 - Remuneraciones',
    '65': 'OP04 - Intereses pagados',
    '42': 'OP05 - Intereses recibidos',
    '77': 'OP05 - Otros ingresos fin.',
    '91': 'OP06 - Impuestos',
    '63': 'OP07 - Otros gastos op.',
    '64': 'OP07 - Otros gastos op.',
    '66': 'OP07 - Otros gastos op.',
    '67': 'OP07 - Otros gastos op.',
    '68': 'OP07 - Otros gastos op.',
    '69': 'OP07 - Otros gastos op.',
    '13': 'IN01 - Adq. intangibles',
    '12': 'IN02 - PPE',
    '71': 'IN03 - Venta activos',
    '81': 'IN04 - Costo venta activos',
    '21': 'FI01 - Préstamos CP',
    '22': 'FI02 - Préstamos LP',
    '31': 'FI03 - Aportes capital',
    '32': 'FI04 - Distribuciones',
}

print(f"\n  Cuentas de IVA encontradas ({len(cuentas_iva)}):")
for c in sorted(cuentas_iva, key=lambda x: x.get('code', '')):
    code = c.get('code', '')
    ifrs3 = (c.get('x_studio_cat_ifrs_3') or '').strip()
    
    # ¿Se mapea a algún concepto?
    concepto_mapeado = 'NO MAPEADO ❌'
    for prefix, concepto in mapeo_prefijos.items():
        if code.startswith(prefix):
            concepto_mapeado = concepto
            break
    
    print(f"    {code:>12} | {c.get('name', '')[:45]:45} | IFRS3: {ifrs3 or 'VACÍO':25} | Mapeo: {concepto_mapeado}")

# Buscar también cuentas IVA Débito (2106xx)
print(f"\n  Cuentas de IVA Débito (2106xx):")
cuentas_iva_debito = odoo.search_read(
    'account.account',
    [['code', 'like', '2106']],
    ['id', 'code', 'name', 'x_studio_cat_ifrs_3'],
    limit=50
)

for c in sorted(cuentas_iva_debito, key=lambda x: x.get('code', '')):
    code = c.get('code', '')
    ifrs3 = (c.get('x_studio_cat_ifrs_3') or '').strip()
    concepto_mapeado = 'NO MAPEADO ❌'
    for prefix, concepto in mapeo_prefijos.items():
        if code.startswith(prefix):
            concepto_mapeado = concepto
            break
    print(f"    {code:>12} | {c.get('name', '')[:45]:45} | IFRS3: {ifrs3 or 'VACÍO':25} | Mapeo: {concepto_mapeado}")

# ═══════════════════════════════════════════════════════════════
# PARTE 5: Para facturas reales (posted) en CxP, ¿amount_total incluye IVA?
# ═══════════════════════════════════════════════════════════════
print("\n" + "═" * 80)
print("PARTE 5: FACTURAS REALES (POSTED) - ¿amount_total incluye IVA?")
print("═" * 80)

# Tomar 5 facturas recientes de proveedores
facturas_ejemplo = odoo.search_read(
    'account.move',
    [
        ['move_type', '=', 'in_invoice'],
        ['journal_id', '=', 2],
        ['state', '=', 'posted'],
        ['date', '>=', '2026-01-01']
    ],
    ['id', 'name', 'partner_id', 'amount_untaxed', 'amount_tax', 'amount_total', 'amount_residual'],
    limit=5
)

print(f"\n  5 facturas posted recientes de proveedores:")
print(f"  {'Factura':>15} {'Partner':>35} {'Base':>18} {'IVA':>18} {'Total':>18} {'Residual':>18}")
print("  " + "-" * 130)
for fx in facturas_ejemplo:
    partner = fx.get('partner_id', [0, ''])[1][:35] if isinstance(fx.get('partner_id'), (list, tuple)) else ''
    print(f"  {fx.get('name', ''):>15} {partner:>35} ${fx.get('amount_untaxed', 0):>15,.0f} ${fx.get('amount_tax', 0):>15,.0f} ${fx.get('amount_total', 0):>15,.0f} ${fx.get('amount_residual', 0):>15,.0f}")

print(f"\n  ℹ️  En real_proyectado.py, calcular_pagos_proveedores usa:")
print(f"     - PAGADAS:   monto_real = -(amount_total - amount_residual) → INCLUYE IVA ✅")
print(f"     - PARCIALES: monto_real = -(amount_total - amount_residual) → INCLUYE IVA ✅")
print(f"     - NO_PAGADAS: monto_proyectado = -amount_residual → INCLUYE IVA ✅")
print(f"     - PROYECT. COMPRAS: amount_total de purchase.order → INCLUYE IVA ✅")
print(f"     - PROYECT. CONTAB:  amount_total del account.move → INCLUYE IVA ✅")

# ═══════════════════════════════════════════════════════════════
# PARTE 6: Todas las facturas en diario Proyecciones Futuras
# ═══════════════════════════════════════════════════════════════
print("\n" + "═" * 80)
print("PARTE 6: TODAS LAS FACTURAS EN DIARIO 'PROYECCIONES FUTURAS' (ID=130)")
print("═" * 80)

facturas_proy = odoo.search_read(
    'account.move',
    [
        ['journal_id', '=', 130],
        ['move_type', 'in', ['in_invoice', 'in_refund']]
    ],
    ['id', 'name', 'partner_id', 'amount_untaxed', 'amount_tax', 'amount_total',
     'date', 'invoice_date_due', 'state', 'move_type'],
    limit=100
)

print(f"\n  Total facturas en Proyecciones Futuras: {len(facturas_proy)}")
print(f"\n  {'ID':>8} {'Nombre':>15} {'Partner':>30} {'Base':>18} {'IVA':>18} {'Total':>18} {'Estado':>10} {'Fecha':>12}")
print("  " + "-" * 150)

total_base = 0
total_iva = 0
total_total = 0

for fx in sorted(facturas_proy, key=lambda x: x.get('amount_total', 0), reverse=True):
    partner = fx.get('partner_id', [0, ''])[1][:30] if isinstance(fx.get('partner_id'), (list, tuple)) else ''
    base = float(fx.get('amount_untaxed', 0) or 0)
    iva = float(fx.get('amount_tax', 0) or 0)
    total = float(fx.get('amount_total', 0) or 0)
    total_base += base
    total_iva += iva
    total_total += total
    
    print(f"  {fx.get('id', ''):>8} {fx.get('name', ''):>15} {partner:>30} ${base:>15,.0f} ${iva:>15,.0f} ${total:>15,.0f} {fx.get('state', ''):>10} {str(fx.get('invoice_date_due') or fx.get('date') or ''):>12}")

print("  " + "-" * 150)
print(f"  {'':>8} {'':>15} {'TOTALES':>30} ${total_base:>15,.0f} ${total_iva:>15,.0f} ${total_total:>15,.0f}")
print(f"\n  💡 Diferencia (Total - Base) = IVA: ${total_iva:,.0f}")
print(f"  💡 Porcentaje IVA: {(total_iva/total_base*100) if total_base else 0:.1f}%")

# ═══════════════════════════════════════════════════════════════
# PARTE 7: ¿Qué campo usa realmente el código para el monto?
# ═══════════════════════════════════════════════════════════════
print("\n" + "═" * 80)
print("PARTE 7: CONCLUSIÓN - ¿DÓNDE FALTA EL IVA?")
print("═" * 80)

print("""
  El código actual en real_proyectado.py usa `amount_total` para TODOS los tipos:
  
  1. Facturas Posted (PAGADAS/PARCIALES/NO_PAGADAS):
     → amount_total y amount_residual → AMBOS INCLUYEN IVA ✅
  
  2. Proyectadas Compras (purchase.order):
     → amount_total → INCLUYE IVA ✅
  
  3. Proyectadas Contabilidad (diario 130):
     → amount_total → INCLUYE IVA ✅
  
  PERO: La DISTRIBUCIÓN por categoría IFRS3 usa las líneas (account.move.line)
  y los ponderadores se calculan sobre `balance` de cada línea.
  
  POSIBLE PROBLEMA:
  - Si la línea de IVA (tax_line) tiene IFRS3 ≠ vacío → se incluye como categoría aparte
  - Si la línea de IVA tiene IFRS3 vacío → se EXCLUYE de ponderadores
    → PERO el monto_total completo (con IVA) se distribuye entre las líneas CON IFRS3
    → Resultado: el IVA está INCLUIDO en el total pero atribuido a las categorías de gasto
  
  CONCLUSIÓN: El IVA sí se está mostrando en el TOTAL, pero NO como categoría separada.
  El boss puede querer que el IVA aparezca como una categoría/línea PROPIA en el desglose.
""")

print("\n✅ DEBUG COMPLETO")
