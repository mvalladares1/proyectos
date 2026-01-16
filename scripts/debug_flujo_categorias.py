"""
Script de Verificación Profunda por Categoría IAS 7
====================================================
Analiza cada categoría del flujo de caja y verifica
que los montos estén correctamente clasificados.

Ejecutar: python scripts/debug_flujo_categorias.py
"""
import xmlrpc.client
import json
from datetime import datetime
from collections import defaultdict

# === CONFIGURACIÓN ===
ODOO_URL = "https://riofuturo.server98c6e.oerpondemand.net"
ODOO_DB = "riofuturo-master"
ODOO_USER = "mvalladares@riofuturo.cl"
ODOO_PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Período a verificar
FECHA_INICIO = "2026-01-01"
FECHA_FIN = "2026-01-31"

# Mapeo de prefijos de cuentas a categorías IAS 7
MAPEO_IAS7 = {
    # OPERACIÓN
    "41": ("OPERACION", "OP01 - Cobros por ventas"),
    "42": ("OPERACION", "OP05 - Intereses recibidos"),
    "51": ("OPERACION", "OP02 - Pagos a proveedores"),
    "52": ("OPERACION", "OP02 - Pagos a proveedores"),
    "53": ("OPERACION", "OP02 - Pagos a proveedores"),
    "61": ("OPERACION", "OP03 - Pagos a empleados"),
    "62": ("OPERACION", "OP03 - Pagos a empleados"),
    "63": ("OPERACION", "OP07 - Otros gastos op."),
    "64": ("OPERACION", "OP07 - Otros gastos op."),
    "65": ("OPERACION", "OP04 - Intereses pagados"),
    "66": ("OPERACION", "OP07 - Otros gastos op."),
    "67": ("OPERACION", "OP07 - Otros gastos op."),
    "68": ("OPERACION", "OP07 - Otros gastos op."),
    "69": ("OPERACION", "OP07 - Otros gastos op."),
    "77": ("OPERACION", "OP05 - Intereses recibidos"),
    "91": ("OPERACION", "OP06 - Impuestos"),
    # INVERSIÓN
    "12": ("INVERSION", "IN02 - Activos fijos"),
    "13": ("INVERSION", "IN01 - Inversiones"),
    "71": ("INVERSION", "IN03 - Venta activos"),
    "81": ("INVERSION", "IN04 - Costo venta activos"),
    # FINANCIAMIENTO
    "21": ("FINANCIAMIENTO", "FI01 - Préstamos CP"),
    "22": ("FINANCIAMIENTO", "FI02 - Préstamos LP"),
    "31": ("FINANCIAMIENTO", "FI03 - Capital"),
    "32": ("FINANCIAMIENTO", "FI04 - Distribuciones"),
}


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
    """Obtiene IDs de cuentas de efectivo."""
    cuentas_cash = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'account.account', 'search_read',
        [[('account_type', '=', 'asset_cash')]],
        {'fields': ['id', 'code', 'name'], 'limit': 100}
    )
    return [c['id'] for c in cuentas_cash], cuentas_cash


def clasificar_cuenta(codigo):
    """Clasifica una cuenta según su prefijo."""
    for prefijo, (actividad, concepto) in MAPEO_IAS7.items():
        if codigo.startswith(prefijo):
            return actividad, concepto
    return "SIN_CLASIFICAR", "NC - No clasificada"


def analizar_contrapartidas(uid, models, cuenta_ids_efectivo, fecha_inicio, fecha_fin):
    """Analiza las contrapartidas de movimientos de efectivo."""
    print("\n" + "="*70)
    print("📊 ANÁLISIS DE CONTRAPARTIDAS POR CATEGORÍA IAS 7")
    print("="*70)
    
    # Obtener movimientos de efectivo del período
    domain = [
        ('account_id', 'in', cuenta_ids_efectivo),
        ('date', '>=', fecha_inicio),
        ('date', '<=', fecha_fin),
        ('parent_state', '=', 'posted')
    ]
    
    movimientos_efectivo = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'account.move.line', 'search_read',
        [domain],
        {'fields': ['id', 'move_id', 'debit', 'credit', 'balance'], 'limit': 10000}
    )
    
    print(f"\n📈 Movimientos de efectivo encontrados: {len(movimientos_efectivo)}")
    
    # Obtener IDs de asientos
    move_ids = list(set(m['move_id'][0] for m in movimientos_efectivo if m['move_id']))
    print(f"📄 Asientos contables únicos: {len(move_ids)}")
    
    # Obtener TODAS las líneas de esos asientos
    todas_lineas = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'account.move.line', 'search_read',
        [[('move_id', 'in', move_ids)]],
        {'fields': ['id', 'move_id', 'account_id', 'debit', 'credit', 'balance', 'name'], 'limit': 50000}
    )
    
    # Obtener info de cuentas
    cuenta_ids_all = list(set(l['account_id'][0] for l in todas_lineas if l['account_id']))
    cuentas_info = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'account.account', 'search_read',
        [[('id', 'in', cuenta_ids_all)]],
        {'fields': ['id', 'code', 'name', 'account_type']}
    )
    cuentas_map = {c['id']: c for c in cuentas_info}
    
    # Agrupar líneas por asiento
    lineas_por_asiento = defaultdict(list)
    for linea in todas_lineas:
        lineas_por_asiento[linea['move_id'][0]].append(linea)
    
    # Clasificar cada asiento según contrapartida principal
    clasificacion = defaultdict(lambda: {'monto': 0, 'count': 0, 'ejemplos': []})
    sin_clasificar = []
    
    for move_id, lineas in lineas_por_asiento.items():
        # Separar líneas de efectivo vs contrapartidas
        lineas_efectivo = []
        contrapartidas = []
        
        for linea in lineas:
            cuenta = cuentas_map.get(linea['account_id'][0], {})
            if cuenta.get('account_type') == 'asset_cash':
                lineas_efectivo.append(linea)
            else:
                contrapartidas.append((linea, cuenta))
        
        # El monto del flujo es la suma de las líneas de efectivo
        monto_flujo = sum(l['debit'] - l['credit'] for l in lineas_efectivo)
        
        # Clasificar por la contrapartida principal (la de mayor monto absoluto)
        if contrapartidas:
            contrapartidas_sorted = sorted(contrapartidas, key=lambda x: -abs(x[0]['debit'] - x[0]['credit']))
            principal = contrapartidas_sorted[0]
            cuenta_principal = principal[1]
            codigo = cuenta_principal.get('code', '')
            
            actividad, concepto = clasificar_cuenta(codigo)
            
            clasificacion[concepto]['monto'] += monto_flujo
            clasificacion[concepto]['count'] += 1
            if len(clasificacion[concepto]['ejemplos']) < 3:
                clasificacion[concepto]['ejemplos'].append({
                    'move_id': move_id,
                    'monto': monto_flujo,
                    'cuenta': f"{codigo} - {cuenta_principal.get('name', '')[:30]}"
                })
            
            if actividad == "SIN_CLASIFICAR":
                sin_clasificar.append({
                    'move_id': move_id,
                    'monto': monto_flujo,
                    'cuenta_codigo': codigo,
                    'cuenta_nombre': cuenta_principal.get('name', ''),
                    'descripcion': principal[0].get('name', '')[:50]
                })
    
    # Mostrar resultados por actividad
    print("\n" + "="*70)
    print("📋 RESUMEN POR CONCEPTO IAS 7")
    print("="*70)
    
    # Agrupar por actividad
    por_actividad = {'OPERACION': [], 'INVERSION': [], 'FINANCIAMIENTO': [], 'SIN_CLASIFICAR': []}
    for concepto, data in sorted(clasificacion.items()):
        for actividad_key in ['OPERACION', 'INVERSION', 'FINANCIAMIENTO']:
            if actividad_key[:2] in concepto[:2].upper():
                por_actividad[actividad_key].append((concepto, data))
                break
        else:
            por_actividad['SIN_CLASIFICAR'].append((concepto, data))
    
    for actividad in ['OPERACION', 'INVERSION', 'FINANCIAMIENTO', 'SIN_CLASIFICAR']:
        conceptos = por_actividad[actividad]
        if not conceptos:
            continue
        
        total_actividad = sum(d['monto'] for _, d in conceptos)
        
        print(f"\n{'🟢' if actividad == 'OPERACION' else '🔵' if actividad == 'INVERSION' else '🟣' if actividad == 'FINANCIAMIENTO' else '⚠️'} {actividad}")
        print(f"   {'─'*50}")
        
        for concepto, data in sorted(conceptos, key=lambda x: -abs(x[1]['monto'])):
            print(f"   {concepto:35s} | ${data['monto']:>15,.0f} | ({data['count']} asientos)")
            for ej in data['ejemplos'][:1]:
                print(f"      └─ Ej: {ej['cuenta'][:40]}")
        
        print(f"   {'─'*50}")
        print(f"   {'SUBTOTAL':35s} | ${total_actividad:>15,.0f}")
    
    # Detalle de sin clasificar
    if sin_clasificar:
        print("\n" + "="*70)
        print(f"⚠️ MOVIMIENTOS SIN CLASIFICAR ({len(sin_clasificar)} asientos)")
        print("="*70)
        
        # Agrupar por prefijo de cuenta
        por_prefijo = defaultdict(lambda: {'monto': 0, 'count': 0, 'ejemplos': []})
        for mov in sin_clasificar:
            prefijo = mov['cuenta_codigo'][:2] if mov['cuenta_codigo'] else '??'
            por_prefijo[prefijo]['monto'] += mov['monto']
            por_prefijo[prefijo]['count'] += 1
            if len(por_prefijo[prefijo]['ejemplos']) < 2:
                por_prefijo[prefijo]['ejemplos'].append(mov)
        
        print("\nAgrupado por prefijo de cuenta:")
        for prefijo, data in sorted(por_prefijo.items(), key=lambda x: -abs(x[1]['monto'])):
            print(f"\n  Prefijo [{prefijo}]: ${data['monto']:>15,.0f} ({data['count']} asientos)")
            for ej in data['ejemplos']:
                print(f"      └─ {ej['cuenta_codigo']} | {ej['cuenta_nombre'][:40]} | ${ej['monto']:,.0f}")
        
        print("\n💡 RECOMENDACIÓN: Agregar estos prefijos al mapeo IAS 7 en:")
        print("   backend/data/mapeo_flujo_caja.json")
    
    return clasificacion, sin_clasificar


def main():
    print("="*70)
    print("🔍 VERIFICACIÓN PROFUNDA - CATEGORÍAS IAS 7 DEL FLUJO DE CAJA")
    print("="*70)
    print(f"📅 Período: {FECHA_INICIO} a {FECHA_FIN}")
    
    uid, models = conectar_odoo()
    
    cuenta_ids, cuentas_info = obtener_cuentas_efectivo(uid, models)
    print(f"\n🏦 Cuentas de efectivo: {len(cuenta_ids)}")
    
    clasificacion, sin_clasificar = analizar_contrapartidas(uid, models, cuenta_ids, FECHA_INICIO, FECHA_FIN)
    
    # Calcular totales
    total_op = sum(d['monto'] for c, d in clasificacion.items() if c.startswith('OP'))
    total_inv = sum(d['monto'] for c, d in clasificacion.items() if c.startswith('IN'))
    total_fin = sum(d['monto'] for c, d in clasificacion.items() if c.startswith('FI'))
    total_nc = sum(d['monto'] for c, d in clasificacion.items() if c.startswith('NC'))
    
    print("\n" + "="*70)
    print("📊 RESUMEN FINAL")
    print("="*70)
    print(f"   🟢 OPERACIÓN:      ${total_op:>15,.0f}")
    print(f"   🔵 INVERSIÓN:      ${total_inv:>15,.0f}")
    print(f"   🟣 FINANCIAMIENTO: ${total_fin:>15,.0f}")
    print(f"   ⚠️ SIN CLASIFICAR: ${total_nc:>15,.0f}")
    print(f"   {'─'*35}")
    variacion = total_op + total_inv + total_fin + total_nc
    print(f"   VARIACIÓN TOTAL:   ${variacion:>15,.0f}")
    
    print("\n" + "="*70)
    print("✅ ANÁLISIS COMPLETADO")
    print("="*70)


if __name__ == "__main__":
    main()
