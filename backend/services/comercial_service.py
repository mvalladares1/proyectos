from typing import List, Dict, Any
from ..core.odoo_client import odoo_client
import pandas as pd
import time
import datetime

class ComercialService:
    """
    Servicio para manejar lógica de negocio del Dashboard Comercial.
    Interactúa con Odoo o Archivos Locales para obtener ventas y categorizarlas.
    """
    def __init__(self):
        self._filter_cache = None
        self._last_cache_update = 0
        self._cache_duration = 300  # 5 minutos - reducir llamadas a Odoo
        self._data_cache = None
        self._last_data_update = 0

    
    def get_filter_values(self) -> Dict[str, List[Any]]:
        """Devuelve listas de valores únicos consultando Odoo en tiempo real con fallback seguro"""
        
        # 0. Usar cache si es reciente
        if self._filter_cache and (time.time() - self._last_cache_update < self._cache_duration):
            return self._filter_cache

        data = self.get_relacion_comercial_data()
        def get_unique(key):
            res = sorted(list(set([d[key] for d in data.get('raw_data', []) if d.get(key)])))
            return res if res else []

        # 2. Construir filtros directamente desde la data de ventas/pedidos
        # Esto asegura "solo a quienes les vendemos"
        clientes_total = get_unique('cliente')
        paises_total = get_unique('pais')
        categorias_total = get_unique('categoria_cliente')
        
        # Actualizar cache de filtros
        res_filters = {
            "anio": sorted(get_unique('anio'), reverse=True),
            "cliente": clientes_total,
            "manejo": get_unique('manejo'),
            "especie": get_unique('especie'),
            "variedad": get_unique('variedad'),
            "incoterm": get_unique('incoterm'),
            "pais": paises_total,
            "categoria_cliente": categorias_total,
            "programa": get_unique('programa')
        }
        
        self._filter_cache = res_filters
        self._last_cache_update = time.time()
        
        return res_filters

    def get_relacion_comercial_data(self, filters: Dict[str, List[Any]] = None) -> Dict[str, Any]:
        """
        Obtiene datos reales desde Odoo (account.move.line y sale.order.line).
        Implementa caché para evitar lentitud.
        """
        # 0. Verificar Caché de datos crudos procesados
        is_cache_valid = (self._data_cache is not None) and (time.time() - self._last_data_update < self._cache_duration)
        
        if is_cache_valid:
            data_processed = self._data_cache
        else:
            data_processed = []

        kpis = {
            "total_ventas_anio": 0,
            "total_ventas_mes": 0,
            "total_comprometido": 0
        }
        
        # 1.0 Obtener tasa de USD
        usd_rate = 1.0
        try:
            usd_info = odoo_client.search_read('res.currency', [('name', '=', 'USD')], ['rate'])
            if usd_info: usd_rate = usd_info[0]['rate']
        except: pass

        # --- INTENTO 1: ODOO LIVE ---
        try:
            if not is_cache_valid:
                domain_inv = [
                    ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
                    ('account_id', 'in', [132, 133, 581, 1741, 1857]), 
                    ('product_id.product_tag_ids', 'in', [18, 19, 20, 25, 21]),  # Excluir 41 (Servicio)
                    ('parent_state', '=', 'posted'),
                    ('display_type', 'not in', ['line_section', 'line_note']),
                    ('product_id', '!=', False)
                ]
                
                # Campos mínimos necesarios
                fields_inv = ['product_id', 'partner_id', 'date', 'quantity', 'move_id', 'balance', 'parent_state']
                results_inv = odoo_client.search_read('account.move.line', domain_inv, fields_inv, limit=50000, order='date desc')
                
                # 1.2 COMPROMETIDO (sale.order.line) - solo pedidos recientes
                domain_sale = [
                    ('state', 'in', ['draft', 'sent', 'sale']),  # Excluir 'done' ya facturados
                    ('display_type', 'not in', ['line_section', 'line_note']),
                    ('product_id', '!=', False),
                    ('product_id.product_tag_ids', 'in', [18, 19, 20, 25, 21])  # Excluir 41
                ]
                # Campos mínimos
                fields_sale = ['product_id', 'order_partner_id', 'price_subtotal', 'product_uom_qty', 'qty_invoiced', 'order_id']
                results_sale = odoo_client.search_read('sale.order.line', domain_sale, fields_sale, limit=10000)

                # Mapas de soporte
                partner_map = {}
                move_map = {}
                product_map = {}
                variety_map = {}
                sale_map = {}

                # IDs para lecturas masivas
                all_partner_ids = set()
                all_move_ids = set()
                all_product_ids = set()
                all_sale_ids = set()

                for line in results_inv:
                    if line.get('partner_id'): all_partner_ids.add(line['partner_id'][0])
                    if line.get('move_id'): all_move_ids.add(line['move_id'][0])
                    if line.get('product_id'): all_product_ids.add(line['product_id'][0])
                
                for line in results_sale:
                    if line.get('order_partner_id'): all_partner_ids.add(line['order_partner_id'][0])
                    if line.get('product_id'): all_product_ids.add(line['product_id'][0])
                    if line.get('order_id'): all_sale_ids.add(line['order_id'][0])

                # Lecturas masivas
                if all_partner_ids:
                    partners_info = odoo_client.read('res.partner', list(all_partner_ids), ['id', 'country_id', 'x_studio_categora_de_contacto'])
                    for p in partners_info:
                        partner_map[p['id']] = {
                            'pais': p['country_id'][1] if p['country_id'] else "Desconocido",
                            'categoria': p['x_studio_categora_de_contacto'] or "Sin Categoría"
                        }

                if all_move_ids:
                    moves_info = odoo_client.read('account.move', list(all_move_ids), ['id', 'invoice_incoterm_id', 'sii_pais_destino_id', 'move_type'])
                    for m in moves_info:
                        move_map[m['id']] = {
                            'incoterm': m['invoice_incoterm_id'][1] if m['invoice_incoterm_id'] else "N/A",
                            'destino_real': m['sii_pais_destino_id'][1] if m.get('sii_pais_destino_id') else None,
                            'move_type': m.get('move_type', 'out_invoice')
                        }

                if all_sale_ids:
                    sales_info = odoo_client.read('sale.order', list(all_sale_ids), ['id', 'date_order', 'incoterm', 'currency_id'])
                    for s in sales_info:
                        sale_map[s['id']] = {
                            'fecha': s['date_order'],
                            'incoterm': s['incoterm'][1] if s['incoterm'] else "N/A",
                            'currency_name': s['currency_id'][1] if s.get('currency_id') else "CLP"
                        }

                if all_product_ids:
                    prod_fields = ['id', 'categ_id', 'product_tag_ids', 'x_studio_sub_categora', 
                                   'x_studio_categora_tipo_de_manejo', 'x_studio_categora_variedad',
                                   'x_studio_selection_field_7qfiv']
                    products_info = odoo_client.read('product.product', list(all_product_ids), prod_fields)
                    all_variety_ids = set()
                    for p in products_info:
                        product_map[p['id']] = p
                        if p.get('x_studio_categora_variedad'):
                            for v_id in p['x_studio_categora_variedad']: all_variety_ids.add(v_id)
                    
                    if all_variety_ids:
                        varieties = odoo_client.read('x_variedad', list(all_variety_ids), ['id', 'display_name'])
                        for v in varieties: variety_map[v['id']] = v.get('display_name', "Variedad Desconocida")

                # Procesar Facturas
                for line in results_inv:
                    # Obtener información del movimiento (factura/nota de crédito)
                    m_id = line['move_id'][0] if line.get('move_id') else None
                    m_type = move_map.get(m_id, {}).get('move_type', 'out_invoice')
                    is_refund = (m_type == 'out_refund')
                    
                    if line.get('parent_state') != 'posted':
                        monto_clp = 0
                        qty = 0
                    else:
                        balance = line.get('balance', 0)
                        monto_clp = -balance 
                        raw_qty = abs(line.get('quantity', 0))
                        
                        # Si es nota de crédito, los kilos deben ser negativos
                        # Si es factura normal, los kilos son positivos
                        qty = -raw_qty if is_refund else raw_qty
                    
                    cliente_name = line['partner_id'][1] if line['partner_id'] else "Desconocido"
                    fecha_str = str(line['date'])[:10]
                    anio = int(fecha_str[:4])
                    mes = int(fecha_str[5:7])
                    trimestre = f"Q{(mes - 1) // 3 + 1}"

                    incoterm = move_map.get(m_id, {}).get('incoterm', "N/A")
                    destino_real = move_map.get(m_id, {}).get('destino_real')
                    p_id = line['partner_id'][0] if line['partner_id'] else None
                    pais = destino_real if destino_real else partner_map.get(p_id, {}).get('pais', "Desconocido")
                    cat_cliente = partner_map.get(p_id, {}).get('categoria', "Sin Categoría")

                    prod_id = line['product_id'][0]
                    especie, manejo, variedad, temporada, programa = self._classify_product(prod_id, line['product_id'][1], product_map, variety_map, anio)

                    # Excluir servicios (no son productos físicos)
                    if especie == "SERVICIOS":
                        continue

                    tipo_display = "Nota de Crédito" if is_refund else "Factura"

                    data_processed.append({
                        'tipo': tipo_display, 'cliente': cliente_name, 'anio': anio, 'mes': mes,
                        'trimestre': trimestre, 'manejo': manejo, 'programa': programa,
                        'especie': especie, 'variedad': variedad, 'temporada': temporada,
                        'incoterm': incoterm, 'pais': pais, 'categoria_cliente': cat_cliente,
                        'kilos': qty, 'monto': monto_clp, 'date': fecha_str,
                        'documento': line.get('move_name', 'N/A')
                    })

                # Procesar Pedidos
                for line in results_sale:
                    s_id = line['order_id'][0]
                    s_data = sale_map.get(s_id, {})
                    qty_ordered = line['product_uom_qty']
                    
                    # Usar el monto total del pedido (sin restar lo facturado)
                    raw_monto_full = line['price_subtotal']
                    
                    if s_data.get('currency_name') == "USD":
                        monto = raw_monto_full / usd_rate if usd_rate != 0 else raw_monto_full
                    else:
                        monto = raw_monto_full
                    
                    fecha_order = s_data.get('fecha', str(datetime.datetime.now()))[:10]
                    anio = int(fecha_order[:4])
                    mes = int(fecha_order[5:7])

                    prod_id = line['product_id'][0]
                    especie, manejo, variedad, temporada, programa = self._classify_product(prod_id, line['product_id'][1], product_map, variety_map, anio)

                    # Excluir servicios (no son productos físicos)
                    if especie == "SERVICIOS":
                        continue

                    data_processed.append({
                        'tipo': 'Comprometido', 'cliente': line['order_partner_id'][1] if line['order_partner_id'] else "Descon.",
                        'anio': anio, 'mes': mes, 'trimestre': f"Q{(mes - 1) // 3 + 1}",
                        'manejo': manejo, 'programa': programa, 'especie': especie,
                        'variedad': variedad, 'temporada': temporada, 'incoterm': s_data.get('incoterm', "N/A"),
                        'pais': partner_map.get(line['order_partner_id'][0], {}).get('pais', "Descon.") if line['order_partner_id'] else "Descon.",
                        'categoria_cliente': partner_map.get(line['order_partner_id'][0], {}).get('categoria', "S/C") if line['order_partner_id'] else "S/C",
                        'kilos': qty_ordered, 'monto': monto, 'date': fecha_order,
                        'documento': line['order_id'][1] if line.get('order_id') else 'S/N'
                    })

        except Exception as e:
            if not is_cache_valid:
                print(f"⚠️ Error Odoo: {e}")

        # Guardar caché
        if not is_cache_valid and data_processed:
            self._data_cache = data_processed
            self._last_data_update = time.time()

        # Aplicar filtros y KPIs
        df_base = pd.DataFrame(data_processed)
        if df_base.empty:
            return {"raw_data": [], "kpis": kpis}

        df_filtered = df_base.copy()
        if filters:
            for k, v in filters.items():
                if v and k in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered[k].isin(v)]

        now = datetime.datetime.now()
        cur_anio, cur_mes = now.year, now.month
        df_inv_base = df_base[df_base['tipo'].isin(['Factura', 'Nota de Crédito'])]
        
        if filters:
            for k, v in filters.items():
                if v and k not in ['anio', 'mes', 'trimestre'] and k in df_inv_base.columns:
                    df_inv_base = df_inv_base[df_inv_base[k].isin(v)]

        sel_anios = filters.get('anio', []) if filters else []
        sel_meses = filters.get('mes', []) if filters else []
        sel_trimestres = filters.get('trimestre', []) if filters else []
        
        # Determinar qué filtros temporales están activos
        has_time_filter = bool(sel_meses or sel_trimestres)
        
        # TOTAL VENTAS (dinámico según filtro)
        # df_inv_base ya tiene filtros de cliente, especie, etc., pero NO de tiempo
        if has_time_filter or sel_anios:
            # Si hay filtro temporal o de año, aplicar esos filtros
            df_for_kpi = df_inv_base.copy()
            if sel_anios:
                df_for_kpi = df_for_kpi[df_for_kpi['anio'].isin(sel_anios)]
            if sel_meses:
                df_for_kpi = df_for_kpi[df_for_kpi['mes'].isin(sel_meses)]
            if sel_trimestres:
                df_for_kpi = df_for_kpi[df_for_kpi['trimestre'].isin(sel_trimestres)]
            
            total_ventas = df_for_kpi['monto'].sum()
            total_kilos = df_for_kpi['kilos'].sum()
            kpi_label = "Total Ventas (Filtrado)"
        else:
            # Sin filtros de tiempo, mostrar TODOS los años
            total_ventas = df_inv_base['monto'].sum()
            total_kilos = df_inv_base['kilos'].sum()
            kpi_label = "Total Ventas"

        return {
            "raw_data": df_filtered.to_dict('records'),
            "kpis": {
                "total_ventas": float(total_ventas),
                "total_kilos": float(total_kilos),
                "total_comprometido": float(df_filtered[df_filtered['tipo'] == 'Comprometido']['monto'].sum()),
                "kpi_label": kpi_label,
                "has_filters": has_time_filter or bool(sel_anios)
            }
        }

    def _classify_product(self, prod_id, prod_name, product_map, variety_map, anio):
        p = product_map.get(prod_id, {})
        p_name = str(prod_name).upper()
        sub_cat = str(p.get('x_studio_sub_categora', '')).upper()
        
        # Combinamos nombre y subcategoría para la búsqueda de especie
        search_text = f"{p_name} {sub_cat}"
        
        # 1. Especie
        # Por defecto tomamos el nombre de la categoría de Odoo (última parte) para evitar el label "Otras"
        orig_cat = p.get('categ_id', [0, ""])[1]
        especie = orig_cat.split(' / ')[-1] if ' / ' in orig_cat else (orig_cat or "Sin Categoría")
        
        # Clasificación por palabras clave (robusta)
        if any(x in search_text for x in ["AR ", "AR-", " AR", "ARÁNDANO", "BLUEBERRY", "BLUEBERRIES"]):
            especie = "Arándano"
        elif any(x in search_text for x in ["FB ", "FB-", " FB", "FRAMBUESA", "RASPBERRY", "RASPBERRIES"]):
            especie = "Frambuesa"
        elif any(x in search_text for x in ["CE ", "CE-", " CE", "CEREZA", "CHERRY", "CHERRIES"]):
            especie = "Cereza"
        elif any(x in search_text for x in ["MORA", "BLACKBERRY", "BLACKBERRIES"]):
            especie = "Mora"
        elif any(x in search_text for x in ["FRUTILLA", "STRAWBERRY", "STRAWBERRIES"]):
            especie = "Frutilla"
        elif any(x in search_text for x in ["MIX", "BERRIES"]):
            especie = "Mix"

        # 2. Manejo
        manejo = p.get('x_studio_categora_tipo_de_manejo') or "Convencional"
        
        # 3. Variedad
        variedad_ids = p.get('x_studio_categora_variedad', [])
        variedad = variety_map.get(variedad_ids[0]) if variedad_ids else "S/V"

        # 4. Temporada
        temporada = p.get('x_studio_selection_field_7qfiv') or f"{anio}-{anio+1}"

        # 5. Programa - Basado en product_tag_ids
        # Tag 18, 19, 20 = Granel | Tag 25 = Retail | Tag 21 = Subproducto | Tag 41 = Servicio
        tag_ids = p.get('product_tag_ids', [])
        
        # Determinar programa por tag
        if 21 in tag_ids:
            programa = "Subproducto"
        elif 25 in tag_ids:
            programa = "Retail"
        elif any(t in tag_ids for t in [18, 19, 20]):
            programa = "Granel"
        elif 41 in tag_ids:
            programa = "SERVICIOS"  # Será excluido
        else:
            # Fallback: buscar por texto si no hay tag reconocido
            orig_cat_up = orig_cat.upper()
            full_search = f"{search_text} {orig_cat_up}"
            if "RETAIL" in full_search: 
                programa = "Retail"
            elif any(x in full_search for x in ["SUBPROD", "MERMA", "Desecho"]): 
                programa = "Subproducto"
            else: 
                programa = "Granel"

        return especie, manejo, variedad, temporada, programa

comercial_service = ComercialService()
