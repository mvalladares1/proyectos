"""
Servicio de Producción - Lógica de negocio para órdenes de fabricación
Migrado del dashboard original de producción
OPTIMIZADO: Incluye caché para KPIs
"""
from typing import Optional, Dict, List, Any
from datetime import datetime
from fastapi import HTTPException

from shared.odoo_client import OdooClient
from backend.utils import clean_record
from backend.cache import get_cache, OdooCache


class ProduccionService:
    """
    Servicio para manejar datos de producción desde Odoo.
    Incluye órdenes de fabricación, componentes, subproductos y KPIs.
    """
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
        self._cache = get_cache()
    
    def get_ordenes_fabricacion(self, estado: Optional[str] = None,
                                fecha_desde: Optional[str] = None,
                                fecha_hasta: Optional[str] = None,
                                limit: int = 100) -> List[Dict]:
        """Obtiene órdenes de fabricación con filtros opcionales."""
        domain = []
        
        if estado:
            domain.append(['state', '=', estado])
        if fecha_desde:
            domain.append(['date_planned_start', '>=', fecha_desde])
        if fecha_hasta:
            domain.append(['date_planned_start', '<=', fecha_hasta])
        
        ordenes = self.odoo.search_read(
            'mrp.production',
            domain,
            ['name', 'product_id', 'product_qty', 'qty_produced', 'state', 
             'date_start', 'date_finished', 'date_planned_start', 'user_id', 'company_id'],
            limit=limit,
            order='date_planned_start desc'
        )
        
        return [clean_record(o) for o in ordenes]
    
    def get_of_detail(self, of_id: int) -> Dict[str, Any]:
        """
        Obtiene el detalle completo de una orden de fabricación.
        Incluye componentes, subproductos, detenciones, consumo y KPIs.
        """
        # Campos básicos
        basic_fields = [
            "name", "product_id", "product_qty", "qty_produced", "user_id",
            "date_planned_start", "date_start", "date_finished", "state", 
            "company_id", "move_raw_ids", "move_finished_ids"
        ]
        
        # Campos personalizados (pueden no existir en todas las instancias)
        custom_fields = [
            "x_studio_cantidad_consumida", "x_studio_kghh_efectiva", 
            "x_studio_kghora_efectiva", "x_studio_horas_detencion_totales",
            "x_studio_dotacin", "x_studio_merma_bolsas",
            "x_studio_odf_es_para_una_po_en_particular", "x_studio_nmero_de_po_1",
            "x_studio_clientes", "x_studio_po_asociada", "x_studio_kg_totales_po",
            "x_studio_kg_consumidos_po", "x_studio_kg_disponibles_po",
            "x_studio_inicio_de_proceso", "x_studio_termino_de_proceso",
            "x_studio_hh", "x_studio_hh_efectiva", "x_studio_sala_de_proceso",
            "x_detenciones_id", "x_studio_one2many_field_edeem"
        ]
        
        # Intentar con todos los campos
        try:
            result = self.odoo.read('mrp.production', [of_id], basic_fields + custom_fields)
        except Exception:
            # Si falla, usar solo básicos
            result = self.odoo.read('mrp.production', [of_id], basic_fields)
        
        if not result:
            raise HTTPException(status_code=404, detail="Orden de Fabricación no encontrada")
        
        of_raw = result[0]
        of = clean_record(of_raw)
        
        # Obtener datos complementarios
        componentes = self._get_lines_detail(of_raw.get("move_raw_ids", []))
        subproductos_raw = self._get_lines_detail(of_raw.get("move_finished_ids", []))
        subproductos = self._filter_subproductos(subproductos_raw)
        detenciones = self._get_detenciones(of_raw.get("x_detenciones_id", []))
        consumo = self._get_consumo(
            of_raw.get("x_studio_one2many_field_edeem", []),
            componentes,
            subproductos
        )
        
        # Calcular KPIs
        kpis = self._calculate_kpis(of, componentes, subproductos)
        
        return {
            "of": of,
            "componentes": componentes,
            "subproductos": subproductos,
            "detenciones": detenciones,
            "consumo": consumo,
            "kpis": kpis
        }
    
    def _get_lines_detail(self, move_ids: List[int]) -> List[Dict]:
        """Obtiene el detalle de líneas de movimiento (lotes, pallets, ubicaciones)"""
        if not move_ids:
            return []
        
        line_ids = self.odoo.search('stock.move.line', [['move_id', 'in', move_ids]])
        if not line_ids:
            return []
        
        lines_raw = self.odoo.read('stock.move.line', line_ids, [
            "product_id", "lot_id", "result_package_id", "package_id",
            "qty_done", "location_id", "location_dest_id", "product_category_name",
            "x_studio_precio_unitario"
        ])
        
        return [clean_record(x) for x in lines_raw]
    
    def _filter_subproductos(self, subproductos_raw: List[Dict]) -> List[Dict]:
        """Filtra subproductos excluyendo 'Proceso Retail'"""
        subproductos = []
        for sub in subproductos_raw:
            prod_name = sub.get("product_id", {}).get("name", "") if isinstance(sub.get("product_id"), dict) else ""
            if "proceso retail" not in prod_name.lower():
                subproductos.append(sub)
        return subproductos
    
    def _get_detenciones(self, ids_det: List[int]) -> List[Dict]:
        """Obtiene las detenciones de una OF"""
        if not ids_det:
            return []
        
        try:
            det_raw = self.odoo.read('x_detenciones_proceso', ids_det, [
                "x_studio_responsable", "x_motivodetencion",
                "x_horainiciodetencion", "x_horafindetencion",
                "x_studio_horas_de_detencin"
            ])
            return [clean_record(x) for x in det_raw]
        except Exception:
            return []
    
    def _get_consumo(self, ids_cons: List[int], componentes: List[Dict], 
                     subproductos: List[Dict]) -> List[Dict]:
        """Obtiene las horas de consumo enriquecidas con datos de producto/lote"""
        if not ids_cons:
            return []
        
        try:
            cons_raw = self.odoo.read('x_mrp_production_line_d413e', ids_cons, [
                "x_name", "x_studio_hora_inicio", "x_studio_hora_fin"
            ])
        except Exception:
            return []
        
        # Crear mapa de Pallet -> {Producto, Lote, Tipo}
        pallet_map = self._create_pallet_map(componentes, subproductos)
        
        consumo = []
        for r in cons_raw:
            clean_r = clean_record(r)
            pallet = clean_r.get("x_name", "").strip()
            
            if pallet in pallet_map:
                clean_r["producto"] = pallet_map[pallet]["product"]
                clean_r["lote"] = pallet_map[pallet]["lot"]
                clean_r["type"] = pallet_map[pallet]["type"]
            else:
                clean_r["producto"] = "Desconocido"
                clean_r["lote"] = ""
                clean_r["type"] = "Desconocido"
            
            consumo.append(clean_r)
        
        return consumo
    
    def _create_pallet_map(self, componentes: List[Dict], 
                          subproductos: List[Dict]) -> Dict[str, Dict]:
        """Crea un mapa de pallet a información de producto"""
        pallet_map = {}
        
        for c in componentes:
            prod_info = {
                "product": c.get("product_id", {}).get("name", "") if isinstance(c.get("product_id"), dict) else "",
                "lot": c.get("lot_id", {}).get("name", "") if isinstance(c.get("lot_id"), dict) else "",
                "type": "Componente"
            }
            
            p_src = c.get("package_id", {}).get("name", "") if isinstance(c.get("package_id"), dict) else ""
            if p_src:
                pallet_map[p_src.strip()] = prod_info
            
            p_dest = c.get("result_package_id", {}).get("name", "") if isinstance(c.get("result_package_id"), dict) else ""
            if p_dest:
                pallet_map[p_dest.strip()] = prod_info
        
        for s in subproductos:
            prod_info = {
                "product": s.get("product_id", {}).get("name", "") if isinstance(s.get("product_id"), dict) else "",
                "lot": s.get("lot_id", {}).get("name", "") if isinstance(s.get("lot_id"), dict) else "",
                "type": "Subproducto"
            }
            
            p_src = s.get("package_id", {}).get("name", "") if isinstance(s.get("package_id"), dict) else ""
            if p_src:
                pallet_map[p_src.strip()] = prod_info
            
            p_dest = s.get("result_package_id", {}).get("name", "") if isinstance(s.get("result_package_id"), dict) else ""
            if p_dest:
                pallet_map[p_dest.strip()] = prod_info
        
        return pallet_map
    
    def _calculate_kpis(self, of: Dict, componentes: List[Dict], 
                       subproductos: List[Dict]) -> Dict:
        """Calcula los KPIs de una OF"""
        product_qty = of.get("product_qty", 0) or 0
        kghh = of.get("x_studio_kghh_efectiva", 0) or 0
        dotacion = of.get("x_studio_dotacin", 0) or 0
        horas_detencion = of.get("x_studio_horas_detencion_totales", 0) or 0
        
        # Consumo real MP (excluyendo insumos, envases, etc)
        excluded_cat = ["insumo", "envase", "etiqueta", "embalaje", "merma"]
        excluded_name = ["caja", "bolsa", "insumo", "envase", "pallet", "etiqueta"]
        
        consumo_real_mp = 0
        for line in componentes:
            cat_name = (line.get("product_category_name", "") or "").lower()
            prod_name = (line.get("product_id", {}).get("name", "") if isinstance(line.get("product_id"), dict) else "").lower()
            qty = line.get("qty_done", 0) or 0
            
            is_excluded = any(k in cat_name for k in excluded_cat) or any(k in prod_name for k in excluded_name)
            if not is_excluded:
                consumo_real_mp += qty
        
        # Total subproductos (sin merma para rendimiento)
        total_sub_yield = sum([
            s.get("qty_done", 0) or 0 for s in subproductos
            if "merma" not in (s.get("product_category_name", "") or "").lower()
        ])
        
        total_sub_kg = sum([s.get("qty_done", 0) or 0 for s in subproductos])
        consumo_total = sum([m.get("qty_done", 0) or 0 for m in componentes])
        
        # Cálculos
        rendimiento = (total_sub_yield / consumo_real_mp * 100) if consumo_real_mp else 0
        kg_por_hh = (total_sub_kg / kghh) if kghh else 0
        kg_por_operario = (total_sub_kg / dotacion) if dotacion else 0
        
        duracion_horas = 0
        if of.get("date_start") and of.get("date_finished"):
            try:
                d0 = datetime.strptime(of["date_start"], "%Y-%m-%d %H:%M:%S")
                d1 = datetime.strptime(of["date_finished"], "%Y-%m-%d %H:%M:%S")
                duracion_horas = round((d1 - d0).total_seconds() / 3600, 2)
            except:
                pass
        
        return {
            "produccion_total_kg": total_sub_kg,
            "produccion_plan_kg": product_qty,
            "rendimiento_%": round(rendimiento, 2),
            "kg_por_hh": round(kg_por_hh, 2),
            "kg_por_operario": round(kg_por_operario, 2),
            "duracion_horas": duracion_horas,
            "horas_detencion": horas_detencion,
            "consumo_mp_kg": consumo_real_mp,
            "consumo_total_kg": consumo_total
        }
    
    def get_kpis(self) -> Dict[str, int]:
        """
        Obtiene KPIs de producción.
        OPTIMIZADO: Usa read_group + caché de 5 minutos.
        """
        # Intentar obtener del caché primero
        cache_key = "produccion_kpis"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            # Una sola llamada a read_group para obtener conteos por estado
            grouped = self.odoo.execute(
                'mrp.production', 'read_group',
                [],  # domain vacío = todos
                ['state'],  # campos a leer
                ['state']  # agrupar por estado
            )
            
            # Convertir resultado a diccionario
            state_counts = {g['state']: g['state_count'] for g in grouped}
            
            total = sum(state_counts.values())
            
            result = {
                'total_ordenes': total,
                'ordenes_progress': state_counts.get('progress', 0),
                'ordenes_confirmed': state_counts.get('confirmed', 0),
                'ordenes_done': state_counts.get('done', 0),
                'ordenes_to_close': state_counts.get('to_close', 0)
            }
            
            # Guardar en caché por 5 minutos
            self._cache.set(cache_key, result, ttl=OdooCache.TTL_KPIS)
            return result
            
        except Exception as e:
            # Fallback al método anterior si read_group falla
            print(f"read_group failed, using fallback: {e}")
            total = len(self.odoo.search('mrp.production', []))
            progress = len(self.odoo.search('mrp.production', [['state', '=', 'progress']]))
            confirmed = len(self.odoo.search('mrp.production', [['state', '=', 'confirmed']]))
            done = len(self.odoo.search('mrp.production', [['state', '=', 'done']]))
            to_close = len(self.odoo.search('mrp.production', [['state', '=', 'to_close']]))
            
            result = {
                'total_ordenes': total,
                'ordenes_progress': progress,
                'ordenes_confirmed': confirmed,
                'ordenes_done': done,
                'ordenes_to_close': to_close
            }
            
            # Incluso en fallback, cachear para evitar spam de llamadas
            self._cache.set(cache_key, result, ttl=OdooCache.TTL_KPIS)
            return result
    
    def get_resumen(self) -> Dict[str, Any]:
        """Obtiene un resumen general de producción."""
        ordenes = self.get_ordenes_fabricacion(limit=10)
        kpis = self.get_kpis()
        
        return {
            'kpis': kpis,
            'total_ordenes': kpis['total_ordenes'],
            'ordenes_recientes': ordenes
        }
    
    def get_clasificacion_pallets(self, 
                                  fecha_inicio: str, 
                                  fecha_fin: str,
                                  tipo_fruta: Optional[str] = None,
                                  tipo_manejo: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene la clasificación de pallets (IQF A y RETAIL) filtrando por fecha, fruta y manejo.
        
        Lógica:
        1. Obtiene stock.move.line filtrados por fecha
        2. Obtiene x_mrp_production_line_d413e 
        3. Compara result_package_id con x_name
        4. Suma kg de qty_done según clasificación en x_studio_observaciones
        
        Args:
            fecha_inicio: Fecha inicio (YYYY-MM-DD)
            fecha_fin: Fecha fin (YYYY-MM-DD)
            tipo_fruta: Opcional - Filtrar por tipo de fruta
            tipo_manejo: Opcional - Filtrar por tipo de manejo (ej: "Orgánico", "Convencional")
        
        Returns:
            {
                "iqf_a_kg": float,
                "retail_kg": float,
                "total_kg": float,
                "detalle": [...] # Lista de pallets clasificados
            }
        """
        try:
            # 1. Obtener stock.move.line con filtros de fecha
            domain_sml = [
                ('date', '>=', fecha_inicio + ' 00:00:00'),
                ('date', '<=', fecha_fin + ' 23:59:59'),
                ('result_package_id', '!=', False),  # Solo con paquete resultado
                ('qty_done', '>', 0)  # Solo con cantidad hecha
            ]
            
            # Obtener campos de stock.move.line
            sml_fields = [
                'result_package_id', 
                'qty_done', 
                'product_id', 
                'lot_id',
                'date',
                'move_id'
            ]
            
            stock_move_lines = self.odoo.search_read(
                'stock.move.line',
                domain_sml,
                sml_fields
            )
            
            if not stock_move_lines:
                return {
                    "iqf_a_kg": 0,
                    "retail_kg": 0,
                    "total_kg": 0,
                    "detalle": []
                }
            
            # 2. Crear mapa de result_package_id -> kg y info
            package_map = {}
            for sml in stock_move_lines:
                pkg_id = sml.get('result_package_id')
                if pkg_id and isinstance(pkg_id, list) and len(pkg_id) >= 2:
                    pkg_name = pkg_id[1]  # [id, name]
                    qty_done = sml.get('qty_done', 0) or 0
                    
                    # Obtener info del producto para filtros
                    product_info = sml.get('product_id', [False, ''])
                    product_name = product_info[1] if isinstance(product_info, list) and len(product_info) >= 2 else ''
                    
                    lot_info = sml.get('lot_id', [False, ''])
                    lot_name = lot_info[1] if isinstance(lot_info, list) and len(lot_info) >= 2 else ''
                    
                    if pkg_name not in package_map:
                        package_map[pkg_name] = {
                            'qty_done': qty_done,
                            'product_name': product_name,
                            'lot_name': lot_name,
                            'date': sml.get('date', ''),
                            'clasificacion': None  # Se llenará después
                        }
                    else:
                        # Si el paquete aparece varias veces, sumar
                        package_map[pkg_name]['qty_done'] += qty_done
            
            # 3. Obtener x_mrp_production_line_d413e para matching
            # Buscar todos los registros para hacer el match
            domain_mrp_line = []
            
            mrp_line_fields = [
                'x_name',
                'x_studio_observaciones'
            ]
            
            mrp_lines = self.odoo.search_read(
                'x_mrp_production_line_d413e',
                domain_mrp_line,
                mrp_line_fields,
                limit=10000  # Límite alto para obtener todos los posibles matches
            )
            
            # 4. Crear mapa de x_name -> x_studio_observaciones
            clasificacion_map = {}
            for mrp_line in mrp_lines:
                x_name = (mrp_line.get('x_name') or '').strip()
                observaciones = (mrp_line.get('x_studio_observaciones') or '').strip().upper()
                
                if x_name:
                    clasificacion_map[x_name] = observaciones
            
            # 5. Hacer el matching y clasificar
            iqf_a_kg = 0
            retail_kg = 0
            detalle = []
            
            for pkg_name, pkg_data in package_map.items():
                clasificacion = clasificacion_map.get(pkg_name, '')
                
                # Aplicar filtros de fruta y manejo si se proporcionaron
                incluir = True
                product_name_lower = pkg_data['product_name'].lower()
                
                if tipo_fruta:
                    if tipo_fruta.lower() not in product_name_lower:
                        incluir = False
                
                if tipo_manejo:
                    # Buscar palabras clave de manejo
                    if tipo_manejo.lower() == 'orgánico' or tipo_manejo.lower() == 'organico':
                        if 'org' not in product_name_lower:
                            incluir = False
                    elif tipo_manejo.lower() == 'convencional':
                        if 'org' in product_name_lower:  # Si tiene "org" es orgánico, no convencional
                            incluir = False
                
                if not incluir:
                    continue
                
                # Clasificar según observaciones
                qty = pkg_data['qty_done']
                
                if 'IQF A' in clasificacion or 'IQFA' in clasificacion:
                    iqf_a_kg += qty
                    pkg_data['clasificacion'] = 'IQF A'
                elif 'RETAIL' in clasificacion:
                    retail_kg += qty
                    pkg_data['clasificacion'] = 'RETAIL'
                else:
                    # Si no tiene clasificación reconocida, no incluir
                    continue
                
                detalle.append({
                    'pallet': pkg_name,
                    'clasificacion': pkg_data['clasificacion'],
                    'kg': round(qty, 2),
                    'producto': pkg_data['product_name'],
                    'lote': pkg_data['lot_name'],
                    'fecha': pkg_data['date']
                })
            
            total_kg = iqf_a_kg + retail_kg
            
            return {
                "iqf_a_kg": round(iqf_a_kg, 2),
                "retail_kg": round(retail_kg, 2),
                "total_kg": round(total_kg, 2),
                "detalle": sorted(detalle, key=lambda x: x['fecha'], reverse=True)
            }
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"❌ ERROR en get_clasificacion_pallets: {error_detail}")
            raise HTTPException(status_code=500, detail=f"Error al obtener clasificación: {str(e)}")
