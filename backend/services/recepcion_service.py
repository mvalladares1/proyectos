"""
Servicio para consultar recepciones de materia prima (MP) desde Odoo
OPTIMIZADO: Usa batch queries para eliminar problema N+1
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


def get_recepciones_mp(username: str, password: str, fecha_inicio: str, fecha_fin: str, productor_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Obtiene recepciones de materia prima con datos de calidad.
    
    OPTIMIZADO: Reduce de ~5 llamadas por recepción a ~6 llamadas totales:
    1. stock.picking (recepciones)
    2. stock.move (todos los movimientos)
    3. product.product (todos los productos)
    4. product.template (todos los templates)
    5. quality.check (todos los checks)
    6. x_quality_check_line_* (líneas por tipo)
    """
    client = OdooClient(username=username, password=password)
    cache = get_cache()
    
    # ============ PASO 1: Obtener todas las recepciones ============
    # IMPORTANTE: Solo recepciones en estado "done" (validadas/hechas)
    domain = [
        ("picking_type_id", "=", 1),
        ("x_studio_categora_de_producto", "=", "MP"),
        ("scheduled_date", ">=", fecha_inicio),
        ("scheduled_date", "<=", fecha_fin),
        ("state", "=", "done")  # Solo recepciones completadas/validadas
    ]
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
            "state"
        ]
    )
    
    if not recepciones:
        return []
    
    # Recolectar IDs para batch queries
    picking_ids = [r["id"] for r in recepciones]
    all_check_ids = []
    for r in recepciones:
        all_check_ids.extend(r.get("check_ids", []))
    
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
            
            # Obtener templates con campo de manejo
            template_map = {}
            if template_ids:
                templates = client.read(
                    "product.template", 
                    list(template_ids), 
                    ["id", "name", "default_code", "x_studio_categora_tipo_de_manejo"]
                )
                for t in templates:
                    manejo = t.get("x_studio_categora_tipo_de_manejo", "")
                    # Si es tupla/lista (selection), tomar el valor legible
                    if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
                        manejo = manejo[1]
                    template_map[t["id"]] = {
                        "name": t.get("name", ""),
                        "default_code": t.get("default_code", "") or "",
                        "manejo": manejo or ""
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
                    "manejo": tmpl_data.get("manejo", "")
                }
            
            # Cachear productos por 30 minutos
            cache.set(cache_key, product_info_map, ttl=OdooCache.TTL_PRODUCTOS)
    
    # ============ PASO 4: Obtener TODOS los quality.check en UNA llamada ============
    checks_map = {}
    checks_by_picking = {}
    
    if all_check_ids:
        checks = client.search_read(
            "quality.check",
            [("id", "in", all_check_ids)],
            [
                "id", "picking_id",
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
                "Manejo": prod_info.get("manejo", "")
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
            "jefe_calidad": "",
            "calific_final": "",
            "lineas_analisis": []
        }
        
        check_ids = rec.get("check_ids", [])
        if check_ids and check_ids[0] in checks_map:
            qc = checks_map[check_ids[0]]
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
                "jefe_calidad": qc.get("x_studio_jefe_de_calidad_y_aseguramiento_", ""),
                "calific_final": qc.get("x_studio_calific_final", ""),
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
        
        resultado.append({
            "id": picking_id,
            "albaran": albaran,
            "fecha": fecha,
            "productor": productor,
            "guia_despacho": rec.get("x_studio_gua_de_despacho", ""),
            "kg_recepcionados": kg_total if kg_total > 0 else calidad_data["kg_recepcionados_calidad"],
            "state": rec.get("state", ""),
            "calific_final": calidad_data["calific_final"],
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
            "jefe_calidad": calidad_data["jefe_calidad"],
            "productos": productos,
            "lineas_analisis": calidad_data.get("lineas_analisis", [])
        })
    
    return resultado
