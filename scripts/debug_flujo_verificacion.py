"""
Script de Verificación Exhaustiva del Flujo de Efectivo
========================================================
Este script verifica paso a paso que los datos del flujo de caja
coinciden con los movimientos reales en Odoo.

Ejecutar: python scripts/debug_flujo_verificacion.py
"""
import xmlrpc.client
import json
from datetime import datetime, timedelta
from collections import defaultdict

# === CONFIGURACIÓN ===
ODOO_URL = "https://riofuturo.server98c6e.oerpondemand.net"
ODOO_DB = "riofuturo-master"
ODOO_USER = "mvalladares@riofuturo.cl"
ODOO_PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Período a verificar
FECHA_INICIO = "2026-01-01"
FECHA_FIN = "2026-01-31"

def conectar_odoo():
    """Conecta a Odoo y retorna uid y models."""
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise Exception("Error de autenticación con Odoo")
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    print(f"✅ Conectado a Odoo como UID: {uid}")
    return uid, models

def obtener_cuentas_efectivo(uid, models):
    """Obtiene todas las cuentas de tipo efectivo (asset_cash)."""
    print("\n" + "="*60)
    print("📊 PASO 1: IDENTIFICAR CUENTAS DE EFECTIVO")
    print("="*60)
    
    # Buscar cuentas tipo asset_cash
    cuentas_cash = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'account.account', 'search_read',
        [[('account_type', '=', 'asset_cash')]],
        {'fields': ['id', 'code', 'name', 'account_type'], 'limit': 100}
    )
    
    print(f"\n🏦 Encontradas {len(cuentas_cash)} cuentas de tipo 'asset_cash':\n")
    
    total_ids = []
    for cuenta in sorted(cuentas_cash, key=lambda x: x['code']):
        print(f"  [{cuenta['id']:4d}] {cuenta['code']:15s} | {cuenta['name']}")
        total_ids.append(cuenta['id'])
    
    return cuentas_cash, total_ids

def obtener_saldo_inicial(uid, models, cuenta_ids, fecha_inicio):
    """Calcula el saldo inicial de las cuentas de efectivo."""
    print("\n" + "="*60)
    print("💰 PASO 2: CALCULAR SALDO INICIAL DE EFECTIVO")
    print(f"   (Todos los movimientos ANTES de {fecha_inicio})")
    print("="*60)
    
    # Obtener todos los movimientos ANTES de la fecha de inicio
    domain = [
        ('account_id', 'in', cuenta_ids),
        ('date', '<', fecha_inicio),
        ('parent_state', '=', 'posted')
    ]
    
    movimientos = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'account.move.line', 'search_read',
        [domain],
        {'fields': ['account_id', 'debit', 'credit', 'balance', 'date'], 'limit': 50000}
    )
    
    saldo_por_cuenta = defaultdict(float)
    for mov in movimientos:
        cuenta_id = mov['account_id'][0] if mov['account_id'] else None
        if cuenta_id:
            saldo_por_cuenta[cuenta_id] += mov.get('balance', mov['debit'] - mov['credit'])
    
    saldo_total = sum(saldo_por_cuenta.values())
    
    print(f"\n📈 Movimientos encontrados antes de {fecha_inicio}: {len(movimientos)}")
    print(f"\n💵 SALDO INICIAL TOTAL: ${saldo_total:,.0f}\n")
    
    # Detalle por cuenta
    print("   Detalle por cuenta:")
    for cuenta_id, saldo in sorted(saldo_por_cuenta.items(), key=lambda x: -abs(x[1])):
        print(f"     Cuenta {cuenta_id}: ${saldo:,.0f}")
    
    return saldo_total, saldo_por_cuenta

def obtener_movimientos_periodo(uid, models, cuenta_ids, fecha_inicio, fecha_fin):
    """Obtiene todos los movimientos del período para cuentas de efectivo."""
    print("\n" + "="*60)
    print(f"📊 PASO 3: MOVIMIENTOS DEL PERÍODO ({fecha_inicio} a {fecha_fin})")
    print("="*60)
    
    domain = [
        ('account_id', 'in', cuenta_ids),
        ('date', '>=', fecha_inicio),
        ('date', '<=', fecha_fin),
        ('parent_state', '=', 'posted')
    ]
    
    movimientos = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'account.move.line', 'search_read',
        [domain],
        {'fields': ['id', 'account_id', 'name', 'ref', 'debit', 'credit', 'balance', 'date', 'move_id', 'partner_id'], 'limit': 5000}
    )
    
    print(f"\n📈 Total movimientos en período: {len(movimientos)}")
    
    # Agrupar por fecha
    por_fecha = defaultdict(list)
    total_debitos = 0
    total_creditos = 0
    
    for mov in movimientos:
        fecha = mov['date']
        por_fecha[fecha].append(mov)
        total_debitos += mov['debit']
        total_creditos += mov['credit']
    
    variacion = total_debitos - total_creditos
    
    print(f"\n💹 RESUMEN DEL PERÍODO:")
    print(f"   - Total Débitos (entradas):  ${total_debitos:,.0f}")
    print(f"   - Total Créditos (salidas):  ${total_creditos:,.0f}")
    print(f"   - Variación Neta:            ${variacion:,.0f}")
    
    print(f"\n📅 Movimientos por día:")
    for fecha in sorted(por_fecha.keys()):
        movs = por_fecha[fecha]
        sum_deb = sum(m['debit'] for m in movs)
        sum_cred = sum(m['credit'] for m in movs)
        print(f"   {fecha}: {len(movs):3d} movs | Déb: ${sum_deb:>12,.0f} | Créd: ${sum_cred:>12,.0f} | Neto: ${sum_deb-sum_cred:>12,.0f}")
    
    return movimientos, variacion

def verificar_contrapartidas(uid, models, movimientos_efectivo):
    """Analiza las contrapartidas de los movimientos de efectivo para clasificar por actividad."""
    print("\n" + "="*60)
    print("🔍 PASO 4: ANÁLISIS DE CONTRAPARTIDAS (CLASIFICACIÓN IAS 7)")
    print("="*60)
    
    # Obtener los move_ids únicos
    move_ids = list(set(mov['move_id'][0] for mov in movimientos_efectivo if mov['move_id']))
    
    print(f"\n📄 Asientos contables únicos: {len(move_ids)}")
    
    # Para cada asiento, obtener TODAS las líneas (no solo las de efectivo)
    todas_lineas = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'account.move.line', 'search_read',
        [[('move_id', 'in', move_ids)]],
        {'fields': ['id', 'move_id', 'account_id', 'name', 'debit', 'credit', 'balance', 'date'], 'limit': 50000}
    )
    
    # Agrupar por move_id
    lineas_por_asiento = defaultdict(list)
    for linea in todas_lineas:
        lineas_por_asiento[linea['move_id'][0]].append(linea)
    
    # Clasificar movimientos por prefijo de cuenta contrapartida
    clasificacion = {
        'OPERACION': {'cobros': 0, 'pagos_prov': 0, 'pagos_emp': 0, 'otros': 0},
        'INVERSION': {'compra_activos': 0, 'venta_activos': 0},
        'FINANCIAMIENTO': {'prestamos': 0, 'capital': 0}
    }
    
    # Obtener info de cuentas para clasificar
    cuenta_ids_all = list(set(l['account_id'][0] for l in todas_lineas if l['account_id']))
    cuentas_info = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'account.account', 'search_read',
        [[('id', 'in', cuenta_ids_all)]],
        {'fields': ['id', 'code', 'name', 'account_type']}
    )
    cuentas_map = {c['id']: c for c in cuentas_info}
    
    # Mostrar algunos ejemplos de asientos para debug
    print("\n📝 Ejemplos de asientos (primeros 10):")
    for move_id in list(move_ids)[:10]:
        lineas = lineas_por_asiento[move_id]
        print(f"\n  Asiento #{move_id} ({lineas[0]['date']}):")
        for l in lineas:
            cuenta = cuentas_map.get(l['account_id'][0], {})
            codigo = cuenta.get('code', '?')
            tipo = cuenta.get('account_type', '?')
            print(f"    [{codigo:10s}] D:{l['debit']:>12,.0f} C:{l['credit']:>12,.0f} | {l['name'][:40]} ({tipo})")
    
    # Estadísticas por tipo de cuenta
    print("\n📊 Estadísticas por tipo de cuenta en contrapartidas:")
    tipos_stats = defaultdict(lambda: {'count': 0, 'debit': 0, 'credit': 0})
    
    for linea in todas_lineas:
        cuenta = cuentas_map.get(linea['account_id'][0], {})
        tipo = cuenta.get('account_type', 'unknown')
        tipos_stats[tipo]['count'] += 1
        tipos_stats[tipo]['debit'] += linea['debit']
        tipos_stats[tipo]['credit'] += linea['credit']
    
    for tipo, stats in sorted(tipos_stats.items(), key=lambda x: -x[1]['count']):
        print(f"  {tipo:30s}: {stats['count']:5d} líneas | Déb: ${stats['debit']:>15,.0f} | Créd: ${stats['credit']:>15,.0f}")
    
    return lineas_por_asiento, cuentas_map

def comparar_con_api(fecha_inicio, fecha_fin):
    """Compara los resultados con la API del dashboard."""
    print("\n" + "="*60)
    print("🔄 PASO 5: COMPARAR CON RESPUESTA DE API DEL DASHBOARD")
    print("="*60)
    
    import requests
    
    url = "http://167.114.114.51:8001/api/v1/flujo-caja/mensual"
    params = {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "username": ODOO_USER,
        "password": ODOO_PASSWORD
    }
    
    try:
        resp = requests.get(url, params=params, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            
            print("\n✅ API respondió correctamente")
            
            conciliacion = data.get('conciliacion', {})
            actividades = data.get('actividades', {})
            
            print(f"\n📊 DATOS DEL FLUJO DE CAJA (API):")
            print(f"   Efectivo Inicial:  ${conciliacion.get('efectivo_inicial', 0):>15,.0f}")
            print(f"   Efectivo Final:    ${conciliacion.get('efectivo_final', 0):>15,.0f}")
            
            for act_key in ['OPERACION', 'INVERSION', 'FINANCIAMIENTO']:
                act_data = actividades.get(act_key, {})
                subtotal = act_data.get('subtotal', 0)
                print(f"   {act_key:15s}:    ${subtotal:>15,.0f}")
            
            variacion = sum(actividades.get(k, {}).get('subtotal', 0) for k in ['OPERACION', 'INVERSION', 'FINANCIAMIENTO'])
            print(f"   VARIACIÓN TOTAL:   ${variacion:>15,.0f}")
            
            # Mostrar cuentas sin clasificar
            cuentas_nc = data.get('cuentas_sin_clasificar', [])
            if cuentas_nc:
                print(f"\n⚠️ Cuentas SIN CLASIFICAR: {len(cuentas_nc)}")
                total_nc = sum(c.get('monto', 0) for c in cuentas_nc)
                print(f"   Monto total sin clasificar: ${total_nc:,.0f}")
                print("\n   Top 10 por monto:")
                for c in sorted(cuentas_nc, key=lambda x: -abs(x.get('monto', 0)))[:10]:
                    print(f"     {c.get('codigo', ''):10s} | ${c.get('monto', 0):>12,.0f} | {c.get('nombre', '')[:40]}")
            
            return data
        else:
            print(f"❌ Error API: {resp.status_code}")
            print(resp.text[:500])
            return None
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None

def main():
    print("="*70)
    print("🔍 VERIFICACIÓN EXHAUSTIVA DEL FLUJO DE EFECTIVO - RIO FUTURO")
    print("="*70)
    print(f"📅 Período: {FECHA_INICIO} a {FECHA_FIN}")
    print(f"🌐 Odoo: {ODOO_URL}")
    print(f"👤 Usuario: {ODOO_USER}")
    
    # Conectar
    uid, models = conectar_odoo()
    
    # Paso 1: Identificar cuentas de efectivo
    cuentas_cash, cuenta_ids = obtener_cuentas_efectivo(uid, models)
    
    # Paso 2: Calcular saldo inicial
    saldo_inicial, saldo_por_cuenta = obtener_saldo_inicial(uid, models, cuenta_ids, FECHA_INICIO)
    
    # Paso 3: Obtener movimientos del período
    movimientos, variacion_directa = obtener_movimientos_periodo(uid, models, cuenta_ids, FECHA_INICIO, FECHA_FIN)
    
    # Paso 4: Analizar contrapartidas
    if movimientos:
        lineas_asiento, cuentas_map = verificar_contrapartidas(uid, models, movimientos)
    
    # Paso 5: Comparar con API
    api_data = comparar_con_api(FECHA_INICIO, FECHA_FIN)
    
    # RESUMEN FINAL
    print("\n" + "="*70)
    print("📋 RESUMEN DE VERIFICACIÓN")
    print("="*70)
    
    saldo_final_calculado = saldo_inicial + variacion_directa
    
    print(f"\n🔢 CÁLCULO DIRECTO DESDE ODOO:")
    print(f"   Saldo Inicial (antes de {FECHA_INICIO}):  ${saldo_inicial:>15,.0f}")
    print(f"   (+) Variación del período:                ${variacion_directa:>15,.0f}")
    print(f"   (=) Saldo Final calculado:                ${saldo_final_calculado:>15,.0f}")
    
    if api_data:
        conciliacion = api_data.get('conciliacion', {})
        ef_ini_api = conciliacion.get('efectivo_inicial', 0)
        ef_fin_api = conciliacion.get('efectivo_final', 0)
        
        print(f"\n🌐 DATOS DE LA API:")
        print(f"   Efectivo Inicial:                         ${ef_ini_api:>15,.0f}")
        print(f"   Efectivo Final:                           ${ef_fin_api:>15,.0f}")
        
        diff_ini = abs(saldo_inicial - ef_ini_api)
        diff_fin = abs(saldo_final_calculado - ef_fin_api)
        
        print(f"\n⚖️ DIFERENCIAS:")
        print(f"   Diferencia en Saldo Inicial:              ${diff_ini:>15,.0f} {'✅' if diff_ini < 100 else '⚠️'}")
        print(f"   Diferencia en Saldo Final:                ${diff_fin:>15,.0f} {'✅' if diff_fin < 100 else '⚠️'}")
    
    print("\n" + "="*70)
    print("✅ VERIFICACIÓN COMPLETADA")
    print("="*70)


if __name__ == "__main__":
    main()
