"""
Servicio para consultar recepciones de materia prima (MP) desde Odoo
OPTIMIZADO: Usa batch queries para eliminar problema N+1 + Caché de 5 minutos
Migrado desde recepcion/backend/recepcion_service.py
"""
from typing import List, Dict, Any, Optional
from shared.odoo_client import OdooClient
from backend.cache import get_cache, OdooCache

# =============================================================================
# OVERRIDE DE ORIGEN: Pickings que deben aparecer con origen diferente al de Odoo
# Esto permite corregir recepciones mal ingresadas sin modificar Odoo
# Formato: {"nombre_picking": "ORIGEN_CORRECTO"}
# Valores válidos: "RFP", "VILKUN", "SAN JOSE"
# =============================================================================
OVERRIDE_ORIGEN_PICKING = {
    "RF/RFP/IN/01151": "VILKUN",
    "RF/RFP/IN/01117": "VILKUN",
    "RF/RFP/IN/01155": "VILKUN",
    "RF/RFP/IN/01156": "VILKUN",
    "RF/RFP/IN/00638": "VILKUN",
    "RF/RFP/IN/00386": "VILKUN",
    "RF/RFP/IN/00684": "VILKUN",
    "RF/RFP/IN/00329": "VILKUN",
    "RF/RFP/IN/00245": "VILKUN",
    "RF/RFP/IN/00664": "VILKUN",
    "RF/RFP/IN/00655": "VILKUN",
    "RF/RFP/IN/00563": "VILKUN",
}


def _normalize_categoria(cat: str) -> str:
    if not cat:
        return ''
    c = cat.strip().upper()
    if 'BANDEJ' in c:
        return 'BANDEJAS'
    return c


def get_recepciones_mp(username: str, password: str, fecha_inicio: str, fecha_fin: str, productor_id: Optional[int] = None, solo_hechas: bool = True, origen: Optional[List[str]] = None, estados: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Obtiene recepciones de materia prima con datos de calidad.
    OPTIMIZADO: Incluye caché de 5 minutos para reducir llamadas repetidas.
    
    OPTIMIZADO: Reduce de ~5 llamadas por recepción a ~6 llamadas totales:
    1. stock.picking (recepciones)
    2. stock.move (todos los movimientos)
    3. product.product (todos los productos)
    4. product.template (todos los templates)
    5. quality.check (todos los checks)
    6. x_quality_check_line_* (líneas por tipo)
    
    Args:
        solo_hechas: Si es True (y no se especifica 'estados'), solo muestra recepciones en estado "done".
        estados: Lista explícita de estados a filtrar (ej. ['assigned', 'done']). Si se usa, ignora solo_hechas.
        origen: Lista de orígenes a filtrar. Valores válidos: "RFP", "VILKUN".
                Si es None o vacío, se incluyen ambos.
    """
    client = OdooClient(username=username, password=password)
    cache = get_cache()
    
    # VALIDACIÓN DE TIPOS: Normalizar origen y estados antes de usarlos
    if origen is not None:
        if isinstance(origen, str):
            print(f"[WARNING] origen llegó como string '{origen}', convirtiendo a lista")
            origen = [origen]
        elif not isinstance(origen, list):
            print(f"[WARNING] origen llegó como tipo {type(origen)}, convirtiendo a lista")
            origen = list(origen) if origen else []
    
    if estados is not None:
        if isinstance(estados, str):
            print(f"[WARNING] estados llegó como string '{estados}', convirtiendo a lista")
            estados = [estados]
        elif not isinstance(estados, list):
            print(f"[WARNING] estados llegó como tipo {type(estados)}, convirtiendo a lista")
            estados = list(estados) if estados else []
    
    
    # Intentar obtener del caché
    cache_key = cache._make_key(
        "recepciones_mp",
        fecha_inicio, fecha_fin, productor_id or 0,
        solo_hechas, tuple(origen or []), tuple(estados or [])
    )
    
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    # No está en caché, calcular...
    
    # Mapeo de origen a picking_type_id
    ORIGEN_PICKING_MAP = {
        "RFP": 1,
        "VILKUN": 217,
        "SAN JOSE": 164  # ID correcto verificado en Odoo
    }
    
    # Determinar picking_type_ids a consultar
    if origen and len(origen) > 0:
        picking_type_ids = [ORIGEN_PICKING_MAP[o] for o in origen if o in ORIGEN_PICKING_MAP]
    else:
        picking_type_ids = [1, 217, 164]  # Todos por defecto
    
    if not picking_type_ids:
        picking_type_ids = [1, 217, 164]
    
    
    # ============ PASO 0.5: Identificar devoluciones y calcular kg devueltos por recepción ============
    # Buscar devoluciones para restar los kg devueltos de las recepciones originales
    PICKING_TYPES_DEVOLUCION = [2, 5, 3]  # IDs de devoluciones/salidas
    
    import re
    devoluciones_por_recepcion = {}  # {albaran_recepcion: [ids_devoluciones]}
    
    try:
        # Buscar devoluciones en un rango más amplio (desde 30 días antes hasta fecha_fin)
        from datetime import datetime, timedelta
        fecha_inicio_dt = datetime.fromisoformat(fecha_inicio.replace('Z', '+00:00'))
        fecha_busqueda_dev = (fecha_inicio_dt - timedelta(days=30)).strftime("%Y-%m-%d")
        
        devoluciones_domain = [
            ("picking_type_id", "in", PICKING_TYPES_DEVOLUCION),
            ("scheduled_date", ">=", fecha_busqueda_dev),
            ("scheduled_date", "<=", fecha_fin),
            ("state", "=", "done"),  # Solo devoluciones completadas
        ]
        
        devoluciones = client.search_read(
            "stock.picking",
            devoluciones_domain,
            ["id", "origin", "name", "state"],
            limit=5000
        )
        
        # Mapear devoluciones a sus recepciones originales
        for dev in devoluciones:
            origin = dev.get("origin", "")
            if origin:
                # El origin puede contener texto como "Retorno de RF/RFP/IN/01234"
                # o directamente "RF/RFP/IN/01234"
                # Extraer el nombre del picking usando regex
                match = re.search(r'(RF/[A-Z]+/IN/\d+|SNJ/INMP/\d+|Vilk/IN/\d+)', origin)
                if match:
                    albaran_original = match.group(1)
                    if albaran_original not in devoluciones_por_recepcion:
                        devoluciones_por_recepcion[albaran_original] = []
                    devoluciones_por_recepcion[albaran_original].append(dev["id"])
        
        print(f"[INFO] Se encontraron {len(devoluciones)} devoluciones completadas")
        print(f"[INFO] Recepciones con devoluciones: {len(devoluciones_por_recepcion)}")
        
    except Exception as e:
        print(f"[WARNING] Error buscando devoluciones: {e}")
        devoluciones_por_recepcion = {}
    
    # ============ PASO 1: Obtener todas las recepciones (EXCLUYENDO DEVOLUCIONES) ============
    # Las devoluciones tienen picking_type_id diferentes a los de recepción
    # IDs de picking_type para DEVOLUCIONES/SALIDAS que NO queremos incluir:
    # - Típicamente los picking_type con code='outgoing' o que sean devoluciones
    # Basándome en la estructura, excluiremos los IDs de picking_types de devolución
    # IDs comunes de devolución en Odoo: 2 (Devoluciones de clientes), 5 (Salidas OUT)
    # Nota: Esto puede variar según la instalación, ajustar según sea necesario
    
    domain = [
        ("picking_type_id", "in", picking_type_ids),
        ("picking_type_id", "not in", PICKING_TYPES_DEVOLUCION),  # EXCLUIR DEVOLUCIONES
        ("x_studio_categora_de_producto", "=", "MP"),
        ("scheduled_date", ">=", fecha_inicio),
        ("scheduled_date", "<=", fecha_fin),
    ]
    
    # Lógica de filtrado de estados
    if estados:
        domain.append(("state", "in", estados))
    elif solo_hechas:
        domain.append(("state", "=", "done"))
    
    # SIEMPRE excluir recepciones canceladas
    domain.append(("state", "!=", "cancel"))
        
    if productor_id:
        domain.append(("partner_id", "=", productor_id))
    
    recepciones = client.search_read(
        "stock.picking",
        domain,
        [
            "id", "name", "scheduled_date", "partner_id", 
            "x_studio_categora_de_producto",
            "x_studio_gua_de_despacho",
            "check_ids",
            "state",
            "picking_type_id",
            "origin"  # Orden de compra asociada
        ],
        limit=5000
    )
    
    # VALIDACIÓN CRÍTICA: Verificar que recepciones sea una lista de diccionarios
    if not recepciones:
        return []
    
    if not isinstance(recepciones, list):
        print(f"[ERROR CRÍTICO] recepciones no es una lista: {type(recepciones)}")
        raise TypeError(f"Se esperaba lista de recepciones, se recibió {type(recepciones)}")
    
    # Filtrar recepciones inválidas
    recepciones_validas = []
    for idx, r in enumerate(recepciones):
        if not isinstance(r, dict):
            print(f"[ERROR] Recepción #{idx} no es diccionario: {type(r)} - valor: {r}")
            continue
        if "id" not in r:
            print(f"[WARNING] Recepción #{idx} sin ID: {r}")
            continue
        recepciones_validas.append(r)
    
    if not recepciones_validas:
        print(f"[WARNING] No hay recepciones válidas después de filtrar")
        return []
    
    recepciones = recepciones_validas
    
    # Recolectar IDs para batch queries
    picking_ids = [r["id"] for r in recepciones]
    # all_check_ids REMOVIDO: Se buscará por picking_id
    
    # ============ PASO 2: Obtener TODOS los movimientos en UNA llamada ============
    # Incluir movimientos de recepciones Y devoluciones
    devolucion_ids = []
    for dev_list in devoluciones_por_recepcion.values():
        devolucion_ids.extend(dev_list)
    
    all_picking_ids = picking_ids + devolucion_ids
    
    moves = client.search_read(
        "stock.move",
        [("picking_id", "in", all_picking_ids)],
        ["picking_id", "product_id", "quantity_done", "product_uom", "price_unit"]
    )
    
    # Agrupar movimientos por picking_id
    moves_by_picking = {}
    all_product_ids = set()
    for m in moves:
        # VALIDACIÓN: Asegurar que m es un diccionario
        if not isinstance(m, dict):
            print(f"[WARNING] Movimiento no es diccionario, saltando: {type(m)}")
            continue
            
        pid = m.get("picking_id")
        if pid:
            picking_id = pid[0] if isinstance(pid, (list, tuple)) else pid
            if picking_id not in moves_by_picking:
                moves_by_picking[picking_id] = []
            moves_by_picking[picking_id].append(m)
            
            prod = m.get("product_id")
            if prod:
                prod_id = prod[0] if isinstance(prod, (list, tuple)) else prod
                all_product_ids.add(prod_id)
    
    # ============ PASO 3: Obtener TODOS los productos en UNA llamada ============
    product_info_map = {}
    template_ids = set()
    
    if all_product_ids:
        # Intentar obtener del caché
        cache_key = f"products_mp:{hash(tuple(sorted(all_product_ids)))}"
        cached = cache.get(cache_key)
        
        # VALIDACIÓN CRÍTICA: Verificar que el caché devuelve un diccionario
        if cached:
            if isinstance(cached, dict):
                product_info_map = cached
            else:
                print(f"[ERROR CRÍTICO] Caché de productos corrupto: se esperaba dict, se recibió {type(cached)}")
                print(f"[ERROR] Limpiando caché corrupto para key: {cache_key}")
                cache.invalidate(cache_key)  # Método correcto es invalidate(), no delete()
                cached = None  # Forzar recarga desde Odoo
        
        if not cached:
            product_infos = client.read(
                "product.product", 
                list(all_product_ids), 
                ["id", "product_tmpl_id", "categ_id"]
            )
            
            for p in product_infos:
                tmpl = p.get("product_tmpl_id")
                if tmpl:
                    tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
                    template_ids.add(tmpl_id)
            
            # Obtener templates con campo de manejo y tipo de fruta
            template_map = {}
            if template_ids:
                templates = client.read(
                    "product.template", 
                    list(template_ids), 
                    ["id", "name", "default_code", "x_studio_categora_tipo_de_manejo", "x_studio_sub_categora"]
                )
                for t in templates:
                    manejo = t.get("x_studio_categora_tipo_de_manejo", "")
                    # Si es tupla/lista (selection), tomar el valor legible
                    if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
                        manejo = manejo[1]
                    
                    # Tipo de fruta del producto (x_studio_sub_categora = "Categoría Tipo de Fruta")
                    tipo_fruta_prod = t.get("x_studio_sub_categora", "")
                    if isinstance(tipo_fruta_prod, (list, tuple)) and len(tipo_fruta_prod) > 1:
                        tipo_fruta_prod = tipo_fruta_prod[1]
                    
                    template_map[t["id"]] = {
                        "name": t.get("name", ""),
                        "default_code": t.get("default_code", "") or "",
                        "manejo": manejo or "",
                        "tipo_fruta": tipo_fruta_prod or ""
                    }

            
            # Mapear producto -> info completa
            for info in product_infos:
                pid = info.get("id")
                tmpl = info.get("product_tmpl_id")
                tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl if tmpl else None
                categ = info.get("categ_id", [None, ""])
                categ_name = categ[1] if isinstance(categ, (list, tuple)) else ""
                tmpl_data = template_map.get(tmpl_id, {})
                
                product_info_map[pid] = {
                    "categ": categ_name, 
                    "name": tmpl_data.get("name", ""),
                    "default_code": tmpl_data.get("default_code", ""),
                    "manejo": tmpl_data.get("manejo", ""),
                    "tipo_fruta": tmpl_data.get("tipo_fruta", "")
                }
            
            # VALIDACIÓN: Asegurar que product_info_map es un diccionario antes de cachear
            if not isinstance(product_info_map, dict):
                print(f"[ERROR CRÍTICO] product_info_map no es diccionario antes de cachear: {type(product_info_map)}")
                product_info_map = {}  # Resetear a diccionario vacío
            else:
                # Cachear productos por 30 minutos
                cache.set(cache_key, product_info_map, ttl=OdooCache.TTL_PRODUCTOS)
    
    checks_map = {}
    checks_by_picking = {}
    
    if picking_ids:
        # Requerimiento: Buscar quality.check asociados a estos pickings
        checks = client.search_read(
            "quality.check",
            [("picking_id", "in", picking_ids)],
            [
                "id", "picking_id",
                "quality_state",
                "x_studio_tipo_de_fruta",
                "x_studio_total_iqf_",
                "x_studio_total_block_",
                "x_studio_kg_recepcionados",
                "x_studio_gramos_de_la_muestra_1",
                "x_studio_totdaomecanico",
                "x_studio_tothongos_1",
                "x_studio_totinmadura",
                "x_studio_totsobremadura",
                "x_studio_totdaoinsecto_1",
                "x_studio_totdefectofrutilla",
                "x_studio_jefe_de_calidad_y_aseguramiento_",
                "x_studio_calific_final",
                "x_studio_frutilla",
                "x_studio_mp",
                "x_studio_frambuesa",
                "x_studio_one2many_field_rgA7I",
                "x_studio_one2many_field_mZmK2"
            ]
        )
        
        for c in checks:
            # VALIDACIÓN: Asegurar que c es un diccionario
            if not isinstance(c, dict):
                print(f"[WARNING] Check no es diccionario, saltando: {type(c)}")
                continue
                
            checks_map[c["id"]] = c
            picking = c.get("picking_id")
            if picking:
                pk_id = picking[0] if isinstance(picking, (list, tuple)) else picking
                if pk_id not in checks_by_picking:
                    checks_by_picking[pk_id] = []
                checks_by_picking[pk_id].append(c)
    
    # ============ PASO 5: Recolectar IDs de líneas de calidad por tipo ============
    lineas_frutilla_ids = []
    lineas_arandano_ids = []
    lineas_frambuesa_ids = []
    lineas_frambuesa_alt_ids = []
    
    for c in checks_map.values():
        tipo = c.get("x_studio_tipo_de_fruta", "")
        if tipo == "Frutilla":
            lineas_frutilla_ids.extend(c.get("x_studio_frutilla", []))
        elif tipo == "Arándano":
            lineas_arandano_ids.extend(c.get("x_studio_mp", []))
        elif tipo in ["Frambuesa", "Mora"]:
            ids_mZmK2 = c.get("x_studio_one2many_field_mZmK2", [])
            ids_rgA7I = c.get("x_studio_one2many_field_rgA7I", [])
            if ids_mZmK2:
                lineas_frambuesa_ids.extend(ids_mZmK2)
            elif ids_rgA7I:
                lineas_frambuesa_alt_ids.extend(ids_rgA7I)
    
    # ============ PASO 6: Obtener líneas de calidad en BATCH ============
    lineas_frutilla_map = {}
    lineas_arandano_map = {}
    lineas_frambuesa_map = {}
    lineas_frambuesa_alt_map = {}
    
    if lineas_frutilla_ids:
        lineas = client.search_read(
            "x_quality_check_line_89a53",
            [("id", "in", lineas_frutilla_ids)],
            ["id", "x_studio_fecha_y_hora", "x_studio_calificacion", "x_studio_total_defectos_",
             "x_studio_muestra_grs", "x_studio_n_palet", "x_studio_dao_mecanico",
             "x_studio_hongo", "x_studio_inmadura", "x_studio_sobremadurez",
             "x_studio_daos_por_insectos", "x_studio_deformesgrs", "x_studio_temperatura_c"]
        )
        for l in lineas:
            lineas_frutilla_map[l["id"]] = l
    
    if lineas_arandano_ids:
        lineas = client.search_read(
            "x_quality_check_line_19657",
            [("id", "in", lineas_arandano_ids)],
            ["id", "x_studio_fecha_y_hora", "x_studio_calificacion", "x_studio_total_defectos_",
             "x_studio_muestra", "x_studio_npalet_1", "x_studio_fruta_verde",
             "x_studio_hongos", "x_studio_frutos_con_decoloracin_e_inmaduros_y_frutos_rojos",
             "x_studio_frutos_con_sobre_madurez_y_exudacin", "x_studio_dao_por_insecto",
             "x_studio_deshidratado", "x_studio_heridapartidamolida", "x_studio_temperatura"]
        )
        for l in lineas:
            lineas_arandano_map[l["id"]] = l
    
    if lineas_frambuesa_ids:
        lineas = client.search_read(
            "x_quality_check_line_89a53",
            [("id", "in", lineas_frambuesa_ids)],
            ["id", "x_studio_fecha_y_hora", "x_studio_calificacion", "x_studio_total_defectos_",
             "x_studio_muestra_grs", "x_studio_n_palet", "x_studio_dao_mecanico",
             "x_studio_hongo", "x_studio_inmadura", "x_studio_sobremadurez",
             "x_studio_daos_por_insectos", "x_studio_deformesgrs", "x_studio_temperatura_c"]
        )
        for l in lineas:
            lineas_frambuesa_map[l["id"]] = l
    
    if lineas_frambuesa_alt_ids:
        lineas = client.search_read(
            "x_quality_check_line_1d183",
            [("id", "in", lineas_frambuesa_alt_ids)],
            ["id", "x_studio_hora_monitoreo", "x_studio_iqf", "x_studio_block",
             "x_studio_muestra", "x_studio_hongos", "x_studio_inmadura",
             "x_studio_sombremadura", "x_studio_deshidratado", "x_studio_crumble",
             "x_studio_t_prod_termin"]
        )
        for l in lineas:
            lineas_frambuesa_alt_map[l["id"]] = l
    
    # ============ PASO 7: Construir resultado final ============
    resultado = []
    
    for idx, rec in enumerate(recepciones):
        # VALIDACIÓN: Asegurar que rec es un diccionario
        if not isinstance(rec, dict):
            print(f"[ERROR] Recepción #{idx} en loop final no es diccionario: {type(rec)}")
            continue
        
        picking_id = rec.get("id")
        if not picking_id:
            print(f"[WARNING] Recepción #{idx} sin ID, saltando")
            continue
            
        productor = rec.get("partner_id", [None, ""])[1] if rec.get("partner_id") else ""
        
        # Excluir productor ADMINISTRADOR
        if productor.upper().strip() == 'ADMINISTRADOR':
            continue
        
        # Obtener albarán de la recepción
        albaran = rec.get("name", "")
        
        # Determinar origen basado en picking_type_id
        picking_type = rec.get("picking_type_id")
        picking_type_id_val = picking_type[0] if isinstance(picking_type, (list, tuple)) else picking_type
        
        # Aplicar override si existe (para corregir recepciones mal ingresadas en Odoo)
        if albaran in OVERRIDE_ORIGEN_PICKING:
            origen_rec = OVERRIDE_ORIGEN_PICKING[albaran]
        else:
            origen_rec = "RFP" if picking_type_id_val == 1 else "VILKUN" if picking_type_id_val == 217 else "SAN JOSE" if picking_type_id_val == 164 else "OTRO"
        
        fecha = rec.get("scheduled_date", "")
        
        # Procesar movimientos de este picking (recepción)
        # IMPORTANTE: Solo sumar movimientos en KG, no unidades (bandejas, etc)
        rec_moves = moves_by_picking.get(picking_id, [])
        kg_total_recepcion = 0
        for m in rec_moves:
            uom = m.get("product_uom")
            uom_name = uom[1].lower() if isinstance(uom, (list, tuple)) and len(uom) > 1 else "kg"
            # Solo sumar si es kg
            if uom_name == "kg":
                kg_total_recepcion += m.get("quantity_done", 0) or 0
        
        # Calcular kg devueltos (si existen devoluciones)
        # IMPORTANTE: Solo sumar movimientos en KG, no unidades
        kg_total_devuelto = 0
        if albaran in devoluciones_por_recepcion:
            for dev_id in devoluciones_por_recepcion[albaran]:
                dev_moves = moves_by_picking.get(dev_id, [])
                for dm in dev_moves:
                    duom = dm.get("product_uom")
                    duom_name = duom[1].lower() if isinstance(duom, (list, tuple)) and len(duom) > 1 else "kg"
                    # Solo sumar si es kg
                    if duom_name == "kg":
                        kg_total_devuelto += dm.get("quantity_done", 0) or 0
            
            if kg_total_devuelto > 0:
                print(f"[INFO] {albaran}: {kg_total_recepcion:.2f} kg recibidos - {kg_total_devuelto:.2f} kg devueltos = {kg_total_recepcion - kg_total_devuelto:.2f} kg netos")
        
        # Kg netos = kg recibidos - kg devueltos
        kg_total = kg_total_recepcion - kg_total_devuelto
        
        # Si después de la devolución no queda nada, excluir la recepción
        if kg_total <= 0:
            print(f"[INFO] Excluyendo {albaran}: devolución completa (0 kg netos)")
            continue
        
        # VALIDACIÓN CRÍTICA: Verificar que product_info_map es un diccionario
        if not isinstance(product_info_map, dict):
            print(f"[ERROR CRÍTICO] product_info_map es {type(product_info_map)} en lugar de dict. Reconstruyendo...")
            product_info_map = {}
        
        # Calcular kg devueltos por producto
        kg_devueltos_por_producto = {}
        if albaran in devoluciones_por_recepcion:
            for dev_id in devoluciones_por_recepcion[albaran]:
                dev_moves = moves_by_picking.get(dev_id, [])
                for dm in dev_moves:
                    if not isinstance(dm, dict):
                        continue
                    dprod = dm.get("product_id")
                    dprod_id = dprod[0] if isinstance(dprod, (list, tuple)) else dprod if dprod else None
                    if dprod_id:
                        kg_dev = dm.get("quantity_done", 0) or 0
                        kg_devueltos_por_producto[dprod_id] = kg_devueltos_por_producto.get(dprod_id, 0) + kg_dev
        
        productos = []
        for m in rec_moves:
            # VALIDACIÓN: Asegurar que m es un diccionario
            if not isinstance(m, dict):
                print(f"[WARNING] Movimiento en picking {picking_id} no es diccionario: {type(m)}")
                continue
                
            prod = m.get("product_id")
            prod_id = prod[0] if isinstance(prod, (list, tuple)) else prod if prod else None
            prod_info = product_info_map.get(prod_id, {})
            
            nombre = prod_info.get("name") or (prod[1] if isinstance(prod, (list, tuple)) else "")
            default_code = prod_info.get("default_code", "")
            nombre_prod = f"[{default_code}] {nombre}" if default_code else nombre
            
            kg_hechos_recepcion = m.get("quantity_done", 0) or 0
            kg_hechos_devueltos = kg_devueltos_por_producto.get(prod_id, 0)
            kg_hechos = kg_hechos_recepcion - kg_hechos_devueltos  # Kg netos
            
            costo_unit = m.get("price_unit", 0) or 0
            costo_total = kg_hechos * costo_unit  # Usar kg netos para el costo
            categoria = _normalize_categoria(prod_info.get("categ", ""))
            
            uom = m.get("product_uom")
            uom_name = uom[1] if isinstance(uom, (list, tuple)) else ""
            
            # Solo agregar productos con kg > 0 después de devoluciones
            if kg_hechos > 0:
                productos.append({
                    "Producto": nombre_prod,
                    "product_id": prod_id,
                    "Kg Hechos": kg_hechos,
                    "Costo Unitario": costo_unit,
                    "Costo Total": costo_total,
                    "UOM": uom_name,
                    "Categoria": categoria,
                    "Manejo": prod_info.get("manejo", ""),
                    "TipoFruta": prod_info.get("tipo_fruta", "")
                })
        
        # Procesar datos de calidad
        calidad_data = {
            "tipo_fruta": "",
            "total_iqf": 0,
            "total_block": 0,
            "kg_recepcionados_calidad": 0,
            "gramos_muestra": 0,
            "dano_mecanico": 0,
            "hongos": 0,
            "inmadura": 0,
            "sobremadura": 0,
            "dano_insecto": 0,
            "defecto_frutilla": 0,
            "fruta_verde": 0,
            "deshidratado": 0,
            "herida_partida": 0,
            "crumble": 0,
            "jefe_calidad": "",
            "calific_final": "",
            "quality_state": "",  # Estado del QC: none, pass, fail
            "lineas_analisis": []
        }
        
        checks_rec = checks_by_picking.get(picking_id, [])
        if checks_rec:
            qc = checks_rec[0] # Tomar el primer control de calidad encontrado
            tipo_fruta = qc.get("x_studio_tipo_de_fruta", "")
            
            calidad_data = {
                "tipo_fruta": tipo_fruta,
                "total_iqf": qc.get("x_studio_total_iqf_", 0) or 0,
                "total_block": qc.get("x_studio_total_block_", 0) or 0,
                "kg_recepcionados_calidad": qc.get("x_studio_kg_recepcionados", 0) or 0,
                "gramos_muestra": qc.get("x_studio_gramos_de_la_muestra_1", 0) or 0,
                "dano_mecanico": qc.get("x_studio_totdaomecanico", 0) or 0,
                "hongos": qc.get("x_studio_tothongos_1", 0) or 0,
                "inmadura": qc.get("x_studio_totinmadura", 0) or 0,
                "sobremadura": qc.get("x_studio_totsobremadura", 0) or 0,
                "dano_insecto": qc.get("x_studio_totdaoinsecto_1", 0) or 0,
                "defecto_frutilla": qc.get("x_studio_totdefectofrutilla", 0) or 0,
                # Estos campos no existen en quality.check, se calculan desde líneas de análisis
                "fruta_verde": 0,
                "deshidratado": 0,
                "herida_partida": 0,
                "crumble": 0,
                "jefe_calidad": qc.get("x_studio_jefe_de_calidad_y_aseguramiento_", ""),
                "calific_final": qc.get("x_studio_calific_final", ""),
                "quality_state": qc.get("quality_state", ""),  # none, pass, fail
                "lineas_analisis": []
            }
            
            # Procesar líneas de análisis según tipo
            lineas_analisis = []
            
            if tipo_fruta == "Frutilla":
                for lid in qc.get("x_studio_frutilla", []):
                    lin = lineas_frutilla_map.get(lid)
                    if lin:
                        lineas_analisis.append({
                            "fecha_hora": lin.get("x_studio_fecha_y_hora", ""),
                            "calificacion": lin.get("x_studio_calificacion", ""),
                            "total_defectos_pct": (lin.get("x_studio_total_defectos_", 0) or 0) * 100,
                            "n_palet": lin.get("x_studio_n_palet", 0) or 0,
                            "dano_mecanico": lin.get("x_studio_dao_mecanico", 0) or 0,
                            "hongos": lin.get("x_studio_hongo", 0) or 0,
                            "inmadura": lin.get("x_studio_inmadura", 0) or 0,
                            "sobremadura": lin.get("x_studio_sobremadurez", 0) or 0,
                            "dano_insecto": lin.get("x_studio_daos_por_insectos", 0) or 0,
                            "deformes": lin.get("x_studio_deformesgrs", 0) or 0,
                            "temperatura": lin.get("x_studio_temperatura_c", 0) or 0
                        })
            
            elif tipo_fruta == "Arándano":
                for lid in qc.get("x_studio_mp", []):
                    lin = lineas_arandano_map.get(lid)
                    if lin:
                        lineas_analisis.append({
                            "fecha_hora": lin.get("x_studio_fecha_y_hora", ""),
                            "calificacion": lin.get("x_studio_calificacion", ""),
                            "total_defectos_pct": (lin.get("x_studio_total_defectos_", 0) or 0) * 100,
                            "n_palet": lin.get("x_studio_npalet_1", 0) or 0,
                            "dano_mecanico": 0,
                            "hongos": lin.get("x_studio_hongos", 0) or 0,
                            "inmadura": lin.get("x_studio_frutos_con_decoloracin_e_inmaduros_y_frutos_rojos", 0) or 0,
                            "sobremadura": lin.get("x_studio_frutos_con_sobre_madurez_y_exudacin", 0) or 0,
                            "dano_insecto": lin.get("x_studio_dao_por_insecto", 0) or 0,
                            "deformes": 0,
                            "deshidratado": lin.get("x_studio_deshidratado", 0) or 0,
                            "herida_partida": lin.get("x_studio_heridapartidamolida", 0) or 0,
                            "fruta_verde": lin.get("x_studio_fruta_verde", 0) or 0,
                            "temperatura": lin.get("x_studio_temperatura", 0) or 0
                        })
            
            elif tipo_fruta in ["Frambuesa", "Mora"]:
                # Intentar primero mZmK2
                ids_mZmK2 = qc.get("x_studio_one2many_field_mZmK2", [])
                if ids_mZmK2:
                    for lid in ids_mZmK2:
                        lin = lineas_frambuesa_map.get(lid)
                        if lin:
                            lineas_analisis.append({
                                "fecha_hora": lin.get("x_studio_fecha_y_hora", ""),
                                "calificacion": lin.get("x_studio_calificacion", ""),
                                "total_defectos_pct": (lin.get("x_studio_total_defectos_", 0) or 0) * 100,
                                "n_palet": lin.get("x_studio_n_palet", 0) or 0,
                                "dano_mecanico": lin.get("x_studio_dao_mecanico", 0) or 0,
                                "hongos": lin.get("x_studio_hongo", 0) or 0,
                                "inmadura": lin.get("x_studio_inmadura", 0) or 0,
                                "sobremadura": lin.get("x_studio_sobremadurez", 0) or 0,
                                "dano_insecto": lin.get("x_studio_daos_por_insectos", 0) or 0,
                                "deformes": lin.get("x_studio_deformesgrs", 0) or 0,
                                "temperatura": lin.get("x_studio_temperatura_c", 0) or 0
                            })
                else:
                    # Fallback a rgA7I
                    for lid in qc.get("x_studio_one2many_field_rgA7I", []):
                        lin = lineas_frambuesa_alt_map.get(lid)
                        if lin:
                            iqf = lin.get("x_studio_iqf", 0) or 0
                            block = lin.get("x_studio_block", 0) or 0
                            calific = "IQF" if iqf > block else "BLOCK"
                            lineas_analisis.append({
                                "fecha_hora": lin.get("x_studio_hora_monitoreo", ""),
                                "calificacion": calific,
                                "total_defectos_pct": 0,
                                "n_palet": 0,
                                "dano_mecanico": 0,
                                "hongos": lin.get("x_studio_hongos", 0) or 0,
                                "inmadura": lin.get("x_studio_inmadura", 0) or 0,
                                "sobremadura": lin.get("x_studio_sombremadura", 0) or 0,
                                "dano_insecto": 0,
                                "deformes": 0,
                                "deshidratado": lin.get("x_studio_deshidratado", 0) or 0,
                                "crumble": lin.get("x_studio_crumble", 0) or 0,
                                "temperatura": lin.get("x_studio_t_prod_termin", 0) or 0
                            })
            
            calidad_data["lineas_analisis"] = lineas_analisis
            
            # Para tipos de fruta diferentes a Frutilla, calcular totales desde líneas de análisis
            # ya que Odoo no tiene campos de totales para estas frutas
            if tipo_fruta != "Frutilla" and lineas_analisis:
                # Sumar valores de todas las líneas
                sum_dano_mecanico = sum(l.get("dano_mecanico", 0) or 0 for l in lineas_analisis)
                sum_hongos = sum(l.get("hongos", 0) or 0 for l in lineas_analisis)
                sum_inmadura = sum(l.get("inmadura", 0) or 0 for l in lineas_analisis)
                sum_sobremadura = sum(l.get("sobremadura", 0) or 0 for l in lineas_analisis)
                sum_dano_insecto = sum(l.get("dano_insecto", 0) or 0 for l in lineas_analisis)
                sum_deshidratado = sum(l.get("deshidratado", 0) or 0 for l in lineas_analisis)
                sum_crumble = sum(l.get("crumble", 0) or 0 for l in lineas_analisis)
                sum_fruta_verde = sum(l.get("fruta_verde", 0) or 0 for l in lineas_analisis)
                sum_herida_partida = sum(l.get("herida_partida", 0) or 0 for l in lineas_analisis)
                
                # Actualizar calidad_data con los valores calculados
                calidad_data["dano_mecanico"] = sum_dano_mecanico
                calidad_data["hongos"] = sum_hongos
                calidad_data["inmadura"] = sum_inmadura
                calidad_data["sobremadura"] = sum_sobremadura
                calidad_data["dano_insecto"] = sum_dano_insecto
                calidad_data["deshidratado"] = sum_deshidratado
                calidad_data["crumble"] = sum_crumble
                calidad_data["fruta_verde"] = sum_fruta_verde
                calidad_data["herida_partida"] = sum_herida_partida
        
        # ============ FALLBACK: Si no hay tipo_fruta del QC, obtener del producto ============
        if not calidad_data["tipo_fruta"] and productos:
            # Buscar el primer producto válido (no bandeja) que tenga TipoFruta
            for p in productos:
                categoria_p = (p.get("Categoria") or "").upper()
                if "BANDEJ" in categoria_p:
                    continue
                tipo_fruta_producto = (p.get("TipoFruta") or "").strip()
                if tipo_fruta_producto:
                    calidad_data["tipo_fruta"] = tipo_fruta_producto
                    break
        
        resultado.append({
            "id": picking_id,
            "albaran": albaran,
            "fecha": fecha,
            "productor": productor,
            "guia_despacho": rec.get("x_studio_gua_de_despacho", ""),
            "oc_asociada": rec.get("origin", ""),  # Orden de compra asociada
            "kg_recepcionados": kg_total if kg_total > 0 else calidad_data["kg_recepcionados_calidad"],
            "state": rec.get("state", ""),
            "origen": origen_rec,
            "calific_final": calidad_data["calific_final"],
            "quality_state": calidad_data["quality_state"],  # Estado del QC: none, pass, fail
            "tipo_fruta": calidad_data["tipo_fruta"],
            "total_iqf": calidad_data["total_iqf"],
            "total_block": calidad_data["total_block"],
            "gramos_muestra": calidad_data["gramos_muestra"],
            "dano_mecanico": calidad_data["dano_mecanico"],
            "hongos": calidad_data["hongos"],
            "inmadura": calidad_data["inmadura"],
            "sobremadura": calidad_data["sobremadura"],
            "dano_insecto": calidad_data["dano_insecto"],
            "defecto_frutilla": calidad_data["defecto_frutilla"],
            "fruta_verde": calidad_data["fruta_verde"],
            "deshidratado": calidad_data["deshidratado"],
            "herida_partida": calidad_data["herida_partida"],
            "crumble": calidad_data["crumble"],
            "jefe_calidad": calidad_data["jefe_calidad"],
            "productos": productos,
            "lineas_analisis": calidad_data.get("lineas_analisis", [])
        })
    
    # Guardar en caché con TTL de 300 segundos (5 minutos)
    cache.set(cache_key, resultado, ttl=300)
    
    return resultado

def validar_recepciones(username: str, password: str, picking_ids: List[int]) -> Dict[str, Any]:
    """
    Valida masivamente un conjunto de recepciones en Odoo (método button_validate).
    """
    client = OdooClient(username=username, password=password)
    success_ids = []
    error_ids = []
    errors = []

    for pid in picking_ids:
        try:
            # En Odoo, button_validate suele retornar True o un dict de acción (ej. wizard)
            res = client.execute("stock.picking", "button_validate", [pid])
            
            # Si retorna un dict con 'res_model', probablemente lanzó un wizard (ej. stock.immediate.transfer)
            # Para simplificar en este dashboard, si lanza wizard, podrías intentar 'process'
            if isinstance(res, dict) and res.get('res_model') == 'stock.immediate.transfer':
                # Esto es común si no se han marcado cantidades. 
                # Intentamos procesar el wizard automáticamente si es necesario.
                # Pero por ahora probamos el llamado básico.
                pass

            success_ids.append(pid)
        except Exception as e:
            error_ids.append(pid)
            errors.append(f"Error en {pid}: {str(e)}")
            print(f"[ERROR] Validando picking {pid}: {e}")

    return {
        "success": len(error_ids) == 0,
        "validados": success_ids,
        "errores": errors,
        "n_error": len(error_ids)
    }

def get_recepciones_pallets(username: str, password: str, fecha_inicio: str, fecha_fin: str, 
                             manejo_filtros: Optional[List[str]] = None, 
                             tipo_fruta_filtros: Optional[List[str]] = None,
                             origen_filtros: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Obtiene la cantidad de pallets y total kg por recepción de MP.
    """
    client = OdooClient(username=username, password=password)
    
    # Mapeo de origen a picking_type_id
    ORIGEN_PICKING_MAP = {
        "RFP": 1,
        "VILKUN": 217,
        "SAN JOSE": 164  # ID correcto verificado en Odoo
    }
    
    # Determinar picking_type_ids a consultar
    if origen_filtros:
        picking_type_ids = [ORIGEN_PICKING_MAP[o] for o in origen_filtros if o in ORIGEN_PICKING_MAP]
    else:
        picking_type_ids = [1, 217, 164]
        
    if not picking_type_ids:
        picking_type_ids = [1, 217, 164]

    # 0. Identificar recepciones IN con devoluciones asociadas
    PICKING_TYPES_DEVOLUCION = [2, 5, 3]  # IDs de devoluciones/salidas a excluir
    
    try:
        devoluciones_domain = [
            ("picking_type_id", "in", PICKING_TYPES_DEVOLUCION),
            ("scheduled_date", ">=", fecha_inicio),
            ("scheduled_date", "<=", fecha_fin + " 23:59:59"),
        ]
        
        devoluciones = client.search_read(
            "stock.picking",
            devoluciones_domain,
            ["id", "origin", "name"],
            limit=5000
        )
        
        recepciones_con_devolucion = set()
        for dev in devoluciones:
            origin = dev.get("origin", "")
            if origin:
                recepciones_con_devolucion.add(origin)
        
        print(f"[INFO PALLETS] Se encontraron {len(devoluciones)} devoluciones")
        print(f"[INFO PALLETS] Recepciones con devolución a excluir: {len(recepciones_con_devolucion)}")
        
    except Exception as e:
        print(f"[WARNING] Error buscando devoluciones en pallets: {e}")
        recepciones_con_devolucion = set()

    # 1. Buscar pickings de MP en el rango (solo validados, EXCLUYENDO DEVOLUCIONES)
    
    domain = [
        ("picking_type_id", "in", picking_type_ids),
        ("picking_type_id", "not in", PICKING_TYPES_DEVOLUCION),  # EXCLUIR DEVOLUCIONES
        ("x_studio_categora_de_producto", "=", "MP"),
        ("scheduled_date", ">=", fecha_inicio),
        ("scheduled_date", "<=", fecha_fin + " 23:59:59"),
        ("state", "=", "done")
    ]
    
    pickings = client.search_read(
        "stock.picking",
        domain,
        ["id", "name", "scheduled_date", "partner_id", "x_studio_gua_de_despacho", "picking_type_id"],
        order="scheduled_date desc",
        limit=2000
    )
    
    if not pickings:
        return []
    
    # Filtrar pickings que tienen devoluciones asociadas
    pickings_filtrados = []
    for p in pickings:
        albaran = p.get("name", "")
        if albaran not in recepciones_con_devolucion:
            pickings_filtrados.append(p)
        else:
            print(f"[INFO PALLETS] Excluyendo picking {albaran} porque tiene devolución")
    
    pickings = pickings_filtrados
    
    if not pickings:
        return []
        
    picking_ids = [p["id"] for p in pickings]
    
    # 2. Obtener todas las líneas de movimiento (move lines) en batch
    move_lines = client.search_read(
        "stock.move.line",
        [("picking_id", "in", picking_ids)],
        ["picking_id", "product_id", "qty_done", "result_package_id"]
    )
    
    # 3. Obtener info de productos
    all_product_ids = list(set(ml["product_id"][0] for ml in move_lines if ml.get("product_id")))
    product_info = {}
    
    if all_product_ids:
        products = client.read("product.product", all_product_ids, ["id", "product_tmpl_id"])
        template_ids = list(set(p["product_tmpl_id"][0] for p in products if p.get("product_tmpl_id")))
        
        templates = client.read(
            "product.template", 
            template_ids, 
            ["id", "x_studio_categora_tipo_de_manejo", "x_studio_sub_categora"]
        )
        
        template_map = {}
        for t in templates:
            manejo = t.get("x_studio_categora_tipo_de_manejo", "")
            if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
                manejo = manejo[1]
            
            tipo_fruta = t.get("x_studio_sub_categora", "")
            if isinstance(tipo_fruta, (list, tuple)) and len(tipo_fruta) > 1:
                tipo_fruta = tipo_fruta[1]
                
            template_map[t["id"]] = {
                "manejo": manejo or "N/A",
                "tipo_fruta": tipo_fruta or "N/A"
            }
            
        for p in products:
            tmpl_id = p["product_tmpl_id"][0] if p.get("product_tmpl_id") else None
            product_info[p["id"]] = template_map.get(tmpl_id, {"manejo": "N/A", "tipo_fruta": "N/A"})

    # 4. Agrupar y filtrar
    ml_by_picking = {}
    for ml in move_lines:
        pk_id = ml["picking_id"][0]
        if pk_id not in ml_by_picking:
            ml_by_picking[pk_id] = []
        ml_by_picking[pk_id].append(ml)
        
    resultado = []
    for p in pickings:
        p_ml = ml_by_picking.get(p["id"], [])
        
        # Determinar planta
        pt_id = p.get("picking_type_id", [0, ""])
        pt_id_val = pt_id[0] if isinstance(pt_id, (list, tuple)) else pt_id
        albaran = p.get("name", "")
        
        # Aplicar override si existe (para corregir recepciones mal ingresadas en Odoo)
        if albaran in OVERRIDE_ORIGEN_PICKING:
            origen_val = OVERRIDE_ORIGEN_PICKING[albaran]
        else:
            origen_val = "RFP" if pt_id_val == 1 else "VILKUN" if pt_id_val == 217 else "SAN JOSE" if pt_id_val == 164 else "OTRO"

        # Enriquecer líneas con info de producto
        filtered_ml = []
        for ml in p_ml:
            p_id = ml["product_id"][0] if ml.get("product_id") else None
            info = product_info.get(p_id, {"manejo": "N/A", "tipo_fruta": "N/A"})
            
            # Filtros
            if manejo_filtros and info["manejo"] not in manejo_filtros:
                continue
            if tipo_fruta_filtros and info["tipo_fruta"] not in tipo_fruta_filtros:
                continue
                
            ml["manejo"] = info["manejo"]
            ml["tipo_fruta"] = info["tipo_fruta"]
            filtered_ml.append(ml)
            
        if not filtered_ml:
            continue
            
        total_kg = sum(ml.get("qty_done", 0) or 0 for ml in filtered_ml)
        packages = set()
        for ml in filtered_ml:
            pkg = ml.get("result_package_id")
            if pkg:
                pkg_id = pkg[0]
                packages.add(pkg_id)
        
        cantidad_pallets = len(packages)
        manejos_presentes = list(set(ml["manejo"] for ml in filtered_ml))
        frutas_presentes = list(set(ml["tipo_fruta"] for ml in filtered_ml))
        
        guia = p.get("x_studio_gua_de_despacho") or ""
        
        resultado.append({
            "id": p["id"],
            "albaran": p["name"],
            "fecha": str(p["scheduled_date"])[:10],
            "productor": p["partner_id"][1] if p.get("partner_id") else "N/A",
            "guia_despacho": guia,
            "cantidad_pallets": cantidad_pallets,
            "total_kg": round(total_kg, 2),
            "manejo": ", ".join(manejos_presentes),
            "tipo_fruta": ", ".join(frutas_presentes),
            "origen": origen_val
        })
    
    # Identificar guías duplicadas (mismo número de guía Y mismo productor)
    guias_productor_count = {}
    for item in resultado:
        guia = item["guia_despacho"]
        productor = item["productor"]
        if guia and productor:  # Solo contar si ambos campos tienen valor
            # Crear clave compuesta (guía, productor)
            clave = (guia, productor)
            guias_productor_count[clave] = guias_productor_count.get(clave, 0) + 1
    
    # Marcar duplicados y agregar URL de Odoo
    odoo_url = client.url  # URL base de Odoo
    for item in resultado:
        guia = item["guia_despacho"]
        productor = item["productor"]
        # Marcar si la combinación (guía, productor) está duplicada
        if guia and productor:
            clave = (guia, productor)
            item["es_duplicada"] = guias_productor_count.get(clave, 0) > 1
        else:
            item["es_duplicada"] = False
        
        # Agregar URL para ir directamente al registro en Odoo
        # Formato universal: primero el modelo, luego el ID
        # Este formato es compatible con todas las versiones de Odoo
        item["odoo_url"] = f"{odoo_url}/web#model=stock.picking&id={item['id']}"
        
    return resultado



def get_recepciones_pallets_detailed(username: str, password: str, fecha_inicio: str, fecha_fin: str, 
                                      manejo_filtros: Optional[List[str]] = None, 
                                      tipo_fruta_filtros: Optional[List[str]] = None,
                                      origen_filtros: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Retorna una lista donde cada elemento es UN PALLET (un package), con su info de recepción.
    Usado para generar el Excel detallado.
    """
    client = OdooClient(username=username, password=password)
    
    # Mapeo de origen a picking_type_id
    ORIGEN_PICKING_MAP = {
        "RFP": 1,
        "VILKUN": 217,
        "SAN JOSE": 164  # ID correcto verificado en Odoo
    }
    
    # Determinar picking_type_ids a consultar
    if origen_filtros:
        if isinstance(origen_filtros, str):
            origen_filtros = [origen_filtros]
        picking_type_ids = [ORIGEN_PICKING_MAP[o] for o in origen_filtros if o in ORIGEN_PICKING_MAP]
    else:
        picking_type_ids = [1, 217, 164]
        
    if not picking_type_ids:
        picking_type_ids = [1, 217, 164]

    # 0. Identificar recepciones IN con devoluciones asociadas
    PICKING_TYPES_DEVOLUCION = [2, 5, 3]  # IDs de devoluciones/salidas a excluir
    
    try:
        devoluciones_domain = [
            ("picking_type_id", "in", PICKING_TYPES_DEVOLUCION),
            ("scheduled_date", ">=", fecha_inicio),
            ("scheduled_date", "<=", fecha_fin + " 23:59:59"),
        ]
        
        devoluciones = client.search_read(
            "stock.picking",
            devoluciones_domain,
            ["id", "origin", "name"],
            limit=5000
        )
        
        recepciones_con_devolucion = set()
        for dev in devoluciones:
            origin = dev.get("origin", "")
            if origin:
                recepciones_con_devolucion.add(origin)
        
        print(f"[INFO DETAILED] Se encontraron {len(devoluciones)} devoluciones")
        print(f"[INFO DETAILED] Recepciones con devolución a excluir: {len(recepciones_con_devolucion)}")
        
    except Exception as e:
        print(f"[WARNING] Error buscando devoluciones en detailed: {e}")
        recepciones_con_devolucion = set()

    domain = [
        ("picking_type_id", "in", picking_type_ids),
        ("picking_type_id", "not in", PICKING_TYPES_DEVOLUCION),  # EXCLUIR DEVOLUCIONES
        ("x_studio_categora_de_producto", "=", "MP"),
        ("scheduled_date", ">=", fecha_inicio),
        ("scheduled_date", "<=", fecha_fin + " 23:59:59"),
        ("state", "=", "done")
    ]
    
    pickings = client.search_read(
        "stock.picking",
        domain,
        ["id", "name", "scheduled_date", "partner_id", "x_studio_gua_de_despacho", "picking_type_id"],
        order="scheduled_date desc",
        limit=2000
    )
    
    if not pickings:
        return []
    
    # Filtrar pickings que tienen devoluciones asociadas
    pickings_filtrados = []
    for p in pickings:
        albaran = p.get("name", "")
        if albaran not in recepciones_con_devolucion:
            pickings_filtrados.append(p)
        else:
            print(f"[INFO DETAILED] Excluyendo picking {albaran} porque tiene devolución")
    
    pickings = pickings_filtrados
    
    if not pickings:
        return []
        
    picking_ids = [p["id"] for p in pickings]
    picking_map = {p["id"]: p for p in pickings}
    
    # Obtener move lines
    move_lines = client.search_read(
        "stock.move.line",
        [("picking_id", "in", picking_ids)],
        ["picking_id", "product_id", "qty_done", "result_package_id"]
    )
    
    # Info de productos
    all_product_ids = list(set(ml["product_id"][0] for ml in move_lines if ml.get("product_id")))
    product_info = {}
    
    if all_product_ids:
        products = client.read("product.product", all_product_ids, ["id", "product_tmpl_id", "display_name"])
        template_ids = list(set(p["product_tmpl_id"][0] for p in products if p.get("product_tmpl_id")))
        
        templates = client.read(
            "product.template", 
            template_ids, 
            ["id", "x_studio_categora_tipo_de_manejo", "x_studio_sub_categora"]
        )
        
        template_map = {}
        for t in templates:
            manejo = t.get("x_studio_categora_tipo_de_manejo", "")
            if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
                manejo = manejo[1]
            tipo_fruta = t.get("x_studio_sub_categora", "")
            if isinstance(tipo_fruta, (list, tuple)) and len(tipo_fruta) > 1:
                tipo_fruta = tipo_fruta[1]
            
            template_map[t["id"]] = {
                "manejo": manejo or "N/A",
                "tipo_fruta": tipo_fruta or "N/A"
            }
            
        for p in products:
            tmpl_id = p["product_tmpl_id"][0] if p.get("product_tmpl_id") else None
            info = template_map.get(tmpl_id, {"manejo": "N/A", "tipo_fruta": "N/A"})
            info["display_name"] = p.get("display_name", "")
            product_info[p["id"]] = info

    resultado = []
    
    for ml in move_lines:
        pk_id = ml["picking_id"][0] if ml.get("picking_id") else None
        if not pk_id:
            continue
        p = picking_map.get(pk_id)
        if not p:
            continue
        
        p_id = ml["product_id"][0] if ml.get("product_id") else None
        info = product_info.get(p_id, {"manejo": "N/A", "tipo_fruta": "N/A", "display_name": ""})
        
        # Filtros
        if manejo_filtros and info["manejo"] not in manejo_filtros:
            continue
        if tipo_fruta_filtros and info["tipo_fruta"] not in tipo_fruta_filtros:
            continue
            
        # Determinar planta
        pt_id_val = p["picking_type_id"][0] if isinstance(p["picking_type_id"], (list, tuple)) else p["picking_type_id"]
        albaran = p.get("name", "")
        
        # Aplicar override si existe (para corregir recepciones mal ingresadas en Odoo)
        if albaran in OVERRIDE_ORIGEN_PICKING:
            origen_val = OVERRIDE_ORIGEN_PICKING[albaran]
        else:
            origen_val = "RFP" if pt_id_val == 1 else "VILKUN" if pt_id_val == 217 else "SAN JOSE" if pt_id_val == 164 else "OTRO"
        
        # Pallet (Package)
        pkg = ml.get("result_package_id")
        pallet_name = pkg[1] if isinstance(pkg, (list, tuple)) else str(pkg) if pkg else "S/P"

        resultado.append({
            "fecha": str(p["scheduled_date"])[:10],
            "origen": origen_val,
            "albaran": p["name"],
            "productor": p["partner_id"][1] if p.get("partner_id") else "N/A",
            "guia_despacho": p.get("x_studio_gua_de_despacho") or "",
            "pallet_name": pallet_name,
            "producto_name": info["display_name"],
            "manejo": info["manejo"],
            "tipo_fruta": info["tipo_fruta"],
            "kg": round(ml.get("qty_done", 0) or 0, 2)
        })
        
    return resultado
