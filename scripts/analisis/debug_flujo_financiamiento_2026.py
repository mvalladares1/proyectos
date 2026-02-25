"""
Debug: Flujo de Caja - Seccion 3: Actividades de Financiamiento (2026)
======================================================================

Reproduce exactamente la logica de flujo_caja_service.py para actividades de
financiamiento, mostrando cada paso del calculo:

1. Identifica cuentas de efectivo (cash accounts)
2. Obtiene movimientos de efectivo en el periodo
3. Busca contrapartidas en los asientos que tocaron efectivo
4. Clasifica cada contrapartida usando CUENTAS_FIJAS_FINANCIAMIENTO
5. Agrega por concepto NIIF y mes
6. Compara con lo que mostraria el dashboard

CUENTAS DE FINANCIAMIENTO MAPEADAS:
  3.0.1 - Prestamos LP: 21010213, 21010223, 22010101
  3.0.2 - Prestamos CP: 21010101, 21010102, 21010103, 82010101
  3.1.1 - Entidades Relacionadas: 21030201, 21030211, 22020101
  3.1.4 - Leasing: 21010201, 21010202, 21010204, 22010202, 22010204, 82010102
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'c:\new\RIO FUTURO\DASHBOARD\proyectos')

from xmlrpc import client as xmlrpc_client
from collections import defaultdict
from datetime import datetime, timedelta

# ======================== CONEXIÓN ========================
url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

common = xmlrpc_client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
if not uid:
    print("❌ Error de autenticación")
    sys.exit(1)
print(f"✅ Autenticado como uid={uid}")

models = xmlrpc_client.ServerProxy(f'{url}/xmlrpc/2/object')

def search_read(model, domain, fields, limit=10000, order=None):
    kwargs = {'fields': fields, 'limit': limit}
    if order:
        kwargs['order'] = order
    return models.execute_kw(db, uid, password, model, 'search_read', [domain], kwargs)

def read_group(model, domain, fields, groupby, limit=10000):
    return models.execute_kw(db, uid, password, model, 'read_group', [domain, fields, groupby], {'limit': limit})

# ======================== CONSTANTES ========================
# Mismas constantes que constants.py
CUENTAS_FIJAS_FINANCIAMIENTO = {
    "21010101": "3.0.2", "21010102": "3.0.2", "21010103": "3.0.2", "82010101": "3.0.2",
    "21010213": "3.0.1", "21010223": "3.0.1", "22010101": "3.0.1",
    "21030201": "3.1.1", "21030211": "3.1.1", "22020101": "3.1.1",
    "21010201": "3.1.4", "21010202": "3.1.4", "21010204": "3.1.4",
    "22010202": "3.1.4", "22010204": "3.1.4", "82010102": "3.1.4"
}

NOMBRES_CONCEPTO = {
    "3.0.1": "Importes procedentes de préstamos de largo plazo",
    "3.0.2": "Importes procedentes de préstamos de corto plazo",
    "3.1":   "Total importes procedentes de préstamos",
    "3.1.1": "Préstamos de entidades relacionadas",
    "3.1.2": "Pagos de préstamos",
    "3.1.3": "Pagos de préstamos a entidades relacionadas",
    "3.1.4": "Pagos de pasivos por arrendamientos financieros",
    "3.1.5": "Dividendos pagados",
    "3.T":   "TOTAL Financiamiento",
}

# Período de análisis
FECHA_INICIO = "2026-01-01"
FECHA_FIN = "2026-02-25"

print(f"\n{'='*80}")
print(f"DEBUG FLUJO DE CAJA - SECCIÓN 3: FINANCIAMIENTO")
print(f"Período: {FECHA_INICIO} a {FECHA_FIN}")
print(f"{'='*80}")

# ======================== PASO 1: CUENTAS DE EFECTIVO ========================
print(f"\n{'='*80}")
print("PASO 1: Identificando cuentas de efectivo...")
print(f"{'='*80}")

# Buscar cuentas con prefijos 1101 y 1102 (misma lógica que mapeo_cuentas.json)
cuentas_efectivo = search_read(
    'account.account',
    [['code', 'like', '1101%']],
    ['id', 'code', 'name'],
    limit=100
)
cuentas_efectivo_2 = search_read(
    'account.account',
    [['code', 'like', '1102%']],
    ['id', 'code', 'name'],
    limit=100
)
cuentas_efectivo.extend(cuentas_efectivo_2)

# También buscar códigos específicos del mapeo_flujo_caja.json
codigos_especificos = ["10000000", "10000001"]
for cod in codigos_especificos:
    cuentas_esp = search_read(
        'account.account',
        [['code', '=', cod]],
        ['id', 'code', 'name'],
        limit=1
    )
    for c in cuentas_esp:
        if c['id'] not in [x['id'] for x in cuentas_efectivo]:
            cuentas_efectivo.append(c)

cuentas_efectivo_ids = [c['id'] for c in cuentas_efectivo]
print(f"Encontradas {len(cuentas_efectivo)} cuentas de efectivo:")
for c in sorted(cuentas_efectivo, key=lambda x: x['code']):
    print(f"  ID {c['id']:5d}: {c['code']} - {c['name']}")

# ======================== PASO 2: MOVIMIENTOS DE EFECTIVO ========================
print(f"\n{'='*80}")
print("PASO 2: Obteniendo movimientos de efectivo en el período...")
print(f"{'='*80}")

# Buscar move lines en cuentas de efectivo, posted
movimientos = search_read(
    'account.move.line',
    [
        ['account_id', 'in', cuentas_efectivo_ids],
        ['date', '>=', FECHA_INICIO],
        ['date', '<=', FECHA_FIN],
        ['parent_state', '=', 'posted']
    ],
    ['id', 'move_id', 'account_id', 'debit', 'credit', 'balance', 'date', 'name'],
    limit=50000
)

print(f"Total movimientos de efectivo: {len(movimientos)}")

# Extraer IDs de asientos únicos
asientos_ids = list(set(m['move_id'][0] for m in movimientos if m.get('move_id')))
print(f"Asientos contables únicos que tocaron efectivo: {len(asientos_ids)}")

# Resumen por mes
mov_por_mes = defaultdict(lambda: {'count': 0, 'debit': 0, 'credit': 0, 'balance': 0})
for m in movimientos:
    mes = str(m['date'])[:7]
    mov_por_mes[mes]['count'] += 1
    mov_por_mes[mes]['debit'] += m.get('debit', 0) or 0
    mov_por_mes[mes]['credit'] += m.get('credit', 0) or 0
    mov_por_mes[mes]['balance'] += m.get('balance', 0) or 0

print("\nResumen por mes (movimientos de efectivo):")
print(f"  {'Mes':<10} | {'Cant':>6} | {'Débito':>18} | {'Crédito':>18} | {'Balance':>18}")
print(f"  {'-'*75}")
for mes in sorted(mov_por_mes.keys()):
    d = mov_por_mes[mes]
    print(f"  {mes:<10} | {d['count']:>6} | ${d['debit']:>15,.0f} | ${d['credit']:>15,.0f} | ${d['balance']:>15,.0f}")

# ======================== PASO 3: CONTRAPARTIDAS AGRUPADAS ========================
print(f"\n{'='*80}")
print("PASO 3: Obteniendo contrapartidas agrupadas por cuenta y mes...")
print(f"(Excluyendo cuentas de efectivo - misma lógica que Query A)")
print(f"{'='*80}")

# read_group de las contrapartidas (no-efectivo) agrupadas por account_id y date:month
# Filtra: asientos que tocaron efectivo, cuentas NO de efectivo
contrapartidas = read_group(
    'account.move.line',
    [
        ['move_id', 'in', asientos_ids],
        ['account_id', 'not in', cuentas_efectivo_ids],
        ['parent_state', '=', 'posted']
    ],
    ['account_id', 'balance', 'date'],
    ['account_id', 'date:month'],
    limit=50000
)

print(f"Total grupos contrapartida: {len(contrapartidas)}")

# ======================== PASO 4: FILTRAR SOLO FINANCIAMIENTO ========================
print(f"\n{'='*80}")
print("PASO 4: Filtrando contrapartidas de FINANCIAMIENTO...")
print(f"{'='*80}")

# Necesitamos obtener los códigos de cuenta de los account_ids
account_ids_unicos = list(set(
    g['account_id'][0] for g in contrapartidas if g.get('account_id')
))

print(f"Consultando info de {len(account_ids_unicos)} cuentas únicas de contrapartida...")
cuentas_info = {}
BATCH_SIZE = 200
for i in range(0, len(account_ids_unicos), BATCH_SIZE):
    batch = account_ids_unicos[i:i+BATCH_SIZE]
    accs = search_read('account.account', [['id', 'in', batch]], ['id', 'code', 'name'], limit=BATCH_SIZE)
    for a in accs:
        cuentas_info[a['id']] = {'code': a['code'], 'name': a['name']}

# Clasificar y filtrar solo financiamiento
financiamiento_por_concepto_mes = defaultdict(lambda: defaultdict(float))
financiamiento_cuentas_detalle = defaultdict(lambda: defaultdict(lambda: {'balance': 0, 'nombre': '', 'concepto': ''}))
total_financiamiento = 0
cuentas_financiamiento_detectadas = set()

# También trackear lo que NO es financiamiento pero tiene prefijo 21/22/31/32
cuentas_no_mapeadas_fi = defaultdict(lambda: {'balance': 0, 'nombre': ''})

for grupo in contrapartidas:
    acc_data = grupo.get('account_id')
    if not acc_data:
        continue
    
    acc_id = acc_data[0]
    info = cuentas_info.get(acc_id, {})
    codigo = info.get('code', '')
    nombre = info.get('name', '')
    balance = grupo.get('balance', 0) or 0
    
    # Parsear mes
    date_month = grupo.get('date:month', '')
    if not date_month:
        continue
    
    # Parsear mes de formato Odoo ("Enero 2026" o "January 2026")
    meses_es = {
        "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
        "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
        "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
    }
    meses_en = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12"
    }
    
    mes_parsed = None
    if date_month and len(date_month) == 7 and date_month[4] == '-':
        mes_parsed = date_month
    else:
        try:
            parts = date_month.strip().lower().split()
            if len(parts) >= 2:
                mes_nombre = parts[0]
                año = parts[1]
                mes_num = meses_es.get(mes_nombre) or meses_en.get(mes_nombre)
                if mes_num and año.isdigit():
                    mes_parsed = f"{año}-{mes_num}"
        except:
            pass
    
    if not mes_parsed:
        continue
    
    # Clasificar: ¿Es cuenta de financiamiento?
    concepto = CUENTAS_FIJAS_FINANCIAMIENTO.get(codigo)
    
    if concepto:
        # Es cuenta de financiamiento fija
        financiamiento_por_concepto_mes[concepto][mes_parsed] += balance
        financiamiento_cuentas_detalle[concepto][codigo]['balance'] += balance
        financiamiento_cuentas_detalle[concepto][codigo]['nombre'] = nombre
        financiamiento_cuentas_detalle[concepto][codigo]['concepto'] = concepto
        cuentas_financiamiento_detectadas.add(codigo)
        total_financiamiento += balance
    elif codigo[:2] in ['21', '22', '31', '32']:
        # Prefijo sugiere financiamiento pero NO está en CUENTAS_FIJAS
        cuentas_no_mapeadas_fi[codigo]['balance'] += balance
        cuentas_no_mapeadas_fi[codigo]['nombre'] = nombre

# ======================== PASO 5: RESULTADOS ========================
print(f"\n{'='*80}")
print("PASO 5: RESULTADOS - Flujos de Financiamiento por Concepto y Mes")
print(f"{'='*80}")

# Todos los meses encontrados
todos_meses = sorted(set(
    mes for conceptos in financiamiento_por_concepto_mes.values() for mes in conceptos.keys()
))

if not todos_meses:
    print("\n⚠️ No se encontraron movimientos de financiamiento en el período")
else:
    for concepto_id in sorted(financiamiento_por_concepto_mes.keys()):
        nombre_concepto = NOMBRES_CONCEPTO.get(concepto_id, concepto_id)
        total_concepto = sum(financiamiento_por_concepto_mes[concepto_id].values())
        
        print(f"\n📋 {concepto_id} - {nombre_concepto}")
        print(f"   {'Mes':<10} | {'Balance':>18}")
        print(f"   {'-'*30}")
        
        for mes in todos_meses:
            valor = financiamiento_por_concepto_mes[concepto_id].get(mes, 0)
            if valor != 0:
                print(f"   {mes:<10} | ${valor:>15,.0f}")
        
        print(f"   {'TOTAL':<10} | ${total_concepto:>15,.0f}")
        
        # Detalle de cuentas
        print(f"   Cuentas que aportan:")
        for codigo, data in sorted(financiamiento_cuentas_detalle[concepto_id].items()):
            print(f"     {codigo} ({data['nombre'][:40]}): ${data['balance']:>12,.0f}")

# ======================== PASO 6: TOTALES ========================
print(f"\n{'='*80}")
print("PASO 6: RESUMEN TOTAL FINANCIAMIENTO")
print(f"{'='*80}")

print(f"\n{'Concepto':<55} | ", end="")
for mes in todos_meses:
    print(f"{'  ' + mes:>14} | ", end="")
print(f"{'TOTAL':>14}")

print(f"{'-'*55}-+-", end="")
for mes in todos_meses:
    print(f"{'-'*14}-+-", end="")
print(f"{'-'*14}")

gran_total = 0
for concepto_id in ["3.0.1", "3.0.2", "3.1.1", "3.1.2", "3.1.3", "3.1.4", "3.1.5"]:
    nombre = NOMBRES_CONCEPTO.get(concepto_id, concepto_id)
    total_c = sum(financiamiento_por_concepto_mes.get(concepto_id, {}).values())
    
    if total_c == 0 and concepto_id not in financiamiento_por_concepto_mes:
        print(f"{concepto_id} {nombre[:50]:<52} | ", end="")
        for mes in todos_meses:
            print(f"{'$0':>14} | ", end="")
        print(f"{'$0':>14}")
        continue
    
    print(f"{concepto_id} {nombre[:50]:<52} | ", end="")
    for mes in todos_meses:
        val = financiamiento_por_concepto_mes.get(concepto_id, {}).get(mes, 0)
        print(f"${val:>12,.0f} | ", end="")
    print(f"${total_c:>12,.0f}")
    gran_total += total_c

print(f"{'-'*55}-+-", end="")
for mes in todos_meses:
    print(f"{'-'*14}-+-", end="")
print(f"{'-'*14}")

print(f"{'3.T TOTAL FINANCIAMIENTO':<55} | ", end="")
for mes in todos_meses:
    total_mes = sum(
        financiamiento_por_concepto_mes.get(c, {}).get(mes, 0)
        for c in ["3.0.1", "3.0.2", "3.1.1", "3.1.2", "3.1.3", "3.1.4", "3.1.5"]
    )
    print(f"${total_mes:>12,.0f} | ", end="")
print(f"${gran_total:>12,.0f}")

# ======================== PASO 7: CUENTAS CON PREFIJO FI NO MAPEADAS ========================
print(f"\n{'='*80}")
print("PASO 7: CUENTAS CON PREFIJO 21/22/31/32 NO EN CUENTAS_FIJAS_FINANCIAMIENTO")
print("(Posiblemente deberían ser financiamiento pero no están mapeadas)")
print(f"{'='*80}")

if cuentas_no_mapeadas_fi:
    print(f"\n{'Código':<12} | {'Nombre':<45} | {'Balance':>15}")
    print(f"{'-'*78}")
    for codigo in sorted(cuentas_no_mapeadas_fi.keys()):
        data = cuentas_no_mapeadas_fi[codigo]
        print(f"{codigo:<12} | {data['nombre'][:45]:<45} | ${data['balance']:>12,.0f}")
    total_no_mapeado = sum(d['balance'] for d in cuentas_no_mapeadas_fi.values())
    print(f"{'TOTAL':<12} | {'':45} | ${total_no_mapeado:>12,.0f}")
else:
    print("\n✅ No hay cuentas con prefijo 21/22/31/32 sin mapear")

# ======================== PASO 8: DESGLOSE POR ASIENTO INDIVIDUAL ========================
print(f"\n{'='*80}")
print("PASO 8: TOP 20 ASIENTOS MÁS GRANDES DE FINANCIAMIENTO")
print(f"{'='*80}")

# Para cada cuenta de financiamiento, buscar las líneas individuales
fi_codes = list(CUENTAS_FIJAS_FINANCIAMIENTO.keys())
fi_accounts = search_read(
    'account.account',
    [['code', 'in', fi_codes]],
    ['id', 'code', 'name'],
    limit=50
)
fi_account_ids = [a['id'] for a in fi_accounts]
fi_code_by_id = {a['id']: a['code'] for a in fi_accounts}

if fi_account_ids:
    # Líneas individuales de financiamiento
    lineas_fi = search_read(
        'account.move.line',
        [
            ['move_id', 'in', asientos_ids],
            ['account_id', 'in', fi_account_ids],
            ['parent_state', '=', 'posted']
        ],
        ['id', 'move_id', 'account_id', 'debit', 'credit', 'balance', 'date', 'name', 'ref'],
        limit=10000,
        order='balance asc'
    )
    
    # Ordenar por balance absoluto
    lineas_fi_sorted = sorted(lineas_fi, key=lambda x: abs(x.get('balance', 0) or 0), reverse=True)
    
    print(f"\nTotal líneas de financiamiento: {len(lineas_fi)}")
    print(f"\n{'Fecha':<12} | {'Asiento':<15} | {'Cuenta':<10} | {'Concepto':<8} | {'Balance':>15} | {'Ref/Nombre':<30}")
    print(f"{'-'*100}")
    
    for l in lineas_fi_sorted[:20]:
        acc_id = l['account_id'][0] if isinstance(l['account_id'], (list, tuple)) else l['account_id']
        codigo = fi_code_by_id.get(acc_id, '?')
        concepto = CUENTAS_FIJAS_FINANCIAMIENTO.get(codigo, '?')
        move_name = l['move_id'][1] if isinstance(l['move_id'], (list, tuple)) else str(l['move_id'])
        ref_name = (l.get('name') or l.get('ref') or '')[:30]
        print(f"{str(l['date']):<12} | {move_name[:15]:<15} | {codigo:<10} | {concepto:<8} | ${l.get('balance', 0):>12,.0f} | {ref_name}")

# ======================== PASO 9: VERIFICACIÓN CRUZADA ========================
print(f"\n{'='*80}")
print("PASO 9: VERIFICACIÓN CRUZADA - Balance de cuentas de financiamiento")
print(f"{'='*80}")
print("(Saldo directo de cada cuenta de financiamiento al inicio y fin del período)")

for codigo in sorted(CUENTAS_FIJAS_FINANCIAMIENTO.keys()):
    concepto = CUENTAS_FIJAS_FINANCIAMIENTO[codigo]
    
    # Buscar account_id
    acc = search_read('account.account', [['code', '=', codigo]], ['id', 'name'], limit=1)
    if not acc:
        print(f"  {codigo}: ❌ Cuenta no encontrada en Odoo")
        continue
    
    acc_id = acc[0]['id']
    acc_name = acc[0]['name']
    
    # Saldo al inicio del período
    fecha_ini_dt = datetime.strptime(FECHA_INICIO, '%Y-%m-%d')
    fecha_anterior = (fecha_ini_dt - timedelta(days=1)).strftime('%Y-%m-%d')
    
    saldo_inicio_result = read_group(
        'account.move.line',
        [
            ['account_id', '=', acc_id],
            ['date', '<=', fecha_anterior],
            ['parent_state', '=', 'posted']
        ],
        ['balance'],
        [],
        limit=1
    )
    saldo_inicio = saldo_inicio_result[0].get('balance', 0) if saldo_inicio_result else 0
    
    saldo_fin_result = read_group(
        'account.move.line',
        [
            ['account_id', '=', acc_id],
            ['date', '<=', FECHA_FIN],
            ['parent_state', '=', 'posted']
        ],
        ['balance'],
        [],
        limit=1
    )
    saldo_fin = saldo_fin_result[0].get('balance', 0) if saldo_fin_result else 0
    
    variacion = saldo_fin - saldo_inicio
    
    # Movimiento que pasa por caja (lo que el dashboard debería mostrar)
    mov_por_caja = financiamiento_cuentas_detalle.get(concepto, {}).get(codigo, {}).get('balance', 0)
    
    diff = variacion - mov_por_caja
    flag = "⚠️" if abs(diff) > 1 else "✅"
    
    print(f"\n  {codigo} - {acc_name[:40]} → Concepto {concepto}")
    print(f"    Saldo inicio (al {fecha_anterior}): ${saldo_inicio:>15,.0f}")
    print(f"    Saldo fin    (al {FECHA_FIN}):    ${saldo_fin:>15,.0f}")
    print(f"    Variación total:                   ${variacion:>15,.0f}")
    print(f"    Movimientos por caja (dashboard):   ${mov_por_caja:>15,.0f}")
    print(f"    Diferencia (no pasó por caja):      ${diff:>15,.0f} {flag}")

print(f"\n{'='*80}")
print("✅ DEBUG COMPLETADO")
print(f"{'='*80}")
