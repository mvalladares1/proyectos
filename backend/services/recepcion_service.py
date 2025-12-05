"""
Servicio para consultar recepciones de materia prima (MP) desde Odoo
Migrado desde recepcion/backend/recepcion_service.py
"""
from typing import List, Dict, Any, Optional
from shared.odoo_client import OdooClient


def get_recepciones_mp(username: str, password: str, fecha_inicio: str, fecha_fin: str, productor_id: Optional[int] = None) -> List[Dict[str, Any]]:
    client = OdooClient(username=username, password=password)
    # Buscar recepciones MP en stock.picking
    domain = [
        ("picking_type_id", "=", 1),  # Recepciones MP
        ("x_studio_categora_de_producto", "=", "MP"),
        ("scheduled_date", ">=", fecha_inicio),
        ("scheduled_date", "<=", fecha_fin)
    ]
    if productor_id:
        domain.append(("partner_id", "=", productor_id))
    
    # Campos que existen en stock.picking según exploración
    recepciones = client.search_read(
        "stock.picking",
        domain,
        [
            "id", "name", "scheduled_date", "partner_id", 
            "x_studio_categora_de_producto",
            "x_studio_gua_de_despacho",
            "check_ids",  # IDs de quality.check
            "state"
        ]
    )
    
    # Procesar recepciones
    resultado = []
    for rec in recepciones:
        productor = rec.get("partner_id", [None, ""])[1] if rec.get("partner_id") else ""
        fecha = rec.get("scheduled_date", "")
        albaran = rec.get("name", "")
        picking_id = rec.get("id")
        
        # Obtener los movimientos (stock.move) para sumar los Kg y extraer productos
        moves = client.search_read(
            "stock.move",
            [("picking_id", "=", picking_id)],
            ["product_id", "quantity_done", "product_uom", "price_unit"]
        )
        # Obtener categorías de productos
        product_ids = [m.get("product_id", [None, None])[0] for m in moves if m.get("product_id")]
        product_categs = {}
        if product_ids:
            product_infos = client.read("product.product", product_ids, ["id", "categ_id"])
            for info in product_infos:
                pid = info.get("id")
                categ = info.get("categ_id", [None, ""])[1] if info.get("categ_id") else ""
                product_categs[pid] = categ

        kg_total = sum(m.get("quantity_done", 0) or 0 for m in moves)
        productos = []
        for m in moves:
            prod_id = m.get("product_id", [None, None])[0] if m.get("product_id") else None
            nombre_prod = m.get("product_id", [None, ""])[1] if m.get("product_id") else ""
            kg_hechos = m.get("quantity_done", 0) or 0
            costo_unit = m.get("price_unit", 0) or 0
            costo_total = kg_hechos * costo_unit
            categoria = product_categs.get(prod_id, "")
            productos.append({
                "Producto": nombre_prod,
                "Kg Hechos": kg_hechos,
                "Costo Unitario": costo_unit,
                "Costo Total": costo_total,
                "UOM": m.get("product_uom", [None, ""])[1] if m.get("product_uom") else "",
                "Categoria": categoria
            })

        # Obtener datos de calidad desde quality.check
        check_ids = rec.get("check_ids", [])
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
        if check_ids:
            checks = client.search_read(
                "quality.check",
                [("id", "in", check_ids)],
                [
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
                    "x_studio_frutilla",  # Líneas Frutilla
                    "x_studio_mp",  # Líneas Arándano (MP)
                    "x_studio_frambuesa",  # Líneas Frambuesa
                    "x_studio_one2many_field_rgA7I",  # Líneas Frambuesa/Mora alternativo
                    "x_studio_one2many_field_mZmK2"  # Líneas Frambuesa (otro campo)
                ]
            )
            if checks:
                qc = checks[0]
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
                    "calific_final": qc.get("x_studio_calific_final", "")
                }
                
                # Obtener líneas de análisis según el tipo de fruta
                lineas_analisis = []
                
                if tipo_fruta == "Frutilla":
                    linea_ids = qc.get("x_studio_frutilla", [])
                    if linea_ids:
                        lineas = client.search_read(
                            "x_quality_check_line_89a53",
                            [("id", "in", linea_ids)],
                            ["x_studio_fecha_y_hora", "x_studio_calificacion", "x_studio_total_defectos_",
                             "x_studio_muestra_grs", "x_studio_n_palet", "x_studio_dao_mecanico",
                             "x_studio_hongo", "x_studio_inmadura", "x_studio_sobremadurez",
                             "x_studio_daos_por_insectos", "x_studio_deformesgrs", "x_studio_temperatura_c"]
                        )
                        for lin in lineas:
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
                    linea_ids = qc.get("x_studio_mp", [])
                    if linea_ids:
                        lineas = client.search_read(
                            "x_quality_check_line_19657",
                            [("id", "in", linea_ids)],
                            ["x_studio_fecha_y_hora", "x_studio_calificacion", "x_studio_total_defectos_",
                             "x_studio_muestra", "x_studio_npalet_1", "x_studio_fruta_verde",
                             "x_studio_hongos", "x_studio_frutos_con_decoloracin_e_inmaduros_y_frutos_rojos",
                             "x_studio_frutos_con_sobre_madurez_y_exudacin", "x_studio_dao_por_insecto",
                             "x_studio_deshidratado", "x_studio_heridapartidamolida", "x_studio_temperatura"]
                        )
                        for lin in lineas:
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
                    linea_ids = qc.get("x_studio_one2many_field_mZmK2", [])
                    if linea_ids:
                        lineas = client.search_read(
                            "x_quality_check_line_89a53",
                            [("id", "in", linea_ids)],
                            ["x_studio_fecha_y_hora", "x_studio_calificacion", "x_studio_total_defectos_",
                             "x_studio_muestra_grs", "x_studio_n_palet", "x_studio_dao_mecanico",
                             "x_studio_hongo", "x_studio_inmadura", "x_studio_sobremadurez",
                             "x_studio_daos_por_insectos", "x_studio_deformesgrs", "x_studio_temperatura_c"]
                        )
                        for lin in lineas:
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
                        linea_ids = qc.get("x_studio_one2many_field_rgA7I", [])
                        if linea_ids:
                            lineas = client.search_read(
                                "x_quality_check_line_1d183",
                                [("id", "in", linea_ids)],
                                ["x_studio_hora_monitoreo", "x_studio_iqf", "x_studio_block",
                                 "x_studio_muestra", "x_studio_hongos", "x_studio_inmadura",
                                 "x_studio_sombremadura", "x_studio_deshidratado", "x_studio_crumble",
                                 "x_studio_t_prod_termin"]
                            )
                            for lin in lineas:
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
