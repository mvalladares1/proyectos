"""
Debug COMPLETO de Fabricaciones - Rio Futuro
=============================================
Este script extrae TODA la información de fabricaciones, componentes, 
subproductos, categorías, manejos, salas, túneles y rendimientos.

Uso: python scripts/debug_fabricaciones.py

Autor: Debug para diagnóstico profundo
Fecha: 2026-01-15
"""
import sys
import os
import json
from datetime import datetime, timedelta
from collections import defaultdict

# Añadir path del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

# Credenciales
USERNAME = "mvalladares@riofuturo.cl"
API_KEY = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Configuración
FECHA_INICIO = "2025-11-17"  # Desde cuando filtrar
FECHA_FIN = "2026-01-15"     # Hasta cuando filtrar
LIMITE_MOS = 20              # Número de MOs a analizar en detalle


def separador(titulo):
    """Imprime un separador visual."""
    print(f"\n{'='*70}")
    print(f"  {titulo}")
    print(f"{'='*70}\n")


def debug_campos_producto():
    """
    PASO 1: Verificar qué campos existen en product.template
    para especie/manejo/categoría.
    """
    separador("PASO 1: CAMPOS DISPONIBLES EN PRODUCT.TEMPLATE")
    
    client = OdooClient(username=USERNAME, password=API_KEY)
    
    # Buscar un producto de ejemplo que sabemos tiene datos
    producto_ejemplo = client.search_read(
        'product.template',
        [['name', 'ilike', 'IQF']],
        [],  # Todos los campos
        limit=1
    )
    
    if producto_ejemplo:
        print("📋 Campos disponibles en product.template:")
        campos_x_studio = []
        campos_otros = []
        
        for campo, valor in sorted(producto_ejemplo[0].items()):
            if 'x_studio' in campo.lower():
                campos_x_studio.append((campo, valor))
            elif 'categ' in campo.lower() or 'manejo' in campo.lower() or 'tipo' in campo.lower():
                campos_otros.append((campo, valor))
        
        print("\n  📌 Campos x_studio_ (personalizados):")
        for campo, valor in campos_x_studio:
            valor_str = str(valor)[:80] if valor else "None"
            print(f"     • {campo}: {valor_str}")
        
        print("\n  📌 Campos relacionados con categoría/tipo:")
        for campo, valor in campos_otros:
            valor_str = str(valor)[:80] if valor else "None"
            print(f"     • {campo}: {valor_str}")
    else:
        print("❌ No se encontraron productos de ejemplo")
    
    return campos_x_studio if producto_ejemplo else []


def debug_producto_especifico():
    """
    PASO 2: Analizar un producto específico que sabemos tiene datos.
    Basado en la imagen: [201222000] AR HB Org. IQF Congelado en Bandeja
    """
    separador("PASO 2: ANÁLISIS DE PRODUCTO ESPECÍFICO")
    
    client = OdooClient(username=USERNAME, password=API_KEY)
    
    # Buscar el producto específico de la imagen
    productos = client.search_read(
        'product.template',
        [['default_code', 'ilike', '201222000']],
        ['id', 'name', 'default_code', 'categ_id',
         'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
        limit=5
    )
    
    if not productos:
        # Intentar buscar por nombre
        productos = client.search_read(
            'product.template',
            [['name', 'ilike', 'AR HB Org']],
            ['id', 'name', 'default_code', 'categ_id',
             'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
            limit=5
        )
    
    if productos:
        print(f"✅ Productos encontrados: {len(productos)}")
        for p in productos:
            print(f"\n   📦 Producto ID: {p['id']}")
            print(f"      Nombre: {p.get('name', 'N/A')}")
            print(f"      Código: {p.get('default_code', 'N/A')}")
            print(f"      Categoría: {p.get('categ_id', 'N/A')}")
            
            # Analizar campos de tipo de fruta
            tipo_fruta = p.get('x_studio_sub_categora')
            print(f"      x_studio_sub_categora (Tipo Fruta): {tipo_fruta}")
            if isinstance(tipo_fruta, (list, tuple)):
                print(f"         → Es lista/tupla, valor[1]: {tipo_fruta[1] if len(tipo_fruta) > 1 else 'N/A'}")
            
            # Analizar campos de manejo
            manejo = p.get('x_studio_categora_tipo_de_manejo')
            print(f"      x_studio_categora_tipo_de_manejo (Manejo): {manejo}")
            if isinstance(manejo, (list, tuple)):
                print(f"         → Es lista/tupla, valor[1]: {manejo[1] if len(manejo) > 1 else 'N/A'}")
    else:
        print("❌ No se encontró el producto específico")
    
    return productos


def debug_mo_completa(mo_name="WH/RF/MO/00841"):
    """
    PASO 3: Analizar una MO completa con todos sus componentes y subproductos.
    """
    separador(f"PASO 3: ANÁLISIS COMPLETO DE MO: {mo_name}")
    
    client = OdooClient(username=USERNAME, password=API_KEY)
    
    # Buscar la MO
    mos = client.search_read(
        'mrp.production',
        [['name', '=', mo_name]],
        ['id', 'name', 'product_id', 'state', 'date_planned_start',
         'x_studio_sala_de_proceso', 'x_studio_dotacin', 
         'x_studio_inicio_de_proceso', 'x_studio_termino_de_proceso',
         'move_raw_ids', 'move_finished_ids', 'move_byproduct_ids'],
        limit=1
    )
    
    if not mos:
        print(f"❌ MO '{mo_name}' no encontrada")
        return None
    
    mo = mos[0]
    print(f"✅ MO encontrada: {mo['name']}")
    print(f"   ID: {mo['id']}")
    print(f"   Producto: {mo.get('product_id', 'N/A')}")
    print(f"   Estado: {mo.get('state', 'N/A')}")
    print(f"   Sala: {mo.get('x_studio_sala_de_proceso', 'N/A')}")
    print(f"   Dotación: {mo.get('x_studio_dotacin', 'N/A')}")
    print(f"   Inicio Proceso: {mo.get('x_studio_inicio_de_proceso', 'N/A')}")
    print(f"   Fin Proceso: {mo.get('x_studio_termino_de_proceso', 'N/A')}")
    
    # ===== COMPONENTES =====
    print(f"\n   📥 COMPONENTES (move_raw_ids):")
    raw_ids = mo.get('move_raw_ids', [])
    print(f"      Total move_raw_ids: {len(raw_ids)}")
    
    if raw_ids:
        # Obtener stock.move.line para estos moves
        move_lines = client.search_read(
            'stock.move.line',
            [['move_id', 'in', raw_ids]],
            ['move_id', 'product_id', 'lot_id', 'qty_done'],
            limit=100
        )
        
        print(f"      Move lines encontrados: {len(move_lines)}")
        
        # Obtener info completa de productos
        product_ids = set()
        for ml in move_lines:
            prod = ml.get('product_id')
            if prod:
                pid = prod[0] if isinstance(prod, (list, tuple)) else prod
                product_ids.add(pid)
        
        print(f"      Productos únicos: {len(product_ids)}")
        
        # Obtener product.product con product_tmpl_id
        if product_ids:
            products_pp = client.search_read(
                'product.product',
                [['id', 'in', list(product_ids)]],
                ['id', 'name', 'product_tmpl_id', 'default_code'],
                limit=100
            )
            
            # Mapear product_id -> tmpl_id
            pp_to_tmpl = {}
            tmpl_ids = set()
            for pp in products_pp:
                tmpl = pp.get('product_tmpl_id')
                if tmpl:
                    tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
                    pp_to_tmpl[pp['id']] = tmpl_id
                    tmpl_ids.add(tmpl_id)
            
            # Obtener product.template con campos de especie/manejo
            if tmpl_ids:
                templates = client.read(
                    'product.template',
                    list(tmpl_ids),
                    ['id', 'name', 'default_code', 'categ_id',
                     'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo']
                )
                
                tmpl_map = {}
                for t in templates:
                    especie_raw = t.get('x_studio_sub_categora')
                    manejo_raw = t.get('x_studio_categora_tipo_de_manejo')
                    
                    # Extraer valor correcto
                    if isinstance(especie_raw, (list, tuple)) and len(especie_raw) > 1:
                        especie = especie_raw[1]
                    elif especie_raw:
                        especie = str(especie_raw)
                    else:
                        especie = 'Sin dato'
                    
                    if isinstance(manejo_raw, (list, tuple)) and len(manejo_raw) > 1:
                        manejo = manejo_raw[1]
                    elif manejo_raw:
                        manejo = str(manejo_raw)
                    else:
                        manejo = 'Sin dato'
                    
                    tmpl_map[t['id']] = {
                        'name': t.get('name', ''),
                        'especie': especie,
                        'manejo': manejo,
                        'especie_raw': especie_raw,
                        'manejo_raw': manejo_raw
                    }
                
                # Mostrar componentes con su especie/manejo
                print(f"\n      Detalle de componentes:")
                total_kg = 0
                for ml in move_lines:
                    prod = ml.get('product_id')
                    if not prod:
                        continue
                    
                    pid = prod[0] if isinstance(prod, (list, tuple)) else prod
                    prod_name = prod[1] if isinstance(prod, (list, tuple)) and len(prod) > 1 else 'N/A'
                    qty = ml.get('qty_done', 0) or 0
                    total_kg += qty
                    
                    tmpl_id = pp_to_tmpl.get(pid)
                    tmpl_info = tmpl_map.get(tmpl_id, {})
                    
                    especie = tmpl_info.get('especie', 'NO_ENCONTRADO')
                    manejo = tmpl_info.get('manejo', 'NO_ENCONTRADO')
                    
                    print(f"         • {prod_name[:50]}")
                    print(f"           Qty: {qty:,.2f} kg | Especie: {especie} | Manejo: {manejo}")
                    
                    # Mostrar valores raw si hay problema
                    if especie == 'Sin dato' or manejo == 'Sin dato':
                        print(f"           ⚠️ RAW: especie={tmpl_info.get('especie_raw')} manejo={tmpl_info.get('manejo_raw')}")
                
                print(f"\n      TOTAL KG COMPONENTES: {total_kg:,.2f}")
    
    # ===== SUBPRODUCTOS =====
    print(f"\n   📤 SUBPRODUCTOS (move_finished_ids + move_byproduct_ids):")
    finished_ids = mo.get('move_finished_ids', []) + mo.get('move_byproduct_ids', [])
    print(f"      Total moves: {len(finished_ids)}")
    
    if finished_ids:
        move_lines = client.search_read(
            'stock.move.line',
            [['move_id', 'in', finished_ids]],
            ['move_id', 'product_id', 'lot_id', 'qty_done'],
            limit=100
        )
        
        print(f"      Move lines encontrados: {len(move_lines)}")
        
        total_kg = 0
        for ml in move_lines:
            prod = ml.get('product_id')
            if not prod:
                continue
            
            prod_name = prod[1] if isinstance(prod, (list, tuple)) and len(prod) > 1 else 'N/A'
            qty = ml.get('qty_done', 0) or 0
            total_kg += qty
            
            print(f"         • {prod_name[:60]} | {qty:,.2f} kg")
        
        print(f"\n      TOTAL KG SUBPRODUCTOS: {total_kg:,.2f}")
    
    return mo


def debug_todas_mos():
    """
    PASO 4: Analizar TODAS las MOs del período y generar estadísticas.
    """
    separador(f"PASO 4: ANÁLISIS DE TODAS LAS MOs ({FECHA_INICIO} a {FECHA_FIN})")
    
    client = OdooClient(username=USERNAME, password=API_KEY)
    
    # Obtener MOs del período
    mos = client.search_read(
        'mrp.production',
        [
            ['date_planned_start', '>=', f'{FECHA_INICIO} 00:00:00'],
            ['date_planned_start', '<=', f'{FECHA_FIN} 23:59:59'],
            ['state', '=', 'done']
        ],
        ['id', 'name', 'product_id', 'state', 'date_planned_start',
         'x_studio_sala_de_proceso', 'move_raw_ids', 'move_finished_ids'],
        limit=500,
        order='date_planned_start desc'
    )
    
    print(f"📊 Total MOs encontradas: {len(mos)}")
    
    # Estadísticas
    salas = defaultdict(int)
    plantas = defaultdict(int)
    especies = defaultdict(int)
    manejos = defaultdict(int)
    productos_sin_especie = []
    productos_sin_manejo = []
    
    # Obtener todos los move_raw_ids
    all_raw_ids = []
    for mo in mos:
        all_raw_ids.extend(mo.get('move_raw_ids', []))
    
    print(f"   Total move_raw_ids a analizar: {len(all_raw_ids)}")
    
    if all_raw_ids:
        # Obtener move lines
        move_lines = client.search_read(
            'stock.move.line',
            [['move_id', 'in', all_raw_ids]],
            ['move_id', 'product_id', 'qty_done'],
            limit=10000
        )
        
        print(f"   Move lines encontrados: {len(move_lines)}")
        
        # Obtener productos únicos
        product_ids = set()
        for ml in move_lines:
            prod = ml.get('product_id')
            if prod:
                pid = prod[0] if isinstance(prod, (list, tuple)) else prod
                product_ids.add(pid)
        
        print(f"   Productos únicos: {len(product_ids)}")
        
        # Obtener product.product
        products_pp = client.search_read(
            'product.product',
            [['id', 'in', list(product_ids)]],
            ['id', 'name', 'product_tmpl_id'],
            limit=5000
        )
        
        pp_to_tmpl = {}
        tmpl_ids = set()
        for pp in products_pp:
            tmpl = pp.get('product_tmpl_id')
            if tmpl:
                tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
                pp_to_tmpl[pp['id']] = {
                    'tmpl_id': tmpl_id,
                    'name': pp['name']
                }
                tmpl_ids.add(tmpl_id)
        
        # Obtener templates con especie/manejo
        print(f"   Templates a consultar: {len(tmpl_ids)}")
        
        if tmpl_ids:
            templates = client.read(
                'product.template',
                list(tmpl_ids),
                ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo']
            )
            
            tmpl_map = {}
            for t in templates:
                especie_raw = t.get('x_studio_sub_categora')
                manejo_raw = t.get('x_studio_categora_tipo_de_manejo')
                
                if isinstance(especie_raw, (list, tuple)) and len(especie_raw) > 1:
                    especie = especie_raw[1]
                elif especie_raw:
                    especie = str(especie_raw)
                else:
                    especie = None
                
                if isinstance(manejo_raw, (list, tuple)) and len(manejo_raw) > 1:
                    manejo = manejo_raw[1]
                elif manejo_raw:
                    manejo = str(manejo_raw)
                else:
                    manejo = None
                
                tmpl_map[t['id']] = {
                    'especie': especie,
                    'manejo': manejo
                }
                
                # Contabilizar
                if especie:
                    especies[especie] += 1
                else:
                    productos_sin_especie.append(t.get('name', 'N/A'))
                
                if manejo:
                    manejos[manejo] += 1
                else:
                    productos_sin_manejo.append(t.get('name', 'N/A'))
    
    # Estadísticas de salas
    for mo in mos:
        sala = mo.get('x_studio_sala_de_proceso') or 'Sin Sala'
        salas[sala] += 1
        
        # Detectar planta
        mo_name = mo.get('name', '')
        if mo_name.upper().startswith('VLK'):
            plantas['VILKUN (por nombre)'] += 1
        elif 'VLK' in str(sala).upper() or 'VILKUN' in str(sala).upper():
            plantas['VILKUN (por sala)'] += 1
        else:
            plantas['RIO FUTURO'] += 1
    
    # Mostrar resultados
    print("\n" + "─"*50)
    print("📊 ESTADÍSTICAS GENERALES")
    print("─"*50)
    
    print(f"\n🏭 SALAS ({len(salas)} únicas):")
    for sala, count in sorted(salas.items(), key=lambda x: -x[1]):
        print(f"   • {sala}: {count} MOs")
    
    print(f"\n🏢 PLANTAS:")
    for planta, count in sorted(plantas.items(), key=lambda x: -x[1]):
        print(f"   • {planta}: {count} MOs")
    
    print(f"\n🍓 ESPECIES ({len(especies)} únicas):")
    for especie, count in sorted(especies.items(), key=lambda x: -x[1]):
        print(f"   • {especie}: {count} productos")
    
    print(f"\n🏷️ MANEJOS ({len(manejos)} únicos):")
    for manejo, count in sorted(manejos.items(), key=lambda x: -x[1]):
        print(f"   • {manejo}: {count} productos")
    
    if productos_sin_especie:
        print(f"\n⚠️ PRODUCTOS SIN ESPECIE ({len(productos_sin_especie)}):")
        for p in productos_sin_especie[:10]:
            print(f"   • {p[:60]}")
        if len(productos_sin_especie) > 10:
            print(f"   ... y {len(productos_sin_especie) - 10} más")
    
    if productos_sin_manejo:
        print(f"\n⚠️ PRODUCTOS SIN MANEJO ({len(productos_sin_manejo)}):")
        for p in productos_sin_manejo[:10]:
            print(f"   • {p[:60]}")
        if len(productos_sin_manejo) > 10:
            print(f"   ... y {len(productos_sin_manejo) - 10} más")
    
    return {
        'total_mos': len(mos),
        'salas': dict(salas),
        'plantas': dict(plantas),
        'especies': dict(especies),
        'manejos': dict(manejos)
    }


def debug_flujo_rendimiento():
    """
    PASO 5: Verificar el flujo completo de cálculo de rendimiento
    usando el servicio actual.
    """
    separador("PASO 5: FLUJO DE RENDIMIENTO (Servicio Actual)")
    
    try:
        from backend.services.rendimiento_service import RendimientoService
        
        service = RendimientoService(username=USERNAME, password=API_KEY)
        
        # Obtener datos del dashboard
        print(f"⏳ Consultando dashboard para {FECHA_INICIO} a {FECHA_FIN}...")
        data = service.get_dashboard_completo(FECHA_INICIO, FECHA_FIN, solo_terminadas=True)
        
        if data:
            overview = data.get('overview', {})
            mos = data.get('mos', [])
            consolidado = data.get('consolidado', {})
            
            print(f"\n📊 OVERVIEW:")
            print(f"   Total MOs procesadas: {overview.get('mos_procesadas', 0)}")
            print(f"   Total Kg MP: {overview.get('total_kg_mp', 0):,.0f}")
            print(f"   Total Kg PT: {overview.get('total_kg_pt', 0):,.0f}")
            print(f"   Rendimiento: {overview.get('rendimiento_promedio', 0):.1f}%")
            
            print(f"\n📊 MOs PROCESADAS ({len(mos)}):")
            
            # Contar especies/manejos en el resultado
            especies_res = defaultdict(int)
            manejos_res = defaultdict(int)
            
            for mo in mos[:10]:  # Mostrar primeras 10
                print(f"\n   {mo.get('mo_name')}:")
                print(f"      Especie: {mo.get('especie', 'N/A')}")
                print(f"      Manejo: {mo.get('manejo', 'N/A')}")
                print(f"      Kg MP: {mo.get('kg_mp', 0):,.0f}")
                print(f"      Kg PT: {mo.get('kg_pt', 0):,.0f}")
                print(f"      Rendimiento: {mo.get('rendimiento', 0):.1f}%")
            
            for mo in mos:
                especies_res[mo.get('especie', 'N/A')] += 1
                manejos_res[mo.get('manejo', 'N/A')] += 1
            
            print(f"\n📊 ESPECIES EN RESULTADO:")
            for esp, count in sorted(especies_res.items(), key=lambda x: -x[1]):
                print(f"   • {esp}: {count} MOs")
            
            print(f"\n📊 MANEJOS EN RESULTADO:")
            for man, count in sorted(manejos_res.items(), key=lambda x: -x[1]):
                print(f"   • {man}: {count} MOs")
            
            # Consolidado por fruta
            print(f"\n📊 CONSOLIDADO POR FRUTA:")
            for fruta in consolidado.get('por_fruta', []):
                print(f"   • {fruta.get('tipo_fruta')}: {fruta.get('kg_pt', 0):,.0f} kg PT")
        else:
            print("❌ No se obtuvieron datos del dashboard")
            
    except Exception as e:
        print(f"❌ Error al ejecutar servicio: {e}")
        import traceback
        traceback.print_exc()


def debug_comparacion_odoo_vs_servicio():
    """
    PASO 6: Comparar datos directos de Odoo vs lo que extrae el servicio
    para identificar dónde se pierde la información.
    """
    separador("PASO 6: COMPARACIÓN ODOO vs SERVICIO")
    
    client = OdooClient(username=USERNAME, password=API_KEY)
    
    # Tomar una MO específica
    mo_name = "WH/RF/MO/00841"  # La de la imagen
    
    print(f"🔍 Analizando MO: {mo_name}")
    
    # 1. Datos directos de Odoo
    print("\n1️⃣ DATOS DIRECTOS DE ODOO:")
    
    mos = client.search_read(
        'mrp.production',
        [['name', '=', mo_name]],
        ['id', 'name', 'move_raw_ids'],
        limit=1
    )
    
    if not mos:
        print(f"   ❌ MO no encontrada")
        return
    
    mo = mos[0]
    raw_ids = mo.get('move_raw_ids', [])
    
    # Obtener componentes
    if raw_ids:
        move_lines = client.search_read(
            'stock.move.line',
            [['move_id', 'in', raw_ids]],
            ['product_id', 'qty_done'],
            limit=50
        )
        
        # Obtener templates
        product_ids = set()
        for ml in move_lines:
            prod = ml.get('product_id')
            if prod:
                product_ids.add(prod[0] if isinstance(prod, (list, tuple)) else prod)
        
        products_pp = client.search_read(
            'product.product',
            [['id', 'in', list(product_ids)]],
            ['id', 'product_tmpl_id'],
            limit=100
        )
        
        tmpl_ids = set()
        pp_to_tmpl = {}
        for pp in products_pp:
            tmpl = pp.get('product_tmpl_id')
            if tmpl:
                tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
                tmpl_ids.add(tmpl_id)
                pp_to_tmpl[pp['id']] = tmpl_id
        
        templates = client.read(
            'product.template',
            list(tmpl_ids),
            ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo']
        )
        
        tmpl_map = {t['id']: t for t in templates}
        
        print(f"   Componentes encontrados: {len(move_lines)}")
        for ml in move_lines:
            prod = ml.get('product_id')
            if not prod:
                continue
            
            pid = prod[0] if isinstance(prod, (list, tuple)) else prod
            prod_name = prod[1] if isinstance(prod, (list, tuple)) and len(prod) > 1 else 'N/A'
            
            tmpl_id = pp_to_tmpl.get(pid)
            tmpl = tmpl_map.get(tmpl_id, {})
            
            especie_raw = tmpl.get('x_studio_sub_categora')
            manejo_raw = tmpl.get('x_studio_categora_tipo_de_manejo')
            
            especie = especie_raw[1] if isinstance(especie_raw, (list, tuple)) and len(especie_raw) > 1 else especie_raw
            manejo = manejo_raw[1] if isinstance(manejo_raw, (list, tuple)) and len(manejo_raw) > 1 else manejo_raw
            
            print(f"   • {prod_name[:50]}")
            print(f"     Especie: {especie} | Manejo: {manejo}")
    
    # 2. Datos del servicio
    print("\n2️⃣ DATOS DEL SERVICIO:")
    
    try:
        from backend.services.rendimiento_service import RendimientoService
        
        service = RendimientoService(username=USERNAME, password=API_KEY)
        
        # Buscar la MO en el resultado
        # Simular lo que hace get_consumos_batch
        consumos = service.get_consumos_batch([mo])
        
        mo_consumos = consumos.get(mo['id'], [])
        print(f"   Consumos extraídos por servicio: {len(mo_consumos)}")
        
        for c in mo_consumos:
            print(f"   • {c.get('product_name', 'N/A')[:50]}")
            print(f"     Especie: {c.get('especie', 'N/A')} | Manejo: {c.get('manejo', 'N/A')}")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")


def main():
    """Ejecuta todos los pasos de debug."""
    print("\n" + "="*70)
    print("  🔍 DEBUG COMPLETO DE FABRICACIONES - RIO FUTURO")
    print(f"     Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"     Período: {FECHA_INICIO} a {FECHA_FIN}")
    print("="*70)
    
    try:
        # Paso 1: Verificar campos disponibles
        debug_campos_producto()
        
        # Paso 2: Producto específico
        debug_producto_especifico()
        
        # Paso 3: MO completa
        debug_mo_completa("WH/RF/MO/00841")
        
        # Paso 4: Todas las MOs
        stats = debug_todas_mos()
        
        # Paso 5: Flujo de rendimiento
        debug_flujo_rendimiento()
        
        # Paso 6: Comparación
        debug_comparacion_odoo_vs_servicio()
        
        separador("RESUMEN FINAL")
        print("🎯 PUNTOS CLAVE PARA REVISAR:")
        print("   1. ¿Los campos x_studio_sub_categora y x_studio_categora_tipo_de_manejo")
        print("      están siendo leídos correctamente?")
        print("   2. ¿El mapeo product.product → product.template funciona?")
        print("   3. ¿El filtro is_excluded_consumo está excluyendo productos válidos?")
        print("   4. ¿La extracción de especie/manejo de listas/tuplas es correcta?")
        
    except Exception as e:
        print(f"\n❌ ERROR GENERAL: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
