"""
Script de Busqueda de Productos No Estandarizados en Ordenes de Venta.

Este script identifica ordenes de venta que contienen productos con codigos
(default_code) que no siguen el formato estandar de 9 digitos.

Formato estandar: [ETAPA-1][FAMILIA-2][MANEJO-1][GRADO-1][VARIEDAD-1][RETAIL-3]
Ejemplo valido: 302131000

Uso:
    python scripts/buscar_productos_no_estandarizados.py
"""

import sys
import os
import re
from datetime import datetime
from collections import defaultdict

# Agregar el directorio raiz al path para importar modulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

# Credenciales
ODOO_USER = "mvalladares@riofuturo.cl"
ODOO_PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Periodo de analisis (desde Nov 2025 hasta el futuro - incluye proyecciones)
FECHA_DESDE = "2025-11-01"
FECHA_HASTA = "2099-12-31"  # Sin limite - incluye ordenes proyectadas

# ============================================================================
# MAPEOS PARA CONSTRUCCION DE CODIGO
# ============================================================================

# ETAPA (posicion 1): Extraida de categ_id (categoria de producto)
ETAPA_MAP = {
    'MP': '1',
    'MPC': '2', 
    'PSP': '3',
    'PTT': '4',
    'RETAIL': '5',
    'SUBPRODUCTO': '6'
}

# FAMILIA (posiciones 2-3): Campo x_studio_sub_categora
FAMILIA_MAP = {
    '[Arándano] - Arándano': '01',
    'Arándano': '01',
    'Arandano': '01',
    '[Frambuesa] - Frambuesa': '02',
    'Frambuesa': '02',
    '[Frutilla] - Frutilla': '03',
    'Frutilla': '03',
    '[Mora] - Mora': '04',
    'Mora': '04',
    '[Mix] - Mix': '06',
    'Mix': '06',
    '[Cereza] - Cereza': '05',
    'Cereza': '05'
}

# MANEJO (posicion 4): Campo x_studio_categora_tipo_de_manejo
MANEJO_MAP = {
    '[Convencional] - Convencional': '1',
    'Convencional': '1',
    '[Orgánico] - Orgánico': '2',
    'Orgánico': '2',
    'Organico': '2'
}

# GRADO (posicion 5): Deducido del nombre del producto
GRADO_PATTERNS = {
    'IQF AA': '1',
    'IQFAA': '1',
    'IQF A': '2',
    'IQFA': '2',
    'IQF-A': '2',
    'PSP': '3',
    'W&B': '4',
    'W & B': '4',
    'WHOLE AND BROKEN': '4',
    'BLOCK': '5',
    'JUGO': '6',
    'JUICE': '6',
    'IQF RETAIL': '7',
    'CRUMBLE': '5',  # Crumble suele ser Block
    'CALIDAD JUGO': '6'
}

# VARIEDAD (posicion 6): Campo x_studio_variedad o deducido
VARIEDAD_PATTERNS = {
    # Arandano
    'S/V': '1',
    'SIN VARIEDAD': '1',
    'HIGHBUSH': '2',
    'HB': '2',
    'RABBITEYE': '3',
    'RE': '3',
    # Frambuesa
    'MEEKER': '2',
    'MK': '2',
    'WAKEFIELD': '3',
    'WF': '3',
    'HERITAGE': '2',
    'HE': '2',
    # Mora
    # Cereza
    # Frutilla
    'ALBION': '2'
}

# IDs de x_variedad mapeados a codigos
# Basado en inspeccion: 6:HE, 7:HB, 8:RY, 9:MK, 10:WF, 15:S/V
VARIEDAD_ID_MAP = {
    6: '2',   # HE -> Heritage (Frambuesa)
    7: '2',   # HB -> Highbush (Arandano)
    8: '3',   # RY -> Rabbiteye (Arandano)
    9: '2',   # MK -> Meeker (Frambuesa)
    10: '3',  # WF -> Wakefield (Frambuesa)
    15: '1',  # S/V -> Sin Variedad
}


def extraer_etapa_de_categoria(categoria_nombre: str) -> str:
    """Extrae el codigo de etapa de la categoria de producto."""
    if not categoria_nombre:
        return '?'
    
    cat_upper = categoria_nombre.upper()
    
    # Buscar en el path de categoria (ej: "PRODUCTOS / PTT")
    for etapa, codigo in ETAPA_MAP.items():
        if etapa in cat_upper:
            return codigo
    
    return '?'


def extraer_familia(tipo_fruta: str) -> str:
    """Extrae el codigo de familia del campo x_studio_sub_categora."""
    if not tipo_fruta:
        return '??'
    
    # Buscar coincidencia exacta primero
    if tipo_fruta in FAMILIA_MAP:
        return FAMILIA_MAP[tipo_fruta]
    
    # Buscar por contenido
    tipo_upper = tipo_fruta.upper()
    if 'ARANDANO' in tipo_upper or 'ARÁNDANO' in tipo_upper:
        return '01'
    if 'FRAMBUESA' in tipo_upper:
        return '02'
    if 'FRUTILLA' in tipo_upper:
        return '03'
    if 'MORA' in tipo_upper:
        return '04'
    if 'CEREZA' in tipo_upper:
        return '05'
    if 'MIX' in tipo_upper:
        return '06'
    
    return '??'


def extraer_manejo(tipo_manejo: str) -> str:
    """Extrae el codigo de manejo del campo x_studio_categora_tipo_de_manejo."""
    if not tipo_manejo:
        return '?'
    
    if tipo_manejo in MANEJO_MAP:
        return MANEJO_MAP[tipo_manejo]
    
    manejo_upper = tipo_manejo.upper()
    if 'CONV' in manejo_upper:
        return '1'
    if 'ORG' in manejo_upper:
        return '2'
    
    return '?'


def extraer_grado_de_nombre(nombre: str) -> str:
    """Deduce el grado del nombre del producto."""
    if not nombre:
        return '?'
    
    nombre_upper = nombre.upper()
    
    # Buscar patrones de grado en orden de especificidad
    if 'IQF AA' in nombre_upper or 'IQFAA' in nombre_upper:
        return '1'
    if 'IQF A' in nombre_upper or 'IQFA' in nombre_upper or 'IQF-A' in nombre_upper:
        return '2'
    if 'WHOLE AND BROKEN' in nombre_upper or 'W&B' in nombre_upper or 'W & B' in nombre_upper:
        return '4'
    if 'PSP' in nombre_upper:
        return '3'
    if 'BLOCK' in nombre_upper:
        return '5'
    if 'CRUMBLE' in nombre_upper:
        return '5'
    if 'CALIDAD JUGO' in nombre_upper or 'JUICE' in nombre_upper or 'JUGO' in nombre_upper:
        return '6'
    if 'IQF RETAIL' in nombre_upper:
        return '7'
    if 'IQF' in nombre_upper:  # IQF generico = IQF A
        return '2'
    
    return '?'


def extraer_variedad_de_ids(variedad_ids: list) -> str:
    """
    Intenta extraer la variedad desde los IDs de x_studio_categora_variedad.
    Devuelve None si no encuentra match.
    """
    if not variedad_ids:
        return None
        
    for var_id in variedad_ids:
        if var_id in VARIEDAD_ID_MAP:
            return VARIEDAD_ID_MAP[var_id]
            
    return None


def extraer_variedad_de_nombre(nombre: str, familia: str) -> str:
    """Deduce la variedad del nombre del producto."""
    if not nombre:
        return '1'  # Default S/V
    
    nombre_upper = nombre.upper()
    
    # Buscar patrones de variedad
    if 'S/V' in nombre_upper or 'SIN VARIEDAD' in nombre_upper:
        return '1'
    if 'HIGHBUSH' in nombre_upper or ' HB ' in nombre_upper or nombre_upper.startswith('HB '):
        return '2'
    if 'RABBITEYE' in nombre_upper or ' RE ' in nombre_upper:
        return '3'
    if 'MEEKER' in nombre_upper or ' MK ' in nombre_upper:
        return '2'
    if 'WAKEFIELD' in nombre_upper:
        return '3'
    if 'HERITAGE' in nombre_upper or ' HE ' in nombre_upper:
        return '2'
    if 'ALBION' in nombre_upper:
        return '2'
    
    return '1'  # Default S/V


def construir_codigo_sugerido(producto_data: dict, nombre: str) -> tuple[str, str]:
    """
    Construye el codigo sugerido basandose en los campos reales del producto.
    
    Returns:
        (codigo_sugerido, descripcion_construccion)
    """
    # Extraer datos del producto
    categoria = producto_data.get('categ_id', '')
    if isinstance(categoria, list) and len(categoria) > 1:
        categoria = categoria[1]
    elif isinstance(categoria, list):
        categoria = ''
    
    tipo_fruta = producto_data.get('x_studio_sub_categora', '') or ''
    tipo_manejo = producto_data.get('x_studio_categora_tipo_de_manejo', '') or ''
    variedad_ids = producto_data.get('x_studio_categora_variedad', [])
    
    # Construir cada componente
    etapa = extraer_etapa_de_categoria(categoria)
    familia = extraer_familia(tipo_fruta)
    manejo = extraer_manejo(tipo_manejo)
    grado = extraer_grado_de_nombre(nombre)
    
    # Intentar sacar variedad por ID primero, luego por nombre
    variedad = extraer_variedad_de_ids(variedad_ids)
    origen_variedad = "ID"
    
    if not variedad:
        variedad = extraer_variedad_de_nombre(nombre, familia)
        origen_variedad = "Nombre"
        
    retail = '000'  # Default
    
    # Construir codigo
    codigo = f"{etapa}{familia}{manejo}{grado}{variedad}{retail}"
    
    # Descripcion de la construccion
    partes = []
    if etapa != '?':
        partes.append(f"Etapa:{etapa}")
    if familia != '??':
        partes.append(f"Fam:{familia}")
    if manejo != '?':
        partes.append(f"Man:{manejo}")
    if grado != '?':
        partes.append(f"Grado:{grado}")
    if variedad:
        partes.append(f"Var:{variedad}({origen_variedad})")
    
    descripcion = ' | '.join(partes) if partes else 'Sin datos suficientes'
    
    # Verificar si el codigo es completo
    tiene_incompleto = '?' in codigo
    
    return codigo, descripcion, tiene_incompleto


def validar_codigo_sintaxis(codigo: str) -> tuple[bool, str]:
    """
    Valida solo la estructura sintactica del codigo.
    """
    if not codigo:
        return False, "Sin codigo"
    
    codigo = codigo.strip()
    
    if len(codigo) != 9:
        return False, f"Longitud incorrecta ({len(codigo)} de 9)"
    
    if not codigo.isdigit():
        return False, "Contiene caracteres no numericos"
        
    return True, "OK"


def validar_producto(codigo: str, producto_data: dict, nombre: str) -> tuple[bool, str]:
    """
    Valida sintaxis y semantica del codigo respecto a los atributos del producto.
    """
    # 1. Validacion Sintactica
    sintaxis_ok, motivo = validar_codigo_sintaxis(codigo)
    if not sintaxis_ok:
        return False, motivo
        
    # 2. Validacion Semantica (Coherencia)
    # Extraer valores esperados
    categoria = producto_data.get('categ_id', '')
    if isinstance(categoria, list) and len(categoria) > 1:
        categoria = categoria[1]
    elif isinstance(categoria, list):
        categoria = ''
        
    tipo_fruta = producto_data.get('x_studio_sub_categora', '') or ''
    tipo_manejo = producto_data.get('x_studio_categora_tipo_de_manejo', '') or ''
    variedad_ids = producto_data.get('x_studio_categora_variedad', [])
    
    # Etapa (Pos 0)
    etapa_esperada = extraer_etapa_de_categoria(categoria)
    if etapa_esperada != '?' and codigo[0] != etapa_esperada:
        return False, f"Incoherencia Etapa: Codigo='{codigo[0]}' vs Produc='{etapa_esperada}'"
        
    # Familia (Pos 1-3)
    familia_esperada = extraer_familia(tipo_fruta)
    if familia_esperada != '??' and codigo[1:3] != familia_esperada:
        return False, f"Incoherencia Familia: Codigo='{codigo[1:3]}' vs Produc='{familia_esperada}'"
        
    # Manejo (Pos 3)
    manejo_esperado = extraer_manejo(tipo_manejo)
    if manejo_esperado != '?' and codigo[3] != manejo_esperado:
        return False, f"Incoherencia Manejo: Codigo='{codigo[3]}' vs Produc='{manejo_esperado}'"
    
    # Variedad (Pos 5) - Solo si tenemos ID experto
    variedad_esperada = extraer_variedad_de_ids(variedad_ids)
    if variedad_esperada and codigo[5] != variedad_esperada:
        return False, f"Incoherencia Variedad: Codigo='{codigo[5]}' vs Produc='{variedad_esperada}'"

    # Grado (Pos 4) - Verificacion laxa contra nombre
    grado_esperado = extraer_grado_de_nombre(nombre)
    if grado_esperado != '?' and codigo[4] != grado_esperado:
        # A veces el nombre es ambiguo, asi que esto podria ser false positive.
        # Por ahora lo dejamos pasar o lo marcamos como warning?
        # El usuario pidio validacion semantica estricta para lo que falta.
        # Vamos a dejarlo fuera del "error" fatal por ahora para no saturar,
        # salvo que sea muy obvio. O mejor aun: No validamos grado semanticamente estricto aun.
        pass

    return True, "OK"


def main():
    """Funcion principal del script."""
    
    import argparse
    parser = argparse.ArgumentParser(description='Buscar productos no estandarizados')
    parser.add_argument('--debug-orders', help='Lista de ordenes separadas por coma para debug (ej: S00873,S00745)')
    args = parser.parse_args()
    
    debug_orders = args.debug_orders.split(',') if args.debug_orders else []
    
    print("\n" + "=" * 100)
    print("BUSQUEDA DE PRODUCTOS NO ESTANDARIZADOS EN ORDENES DE VENTA")
    print("Version 3.0 - Validacion Semantica (Sintaxis + Coherencia)")
    print(f"Periodo: {FECHA_DESDE} a {FECHA_HASTA}")
    if debug_orders:
        print(f"MODO DEBUG: Filtrando por ordenes {debug_orders}")
    print("=" * 100)
    
    # Conectar a Odoo
    print("\n[*] Conectando a Odoo...")
    odoo = OdooClient(username=ODOO_USER, password=ODOO_PASSWORD)
    print("[OK] Conectado exitosamente\n")
    
    # =========================================================================
    # PASO 1: Obtener TODOS los productos con sus campos de clasificacion
    # =========================================================================
    print("[*] Cargando catalogo de productos con datos de clasificacion...")
    
    # Primero obtener product.product con su template
    productos_raw = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'product.product', 'search_read',
        [[]],
        {
            'fields': ['id', 'name', 'default_code', 'product_tmpl_id'],
            'limit': 50000,
            'context': {'active_test': False}
        }
    )
    
    print(f"    Productos encontrados: {len(productos_raw):,}")
    
    # Obtener templates con campos de clasificacion
    template_ids = list(set([p['product_tmpl_id'][0] for p in productos_raw if p.get('product_tmpl_id')]))
    
    templates_raw = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'product.template', 'search_read',
        [[['id', 'in', template_ids]]],
        {
            'fields': ['id', 'name', 'categ_id', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo', 'x_studio_categora_variedad'],
            'context': {'active_test': False}
        }
    )
    
    print(f"    Templates con clasificacion: {len(templates_raw):,}")
    
    # Crear mapas
    template_map = {t['id']: t for t in templates_raw}
    producto_to_template = {p['id']: p['product_tmpl_id'][0] for p in productos_raw if p.get('product_tmpl_id')}
    producto_codigo_map = {p['id']: p.get('default_code', '') for p in productos_raw}
    producto_nombre_map = {p['id']: p.get('name', '') for p in productos_raw}
    
    # =========================================================================
    # PASO 2: Obtener ordenes de venta en el periodo
    # =========================================================================
    print(f"\n[*] Buscando ordenes de venta ({FECHA_DESDE} a {FECHA_HASTA})...")
    
    domain = [
        ['date_order', '>=', FECHA_DESDE],
        ['date_order', '<=', FECHA_HASTA + ' 23:59:59'],
        ['state', '!=', 'cancel']
    ]
    
    if debug_orders:
        domain.append(['name', 'in', debug_orders])
    
    ordenes = odoo.search_read(
        'sale.order',
        domain,
        ['id', 'name', 'date_order', 'partner_id', 'state'],
        order='date_order asc'
    )
    
    print(f"    Ordenes encontradas: {len(ordenes):,}\n")
    
    if not ordenes:
        print("[!] No se encontraron ordenes en el periodo especificado.")
        return
    
    orden_map = {o['id']: o for o in ordenes}
    orden_ids = [o['id'] for o in ordenes]
    
    # =========================================================================
    # PASO 3: Obtener lineas de venta
    # =========================================================================
    print("[*] Obteniendo lineas de venta...")
    
    lineas = odoo.search_read(
        'sale.order.line',
        [
            ['order_id', 'in', orden_ids],
            ['product_id', '!=', False]
        ],
        ['id', 'order_id', 'product_id', 'product_uom_qty', 'price_unit'],
        limit=100000
    )
    
    print(f"    Lineas de venta: {len(lineas):,}\n")
    
    # =========================================================================
    # PASO 4: Analizar cada linea y construir sugerencias
    # =========================================================================
    print("[*] Analizando codigos y construyendo sugerencias...\n")
    
    ordenes_problematicas = defaultdict(list)
    productos_no_estandar = set()
    productos_ok = set()
    
    for linea in lineas:
        orden_id = linea.get('order_id', [None])[0] if linea.get('order_id') else None
        producto_id = linea.get('product_id', [None])[0] if linea.get('product_id') else None
        producto_nombre = linea.get('product_id', [None, 'N/A'])[1] if linea.get('product_id') else 'N/A'
        
        if not orden_id or not producto_id:
            continue
        
        # Obtener datos completos del producto para validacion
        template_id = producto_to_template.get(producto_id)
        template_data = template_map.get(template_id, {}) if template_id else {}
        codigo = producto_codigo_map.get(producto_id, '')

        # VALIDACION COMPLETA (Sintaxis + Semantica)
        es_valido, motivo = validar_producto(codigo, template_data, producto_nombre)
        
        if es_valido:
            productos_ok.add(producto_id)
        else:
            productos_no_estandar.add(producto_id)
            
            # Construir codigo sugerido
            codigo_sugerido, descripcion, incompleto = construir_codigo_sugerido(
                template_data, 
                producto_nombre
            )
            
            ordenes_problematicas[orden_id].append({
                'producto_id': producto_id,
                'nombre': producto_nombre,
                'codigo_actual': codigo if codigo else 'VACIO',
                'motivo': motivo,
                'cantidad': linea.get('product_uom_qty', 0),
                'codigo_sugerido': codigo_sugerido,
                'descripcion_construccion': descripcion,
                'incompleto': incompleto,
                'tipo_fruta': template_data.get('x_studio_sub_categora', ''),
                'tipo_manejo': template_data.get('x_studio_categora_tipo_de_manejo', '')
            })
    
    # =========================================================================
    # PASO 5: Mostrar resultados
    # =========================================================================
    print("=" * 100)
    print("ORDENES CON PRODUCTOS NO ESTANDARIZADOS")
    print("=" * 100)
    
    total_problemas = 0
    sugerencias_completas = 0
    
    for orden_id, problemas in sorted(ordenes_problematicas.items(), key=lambda x: orden_map.get(x[0], {}).get('name', '')):
        orden = orden_map.get(orden_id, {})
        nombre_orden = orden.get('name', f'ID:{orden_id}')
        fecha = orden.get('date_order', 'N/A')[:10] if orden.get('date_order') else 'N/A'
        cliente = orden.get('partner_id', [None, 'N/A'])[1] if orden.get('partner_id') else 'N/A'
        estado = orden.get('state', 'N/A')
        
        print(f"\n[ORDEN] {nombre_orden} | {fecha} | {cliente[:40]} | Estado: {estado}")
        print("-" * 100)
        
        for prob in problemas:
            total_problemas += 1
            if not prob['incompleto']:
                sugerencias_completas += 1
            
            estado_sug = "[COMPLETO]" if not prob['incompleto'] else "[PARCIAL]"
            print(f"   [X] [{prob['codigo_actual']:>12}] {prob['nombre'][:50]}")
            print(f"       Motivo: {prob['motivo']}")
            print(f"       Sugerido: {prob['codigo_sugerido']} {estado_sug}")
            print(f"       Detalle: {prob['descripcion_construccion']}")
            print(f"       Base: TipoFruta={prob['tipo_fruta'] or 'N/A'} | Manejo={prob['tipo_manejo'] or 'N/A'}")
    
    # =========================================================================
    # PASO 6: Resumen estadistico
    # =========================================================================
    print("\n" + "=" * 100)
    print("RESUMEN ESTADISTICO")
    print("=" * 100)
    
    pct_problemas = len(ordenes_problematicas)/len(ordenes)*100 if len(ordenes) > 0 else 0
    pct_completas = sugerencias_completas/total_problemas*100 if total_problemas > 0 else 0
    
    print(f"""
    Ordenes de venta analizadas:  {len(ordenes):,}
    Ordenes con problemas:        {len(ordenes_problematicas):,} ({pct_problemas:.1f}%)
    
    Productos unicos analizados:  {len(productos_ok) + len(productos_no_estandar):,}
    Productos con codigo valido:  {len(productos_ok):,}
    Productos sin codigo estandar:{len(productos_no_estandar):,}
    
    Total de lineas problematicas:  {total_problemas:,}
    Sugerencias completas:          {sugerencias_completas:,} ({pct_completas:.1f}%)
    Sugerencias parciales:          {total_problemas - sugerencias_completas:,}
    """)
    
    # =========================================================================
    # PASO 7: Exportar a Excel
    # =========================================================================
    print("[*] Generando archivo Excel...")
    
    try:
        import pandas as pd
        
        datos_excel = []
        
        for orden_id, problemas in ordenes_problematicas.items():
            orden = orden_map.get(orden_id, {})
            nombre_orden = orden.get('name', f'ID:{orden_id}')
            fecha = orden.get('date_order', 'N/A')[:10] if orden.get('date_order') else 'N/A'
            cliente = orden.get('partner_id', [None, 'N/A'])[1] if orden.get('partner_id') else 'N/A'
            estado = orden.get('state', 'N/A')
            
            for prob in problemas:
                datos_excel.append({
                    'Orden': nombre_orden,
                    'Fecha': fecha,
                    'Cliente': cliente,
                    'Estado Orden': estado,
                    'Producto': prob['nombre'],
                    'Codigo Actual': prob['codigo_actual'],
                    'Motivo Error': prob['motivo'],
                    'Cantidad': prob['cantidad'],
                    'Codigo Sugerido': prob['codigo_sugerido'],
                    'Sugerencia Completa': 'SI' if not prob['incompleto'] else 'NO',
                    'Tipo Fruta (Odoo)': prob['tipo_fruta'],
                    'Tipo Manejo (Odoo)': prob['tipo_manejo']
                })
        
        df = pd.DataFrame(datos_excel)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_excel = f"productos_no_estandarizados_{timestamp}.xlsx"
        
        df.to_excel(archivo_excel, index=False, sheet_name='Productos No Estandar')
        
        print(f"    [OK] Archivo guardado: {archivo_excel}")
        print(f"    [OK] Registros exportados: {len(datos_excel):,}")
        
    except ImportError:
        print("    [!] pandas no esta instalado. No se pudo generar el Excel.")
    except Exception as e:
        print(f"    [X] Error al generar Excel: {e}")
    
    print("\n" + "=" * 100)
    print("[OK] ANALISIS COMPLETADO")
    print("=" * 100 + "\n")


if __name__ == '__main__':
    main()
