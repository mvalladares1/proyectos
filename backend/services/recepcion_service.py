"""
Servicio para consultar recepciones de materia prima (MP) desde Odoo
OPTIMIZADO: Usa batch queries para eliminar problema N+1 + Caché de 5 minutos
Migrado desde recepcion/backend/recepcion_service.py
"""
from typing import List, Dict, Any, Optional
from shared.odoo_client import OdooClient
from backend.cache import get_cache, OdooCache


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
    
    # DEBUG: Log parámetros normalizados
    print(f"[DEBUG recepcion_service] origen (normalizado): {origen}, tipo: {type(origen)}")
    print(f"[DEBUG recepcion_service] estados (normalizado): {estados}, tipo: {type(estados)}")
    
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
        "VILKUN": 217
    }
    
    # DEBUG: Log the origen parameter received
    print(f"[DEBUG recepcion_service] origen recibido: {origen}, tipo: {type(origen)}")
    
    # Determinar picking_type_ids a consultar
    if origen and len(origen) > 0:
        picking_type_ids = [ORIGEN_PICKING_MAP[o] for o in origen if o in ORIGEN_PICKING_MAP]
    else:
        picking_type_ids = [1, 217]  # Ambos por defecto
    
    if not picking_type_ids:
        picking_type_ids = [1, 217]
    
    # DEBUG: Log the picking_type_ids being used
    print(f"[DEBUG recepcion_service] picking_type_ids a usar: {picking_type_ids}")
    
    # ============ PASO 1: Obtener todas las recepciones ============
    domain = [
        ("picking_type_id", "in", picking_type_ids),
        ("x_studio_categora_de_producto", "=", "MP"),
        ("scheduled_date", ">=", fecha_inicio),
        ("scheduled_date", "<=", fecha_fin),
    ]
    
    # Lógica de filtrado de estados
    if estados:
        domain.append(("state", "in", estados))
    elif solo_hechas:
        domain.append(("state", "=", "done"))
        
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
    
    if not recepciones:
        return []
    
    # Recolectar IDs para batch queries
    picking_ids = [r["id"] for r in recepciones]
    # all_check_ids REMOVIDO: Se buscará por picking_id
    
    # ============ PASO 2: Obtener TODOS los movimientos en UNA llamada ============
    moves = client.search_read(
        "stock.move",
        [("picking_id", "in", picking_ids)],
        ["picking_id", "product_id", "quantity_done", "product_uom", "price_unit"]
    )
    
    # Agrupar movimientos por picking_id
    moves_by_picking = {}
    all_product_ids = set()
    for m in moves:
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
        
        if cached:
            product_info_map = cached
        else:
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
    
    for rec in recepciones:
        picking_id = rec.get("id")
        productor = rec.get("partner_id", [None, ""])[1] if rec.get("partner_id") else ""
        
        # Excluir productor ADMINISTRADOR
        if productor.upper().strip() == 'ADMINISTRADOR':
            continue
        
        # Determinar origen basado en picking_type_id
        picking_type = rec.get("picking_type_id")
        picking_type_id_val = picking_type[0] if isinstance(picking_type, (list, tuple)) else picking_type
        origen_rec = "RFP" if picking_type_id_val == 1 else "VILKUN" if picking_type_id_val == 217 else "OTRO"
        
        fecha = rec.get("scheduled_date", "")
        albaran = rec.get("name", "")
        
        # Procesar movimientos de este picking
        rec_moves = moves_by_picking.get(picking_id, [])
        kg_total = sum(m.get("quantity_done", 0) or 0 for m in rec_moves)
        
        productos = []
        for m in rec_moves:
            prod = m.get("product_id")
            prod_id = prod[0] if isinstance(prod, (list, tuple)) else prod if prod else None
            prod_info = product_info_map.get(prod_id, {})
            
            nombre = prod_info.get("name") or (prod[1] if isinstance(prod, (list, tuple)) else "")
            default_code = prod_info.get("default_code", "")
            nombre_prod = f"[{default_code}] {nombre}" if default_code else nombre
            
            kg_hechos = m.get("quantity_done", 0) or 0
            costo_unit = m.get("price_unit", 0) or 0
            costo_total = kg_hechos * costo_unit
            categoria = _normalize_categoria(prod_info.get("categ", ""))
            
            uom = m.get("product_uom")
            uom_name = uom[1] if isinstance(uom, (list, tuple)) else ""
            
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
