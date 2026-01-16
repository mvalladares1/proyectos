"""
DEBUG FORENSE - Análisis Completo de Contabilidad para Flujo de Caja
=====================================================================

Este script hace un análisis exhaustivo de la contabilidad en Odoo para:
1. Identificar TODAS las cuentas contables
2. Analizar su estructura y jerarquía
3. Identificar cuentas de efectivo y bancos
4. Revisar movimientos reales
5. Generar mapeo correcto para flujo de caja IAS 7
"""

import sys
import os
import json
from datetime import datetime, timedelta
from collections import defaultdict

# Agregar path para importar OdooClient
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient


def print_section(title):
    """Imprime un separador de sección."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def analizar_cuentas_contables(odoo):
    """Analiza TODAS las cuentas contables del sistema."""
    print_section("1. ANÁLISIS DE CUENTAS CONTABLES")
    
    # Obtener TODAS las cuentas
    print("📊 Buscando todas las cuentas contables...")
    cuentas_ids = odoo.search('account.account', [], limit=None, order='code asc')
    
    print(f"✅ Se encontraron {len(cuentas_ids)} cuentas contables\n")
    
    # Leer campos importantes
    cuentas = odoo.read('account.account', cuentas_ids, [
        'code', 'name', 'account_type', 'reconcile', 'deprecated'
    ])
    
    # Agrupar por prefijos
    cuentas_por_prefijo = defaultdict(list)
    cuentas_por_tipo = defaultdict(list)
    
    for cuenta in cuentas:
        code = cuenta.get('code', '')
        tipo = cuenta.get('account_type', 'N/A')
        
        # Agrupar por primer dígito
        if code:
            prefijo = code[0]
            cuentas_por_prefijo[prefijo].append(cuenta)
            cuentas_por_tipo[tipo].append(cuenta)
    
    # Mostrar estructura por nivel 1
    print("📁 ESTRUCTURA DEL PLAN DE CUENTAS (Nivel 1):")
    print("-" * 80)
    for prefijo in sorted(cuentas_por_prefijo.keys()):
        cuentas_grupo = cuentas_por_prefijo[prefijo]
        print(f"\n{prefijo}XX - {len(cuentas_grupo)} cuentas")
        # Mostrar primeras 5 de cada grupo
        for c in cuentas_grupo[:5]:
            print(f"  {c['code']:12} | {c['name'][:50]:50} | {c.get('account_type', 'N/A')}")
        if len(cuentas_grupo) > 5:
            print(f"  ... y {len(cuentas_grupo) - 5} cuentas más")
    
    # Mostrar tipos de cuenta
    print("\n\n📊 TIPOS DE CUENTA EN EL SISTEMA:")
    print("-" * 80)
    for tipo, cuentas_tipo in sorted(cuentas_por_tipo.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"{tipo:40} | {len(cuentas_tipo):4} cuentas")
    
    return cuentas


def identificar_cuentas_efectivo(cuentas):
    """Identifica cuentas que son de efectivo y equivalentes."""
    print_section("2. IDENTIFICACIÓN DE CUENTAS DE EFECTIVO")
    
    # Palabras clave que indican efectivo
    keywords_efectivo = [
        'caja', 'banco', 'efectivo', 'cash', 'bank',
        'cuenta corriente', 'vista', 'ahorro'
    ]
    
    posibles_efectivo = []
    
    for cuenta in cuentas:
        code = cuenta.get('code', '')
        name = cuenta.get('name', '').lower()
        tipo = cuenta.get('account_type', '')
        
        # Criterios de identificación
        es_prefijo_11 = code.startswith('11')  # Típicamente efectivo en Chile
        tiene_keyword = any(kw in name for kw in keywords_efectivo)
        es_tipo_liquidity = 'liquidity' in tipo.lower() if tipo else False
        
        if es_prefijo_11 or tiene_keyword or es_tipo_liquidity:
            posibles_efectivo.append({
                'code': code,
                'name': cuenta['name'],
                'tipo': tipo,
                'criterio': 'prefijo_11' if es_prefijo_11 else ('keyword' if tiene_keyword else 'tipo_liquidity')
            })
    
    print(f"🔍 Se identificaron {len(posibles_efectivo)} posibles cuentas de efectivo:\n")
    print(f"{'Código':12} | {'Nombre':50} | {'Tipo':30} | Criterio")
    print("-" * 120)
    
    for c in posibles_efectivo:
        print(f"{c['code']:12} | {c['name'][:50]:50} | {c['tipo'][:30]:30} | {c['criterio']}")
    
    return posibles_efectivo


def analizar_movimientos_recientes(odoo, cuentas_efectivo):
    """Analiza movimientos contables recientes en cuentas de efectivo."""
    print_section("3. ANÁLISIS DE MOVIMIENTOS EN CUENTAS DE EFECTIVO")
    
    # Fecha: últimos 30 días
    fecha_fin = datetime.now()
    fecha_inicio = fecha_fin - timedelta(days=30)
    
    print(f"📅 Analizando movimientos desde {fecha_inicio.date()} hasta {fecha_fin.date()}\n")
    
    # Obtener códigos de cuentas de efectivo
    codigos_efectivo = [c['code'] for c in cuentas_efectivo]
    
    # Buscar movimientos
    domain = [
        ('date', '>=', fecha_inicio.strftime('%Y-%m-%d')),
        ('date', '<=', fecha_fin.strftime('%Y-%m-%d')),
        ('account_id.code', 'in', codigos_efectivo)
    ]
    
    print("🔍 Buscando movimientos...")
    movimientos_ids = odoo.search('account.move.line', domain, limit=100)
    
    if not movimientos_ids:
        print("⚠️  No se encontraron movimientos en cuentas de efectivo en los últimos 30 días")
        return []
    
    movimientos = odoo.read('account.move.line', movimientos_ids, [
        'date', 'name', 'account_id', 'debit', 'credit', 'balance', 'move_id', 'partner_id'
    ])
    
    print(f"✅ Se encontraron {len(movimientos)} movimientos\n")
    
    # Mostrar muestra
    print("📋 MUESTRA DE MOVIMIENTOS (primeros 10):")
    print("-" * 120)
    print(f"{'Fecha':12} | {'Cuenta':25} | {'Descripción':40} | {'Débito':15} | {'Crédito':15}")
    print("-" * 120)
    
    for mov in movimientos[:10]:
        cuenta_info = mov.get('account_id', [False, 'N/A'])
        cuenta_nombre = cuenta_info[1] if isinstance(cuenta_info, list) else 'N/A'
        fecha = mov.get('date', 'N/A')
        desc = mov.get('name', 'Sin descripción')[:40]
        debito = mov.get('debit', 0)
        credito = mov.get('credit', 0)
        
        print(f"{fecha:12} | {cuenta_nombre[:25]:25} | {desc:40} | ${debito:13,.0f} | ${credito:13,.0f}")
    
    # Resumen por cuenta
    print("\n\n💰 RESUMEN POR CUENTA DE EFECTIVO:")
    print("-" * 80)
    
    resumen_por_cuenta = defaultdict(lambda: {'debito': 0, 'credito': 0, 'count': 0})
    
    for mov in movimientos:
        cuenta_info = mov.get('account_id', [False, 'N/A'])
        cuenta_nombre = cuenta_info[1] if isinstance(cuenta_info, list) else 'N/A'
        resumen_por_cuenta[cuenta_nombre]['debito'] += mov.get('debit', 0)
        resumen_por_cuenta[cuenta_nombre]['credito'] += mov.get('credit', 0)
        resumen_por_cuenta[cuenta_nombre]['count'] += 1
    
    print(f"{'Cuenta':40} | {'# Movs':8} | {'Total Débito':15} | {'Total Crédito':15}")
    print("-" * 80)
    
    for cuenta, datos in sorted(resumen_por_cuenta.items()):
        print(f"{cuenta[:40]:40} | {datos['count']:8} | ${datos['debito']:13,.0f} | ${datos['credito']:13,.0f}")
    
    return movimientos


def analizar_estructura_contable_completa(odoo):
    """Analiza la estructura contable completa para mapeo IAS 7."""
    print_section("4. ANÁLISIS PARA MAPEO IAS 7")
    
    print("📊 Analizando cuentas por categorías IAS 7...\n")
    
    # Obtener todas las cuentas
    cuentas_ids = odoo.search('account.account', [], limit=None, order='code asc')
    cuentas = odoo.read('account.account', cuentas_ids, ['code', 'name', 'account_type'])
    
    # Categorías IAS 7
    categorias = {
        '4XX - INGRESOS': [],
        '5XX - COSTOS Y GASTOS': [],
        '2XX - PASIVOS': [],
        '1XX - ACTIVOS': [],
        '3XX - PATRIMONIO': [],
    }
    
    for cuenta in cuentas:
        code = cuenta.get('code', '')
        if not code:
            continue
            
        primer_digito = code[0]
        
        if primer_digito == '4':
            categorias['4XX - INGRESOS'].append(cuenta)
        elif primer_digito == '5':
            categorias['5XX - COSTOS Y GASTOS'].append(cuenta)
        elif primer_digito == '2':
            categorias['2XX - PASIVOS'].append(cuenta)
        elif primer_digito == '1':
            categorias['1XX - ACTIVOS'].append(cuenta)
        elif primer_digito == '3':
            categorias['3XX - PATRIMONIO'].append(cuenta)
    
    # Mostrar estructura
    for categoria, cuentas_cat in categorias.items():
        print(f"\n{categoria} ({len(cuentas_cat)} cuentas):")
        print("-" * 80)
        
        # Agrupar por subcategorías (2 primeros dígitos)
        subcategorias = defaultdict(list)
        for c in cuentas_cat:
            code = c.get('code', '')
            if len(code) >= 2:
                prefijo = code[:2]
                subcategorias[prefijo].append(c)
        
        for prefijo in sorted(subcategorias.keys()):
            cuentas_sub = subcategorias[prefijo]
            print(f"\n  {prefijo}X - {len(cuentas_sub)} cuentas:")
            for c in cuentas_sub[:3]:
                print(f"    {c['code']:12} | {c['name'][:60]}")
            if len(cuentas_sub) > 3:
                print(f"    ... y {len(cuentas_sub) - 3} más")
    
    return categorias


def generar_mapeo_sugerido(cuentas_efectivo, categorias):
    """Genera un mapeo sugerido basado en el análisis."""
    print_section("5. MAPEO SUGERIDO PARA FLUJO DE CAJA")
    
    mapeo = {
        "cuentas_efectivo": {
            "prefijos": [],
            "codigos_especificos": [],
            "descripcion": "Cuentas de efectivo y equivalentes al efectivo"
        },
        "mapeo_lineas": {}
    }
    
    # Extraer prefijos de cuentas de efectivo
    prefijos_efectivo = set()
    codigos_especificos = []
    
    for c in cuentas_efectivo:
        code = c['code']
        # Si tiene 4 dígitos, usar como prefijo de 2 dígitos
        if len(code) >= 2:
            prefijos_efectivo.add(code[:2])
        # Guardar código completo también
        codigos_especificos.append(code)
    
    mapeo['cuentas_efectivo']['prefijos'] = sorted(list(prefijos_efectivo))
    mapeo['cuentas_efectivo']['codigos_especificos'] = sorted(codigos_especificos)
    
    print("💵 CUENTAS DE EFECTIVO IDENTIFICADAS:")
    print(f"  Prefijos: {mapeo['cuentas_efectivo']['prefijos']}")
    print(f"  Códigos específicos: {len(codigos_especificos)} cuentas")
    print()
    
    # Mapeo IAS 7 sugerido
    print("📋 MAPEO IAS 7 SUGERIDO:\n")
    
    mapeo['mapeo_lineas'] = {
        "OP01": {
            "prefijos": ["41", "42"],  # Ingresos por ventas
            "descripcion": "Cobros procedentes de las ventas de bienes y prestación de servicios"
        },
        "OP02": {
            "prefijos": ["51", "52", "21"],  # Costos y proveedores
            "descripcion": "Pagos a proveedores por el suministro de bienes y servicios"
        },
        "OP03": {
            "prefijos": ["62", "63", "64"],  # Gastos de personal
            "descripcion": "Pagos a y por cuenta de los empleados"
        },
        "OP04": {
            "prefijos": ["65"],  # Gastos financieros
            "descripcion": "Intereses pagados"
        },
        "OP05": {
            "prefijos": ["47", "77"],  # Ingresos financieros
            "descripcion": "Intereses recibidos"
        },
        "OP06": {
            "prefijos": ["67", "40"],  # Impuestos
            "descripcion": "Impuestos a las ganancias pagados"
        },
        "IN01": {
            "prefijos": ["13"],  # Inversiones
            "descripcion": "Pagos por adquisición de inversiones"
        },
        "IN02": {
            "prefijos": ["14", "15", "16", "17"],  # Activos fijos
            "descripcion": "Compras de propiedades, planta y equipo"
        },
        "FI01": {
            "prefijos": ["25"],  # Préstamos largo plazo
            "descripcion": "Obtención de préstamos"
        },
        "FI02": {
            "prefijos": ["25"],  # Amortización préstamos
            "descripcion": "Reembolsos de préstamos"
        },
        "FI03": {
            "prefijos": ["31"],  # Capital
            "descripcion": "Aportes de capital"
        },
        "FI04": {
            "prefijos": ["33"],  # Dividendos
            "descripcion": "Dividendos pagados"
        }
    }
    
    for codigo, config in mapeo['mapeo_lineas'].items():
        print(f"{codigo}: {config['descripcion']}")
        print(f"  → Prefijos: {config['prefijos']}")
        print()
    
    return mapeo


def guardar_mapeo(mapeo, filename='mapeo_flujo_caja_generado.json'):
    """Guarda el mapeo en un archivo JSON."""
    print_section("6. GUARDANDO MAPEO GENERADO")
    
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'backend', 'data', filename
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mapeo, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Mapeo guardado en: {output_path}")
    print(f"📝 Archivo: {filename}")
    
    return output_path


def main():
    """Ejecuta el análisis forense completo."""
    print("\n" + "=" * 80)
    print("  DEBUG FORENSE - ANALISIS DE CONTABILIDAD PARA FLUJO DE CAJA")
    print("=" * 80)
    
    # Credenciales
    username = "mvalladares@riofuturo.cl"
    password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"
    
    print(f"\n📡 Conectando a Odoo...")
    print(f"   Usuario: {username}")
    
    try:
        # Conectar a Odoo
        odoo = OdooClient(username=username, password=password)
        print("✅ Conexión exitosa\n")
        
        # 1. Analizar todas las cuentas
        cuentas = analizar_cuentas_contables(odoo)
        
        # 2. Identificar cuentas de efectivo
        cuentas_efectivo = identificar_cuentas_efectivo(cuentas)
        
        # 3. Analizar movimientos
        movimientos = analizar_movimientos_recientes(odoo, cuentas_efectivo)
        
        # 4. Analizar estructura completa
        categorias = analizar_estructura_contable_completa(odoo)
        
        # 5. Generar mapeo sugerido
        mapeo = generar_mapeo_sugerido(cuentas_efectivo, categorias)
        
        # 6. Guardar mapeo
        archivo_guardado = guardar_mapeo(mapeo)
        
        print_section("✅ ANÁLISIS COMPLETO FINALIZADO")
        
        print("📊 RESUMEN:")
        print(f"  • Total cuentas analizadas: {len(cuentas)}")
        print(f"  • Cuentas de efectivo identificadas: {len(cuentas_efectivo)}")
        print(f"  • Movimientos analizados: {len(movimientos) if movimientos else 0}")
        print(f"  • Mapeo generado: {archivo_guardado}")
        print()
        print("🎯 PRÓXIMOS PASOS:")
        print("  1. Revisa el archivo generado: mapeo_flujo_caja_generado.json")
        print("  2. Valida que las cuentas de efectivo sean correctas")
        print("  3. Ajusta los prefijos de las categorías IAS 7 según necesites")
        print("  4. Reemplaza el archivo mapeo_flujo_caja.json con el generado")
        print("  5. Reinicia la API para aplicar cambios")
        print()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
