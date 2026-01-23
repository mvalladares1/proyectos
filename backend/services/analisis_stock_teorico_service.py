"""
Servicio para análisis de stock teórico anual
Calcula: Compras - Ventas - Merma proyectada por año, tipo de fruta y manejo
"""
from typing import List, Dict, Optional
from datetime import datetime


class AnalisisStockTeoricoService:
    """Servicio para análisis de stock teórico anual con proyección de merma."""
    
    def __init__(self, odoo):
        """
        Args:
            odoo: Cliente OdooClient configurado
        """
        self.odoo = odoo
    
    def get_analisis_rango(self, fecha_desde: str, fecha_hasta: str):
        """
        Análisis de stock teórico para un rango de fechas específico.
        
        Args:
            fecha_desde: Fecha inicio en formato YYYY-MM-DD
            fecha_hasta: Fecha fin en formato YYYY-MM-DD
        
        Returns:
            dict con:
                - resumen: totales consolidados del período
                - datos: desglose detallado por tipo de fruta y manejo
                - merma_historica_pct: % de merma del período
        """
        # Obtener compras
        compras = self._get_compras_por_tipo_manejo(fecha_desde, fecha_hasta)
        
        # Obtener ventas
        ventas = self._get_ventas_por_tipo_manejo(fecha_desde, fecha_hasta)
        
        # Consolidar datos
        datos_consolidados = self._consolidar_datos(compras, ventas)
        
        # Calcular % de merma del período
        merma_total_kg = 0
        merma_total_base = 0
        
        for item in datos_consolidados:
            merma_kg = item.get('merma_kg', 0)
            compras_kg = item.get('compras_kg', 0)
            
            if merma_kg > 0 and compras_kg > 0:
                merma_total_kg += merma_kg
                merma_total_base += compras_kg
        
        pct_merma = (merma_total_kg / merma_total_base * 100) if merma_total_base > 0 else 0
        
        # Generar resumen
        resumen = self._generar_resumen_simple(datos_consolidados)
        
        return {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'merma_historica_pct': round(pct_merma, 2),
            'resumen': resumen,
            'datos': datos_consolidados
        }
    
    def get_analisis_multi_anual(self, anios: List[int], fecha_corte_mes_dia: str = "10-31"):
        """
        Análisis multi-anual de compras, ventas y stock teórico.
        IMPORTANTE: Los "años" son TEMPORADAS que van de noviembre a octubre.
        
        Args:
            anios: Lista de temporadas a analizar [2024, 2025, 2026]
                  Temporada 2024 = 2023-11-01 a 2024-10-31
                  Temporada 2025 = 2024-11-01 a 2025-10-31
                  Temporada 2026 = 2025-11-01 a 2026-10-31
            fecha_corte_mes_dia: Mes-Día de corte (formato "MM-DD"), default "10-31"
        
        Returns:
            dict con:
                - resumen_general: totales consolidados
                - por_anio: desglose detallado año por año
                - merma_historica: % de merma calculado histórico
                - proyeccion_stock: stock teórico final por año
        """
        resultados_por_anio = {}
        merma_total_kg = 0
        merma_total_base = 0
        
        # Procesar cada temporada
        for anio in sorted(anios):
            # Temporada comienza en noviembre del año anterior
            fecha_desde = f"{anio - 1}-11-01"
            
            # Temporada termina en octubre del año indicado (o hoy si es año actual)
            fecha_corte_completa = f"{anio}-{fecha_corte_mes_dia}"
            
            if anio == datetime.now().year:
                # Temporada actual: hasta el corte o hasta hoy (lo que sea menor)
                fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                fecha_hasta = min(fecha_corte_completa, fecha_hoy)
            elif anio < datetime.now().year:
                # Temporadas pasadas: hasta el corte
                fecha_hasta = fecha_corte_completa
            else:
                # Temporadas futuras: hasta el corte
                fecha_hasta = fecha_corte_completa
            
            # Obtener compras
            compras = self._get_compras_por_tipo_manejo(fecha_desde, fecha_hasta)
            
            # Obtener ventas
            ventas = self._get_ventas_por_tipo_manejo(fecha_desde, fecha_hasta)
            
            # Calcular merma real (diferencia entre compras y ventas)
            # Asumimos: Compras - Ventas = Stock + Merma
            # Simplificación: Merma = (Compras - Ventas) cuando Compras > Ventas
            
            datos_consolidados = self._consolidar_datos(compras, ventas)
            
            resultados_por_anio[anio] = {
                'anio': anio,
                'temporada': f"{anio-1}-11-01 a {anio}-10-31",
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta,
                'datos': datos_consolidados
            }
            
            # Acumular merma histórica para calcular % promedio
            for item in datos_consolidados:
                merma_kg = item.get('merma_kg', 0)
                compras_kg = item.get('compras_kg', 0)
                
                if merma_kg > 0 and compras_kg > 0:
                    merma_total_kg += merma_kg
                    merma_total_base += compras_kg
        
        # Calcular % de merma histórica global
        pct_merma_historico = (merma_total_kg / merma_total_base * 100) if merma_total_base > 0 else 0
        
        # Generar resumen general
        resumen = self._generar_resumen_general(resultados_por_anio, pct_merma_historico)
        
        return {
            'anios_analizados': anios,
            'fecha_corte': fecha_corte_mes_dia,
            'merma_historica_pct': round(pct_merma_historico, 2),
            'resumen_general': resumen,
            'por_anio': resultados_por_anio
        }
    
    def _get_compras_por_tipo_manejo(self, fecha_desde: str, fecha_hasta: str) -> List[Dict]:
        """
        Obtiene compras agrupadas por tipo de fruta y manejo.
        ACTUALIZADO: Usa product.template + filtra por diario "Facturas Proveedores" + categoría producto.
        Incluye productos archivados usando active_test=False.
        """
        # Líneas de facturas de proveedor - SOLO diario "Facturas de Proveedores"
        # Filtrado por cuentas específicas para evitar duplicaciones contables
        # display_type='product' excluye líneas de COGS (costo de venta) que duplican
        lineas = self.odoo.search_read(
            'account.move.line',
            [
                ['move_id.move_type', '=', 'in_invoice'],
                ['move_id.state', '=', 'posted'],
                ['move_id.payment_state', '!=', 'reversed'],  # Excluir facturas revertidas
                ['move_id.journal_id.name', '=', 'Facturas de Proveedores'],
                ['product_id', '!=', False],
                ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
                ['product_id.type', '!=', 'service'],
                ['account_id.code', 'in', ['21020107', '21020106']],  # Solo cuentas de facturas por recibir
                ['debit', '>', 0],  # Solo líneas con débito (compra real)
                ['display_type', '=', 'product'],  # Solo líneas de producto, excluir COGS
                ['date', '>=', fecha_desde],
                ['date', '<=', fecha_hasta]
            ],
            ['product_id', 'quantity', 'debit', 'account_id'],
            limit=100000
        )
        
        print(f"[DEBUG COMPRAS] Fecha: {fecha_desde} a {fecha_hasta}")
        print(f"[DEBUG COMPRAS] Líneas encontradas (diario Facturas Proveedores): {len(lineas)}")
        
        if not lineas:
            return []
        
        # Obtener product.product
        prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas if l.get('product_id')]))
        
        print(f"[DEBUG COMPRAS] IDs de productos únicos en líneas: {len(prod_ids)}")
        
        # IMPORTANTE: Usar execute_kw con active_test=False para incluir productos archivados
        productos = self.odoo.models.execute_kw(
            self.odoo.db, self.odoo.uid, self.odoo.password,
            'product.product', 'read',
            [prod_ids, ['id', 'product_tmpl_id', 'categ_id']],
            {'context': {'active_test': False}}
        )
        
        print(f"[DEBUG COMPRAS] Productos encontrados en Odoo: {len(productos)}")
        
        # Obtener templates únicos
        template_ids = set()
        product_to_template = {}
        
        for prod in productos:
            prod_id = prod['id']
            tmpl = prod.get('product_tmpl_id')
            if tmpl:
                tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
                template_ids.add(tmpl_id)
                product_to_template[prod_id] = {
                    'tmpl_id': tmpl_id,
                    'categ': prod.get('categ_id', [None, ''])
                }
        
        print(f"[DEBUG COMPRAS] Templates únicos: {len(template_ids)}")
        
        # Obtener templates con campos tipo y manejo (incluir archivados)
        template_map = {}
        if template_ids:
            # IMPORTANTE: active_test=False para incluir templates archivados
            templates = self.odoo.models.execute_kw(
                self.odoo.db, self.odoo.uid, self.odoo.password,
                'product.template', 'read',
                [list(template_ids), ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo']],
                {'context': {'active_test': False}}
            )
            
            print(f"[DEBUG COMPRAS] Templates obtenidos: {len(templates)}")
            
            for tmpl in templates:
                # Parsear tipo de fruta - MEJORADO
                tipo = tmpl.get('x_studio_sub_categora')
                if tipo:
                    if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
                        tipo_str = tipo[1]
                    elif isinstance(tipo, str):
                        tipo_str = tipo
                    elif isinstance(tipo, (list, tuple)) and len(tipo) == 1:
                        tipo_str = str(tipo[0])
                    else:
                        tipo_str = None
                else:
                    tipo_str = None
                
                # Parsear manejo - MEJORADO
                manejo = tmpl.get('x_studio_categora_tipo_de_manejo')
                if manejo:
                    if isinstance(manejo, (list, tuple)) and len(tipo) > 1:
                        manejo_str = manejo[1]
                    elif isinstance(manejo, str):
                        manejo_str = manejo
                    elif isinstance(manejo, (list, tuple)) and len(manejo) == 1:
                        manejo_str = str(manejo[0])
                    else:
                        manejo_str = None
                else:
                    manejo_str = None
                
                template_map[tmpl['id']] = {
                    'nombre': tmpl.get('name', ''),
                    'tipo_fruta': tipo_str,
                    'manejo': manejo_str,
                    'tiene_ambos': bool(tipo_str and manejo_str)
                }
        
        # Mapear productos - TODOS los productos (ya filtrados por PRODUCTOS y account codes)
        productos_map = {}
        productos_incluidos = 0
        
        for prod_id, prod_data in product_to_template.items():
            tmpl_id = prod_data['tmpl_id']
            categ = prod_data['categ']
            categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
            
            if tmpl_id in template_map:
                tmpl_info = template_map[tmpl_id]
                
                # Incluir TODOS los productos que llegaron aquí (ya filtrados por cuenta contable)
                productos_map[prod_id] = {
                    'tipo_fruta': tmpl_info['tipo_fruta'] or 'Sin tipo',
                    'manejo': tmpl_info['manejo'] or 'Sin manejo',
                    'nombre': tmpl_info['nombre'],
                    'categoria': categ_name
                }
                productos_incluidos += 1
        
        print(f"[DEBUG COMPRAS] Productos incluidos: {productos_incluidos}")
        print(f"[DEBUG COMPRAS] Productos mapeados: {len(productos_map)}")
        
        # Agrupar por tipo + manejo
        agrupado = {}
        lineas_descartadas = 0
        kg_descartados = 0
        
        for linea in lineas:
            prod_id = linea.get('product_id', [None])[0]
            if not prod_id or prod_id not in productos_map:
                lineas_descartadas += 1
                kg_descartados += linea.get('quantity', 0)
                continue
            
            prod = productos_map[prod_id]
            key = f"{prod['tipo_fruta']}||{prod['manejo']}"
            
            if key not in agrupado:
                agrupado[key] = {
                    'tipo_fruta': prod['tipo_fruta'],
                    'manejo': prod['manejo'],
                    'kg': 0,
                    'monto': 0
                }
            
            agrupado[key]['kg'] += linea.get('quantity', 0)
            agrupado[key]['monto'] += linea.get('debit', 0)
        
        print(f"[DEBUG COMPRAS] Líneas descartadas: {lineas_descartadas} ({kg_descartados:,.0f} kg)")
        
        return list(agrupado.values())
    
    def _get_ventas_por_tipo_manejo(self, fecha_desde: str, fecha_hasta: str) -> List[Dict]:
        """
        Obtiene ventas agrupadas por tipo de fruta y manejo.
        ACTUALIZADO: Usa product.template + filtra por diario "Facturas de Cliente" + categoría producto.
        Incluye productos archivados usando active_test=False.
        """
        # Líneas de facturas de cliente - SOLO diario "Facturas de Cliente"
        # Filtrado SOLO por tipo_fruta y manejo (sin restricción de cuenta contable)
        # display_type='product' excluye líneas de COGS que duplican
        lineas = self.odoo.search_read(
            'account.move.line',
            [
                ['move_id.move_type', '=', 'out_invoice'],
                ['move_id.state', '=', 'posted'],
                ['move_id.payment_state', '!=', 'reversed'],  # Excluir facturas revertidas
                ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
                ['product_id', '!=', False],
                ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
                ['product_id.type', '!=', 'service'],
                ['display_type', '=', 'product'],  # Solo líneas de producto, excluir COGS
                ['date', '>=', fecha_desde],
                ['date', '<=', fecha_hasta]
            ],
            ['product_id', 'quantity', 'credit', 'debit'],
            limit=100000
        )
        
        print(f"[DEBUG VENTAS] Fecha: {fecha_desde} a {fecha_hasta}")
        print(f"[DEBUG VENTAS] Líneas encontradas (diario Facturas de Cliente): {len(lineas)}")
        
        if not lineas:
            return []
        
        # Obtener product.product
        prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas if l.get('product_id')]))
        
        # IMPORTANTE: Usar execute_kw con active_test=False para incluir productos archivados
        productos = self.odoo.models.execute_kw(
            self.odoo.db, self.odoo.uid, self.odoo.password,
            'product.product', 'read',
            [prod_ids, ['id', 'product_tmpl_id', 'categ_id']],
            {'context': {'active_test': False}}
        )
        
        print(f"[DEBUG VENTAS] Productos únicos: {len(productos)}")
        
        # Obtener templates únicos
        template_ids = set()
        product_to_template = {}
        
        for prod in productos:
            prod_id = prod['id']
            tmpl = prod.get('product_tmpl_id')
            if tmpl:
                tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
                template_ids.add(tmpl_id)
                product_to_template[prod_id] = {
                    'tmpl_id': tmpl_id,
                    'categ': prod.get('categ_id', [None, ''])
                }
        
        print(f"[DEBUG VENTAS] Templates únicos: {len(template_ids)}")
        
        # Obtener templates con campos tipo y manejo (incluir archivados)
        template_map = {}
        if template_ids:
            # IMPORTANTE: active_test=False para incluir templates archivados
            templates = self.odoo.models.execute_kw(
                self.odoo.db, self.odoo.uid, self.odoo.password,
                'product.template', 'read',
                [list(template_ids), ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo']],
                {'context': {'active_test': False}}
            )
            
            print(f"[DEBUG VENTAS] Templates obtenidos: {len(templates)}")
            
            for tmpl in templates:
                # Parsear tipo de fruta - MEJORADO
                tipo = tmpl.get('x_studio_sub_categora')
                if tipo:
                    if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
                        tipo_str = tipo[1]
                    elif isinstance(tipo, str):
                        tipo_str = tipo
                    elif isinstance(tipo, (list, tuple)) and len(tipo) == 1:
                        tipo_str = str(tipo[0])
                    else:
                        tipo_str = None
                else:
                    tipo_str = None
                
                # Parsear manejo - MEJORADO
                manejo = tmpl.get('x_studio_categora_tipo_de_manejo')
                if manejo:
                    if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
                        manejo_str = manejo[1]
                    elif isinstance(manejo, str):
                        manejo_str = manejo
                    elif isinstance(manejo, (list, tuple)) and len(manejo) == 1:
                        manejo_str = str(manejo[0])
                    else:
                        manejo_str = None
                else:
                    manejo_str = None
                
                template_map[tmpl['id']] = {
                    'nombre': tmpl.get('name', ''),
                    'tipo_fruta': tipo_str,
                    'manejo': manejo_str,
                    'tiene_ambos': bool(tipo_str and manejo_str)
                }
        
        # Mapear productos - TODOS los productos (ya filtrados por PRODUCTOS y account codes)
        productos_map = {}
        productos_incluidos = 0
        
        for prod_id, prod_data in product_to_template.items():
            tmpl_id = prod_data['tmpl_id']
            categ = prod_data['categ']
            categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
            
            if tmpl_id in template_map:
                tmpl_info = template_map[tmpl_id]
                
                # Incluir TODOS los productos que llegaron aquí (ya filtrados por cuenta contable)
                productos_map[prod_id] = {
                    'tipo_fruta': tmpl_info['tipo_fruta'] or 'Sin tipo',
                    'manejo': tmpl_info['manejo'] or 'Sin manejo',
                    'nombre': tmpl_info['nombre'],
                    'categoria': categ_name
                }
                productos_incluidos += 1
        
        print(f"[DEBUG VENTAS] Productos incluidos: {productos_incluidos}")
        print(f"[DEBUG VENTAS] Productos mapeados: {len(productos_map)}")
        
        # Agrupar por tipo + manejo
        agrupado = {}
        
        for linea in lineas:
            prod_id = linea.get('product_id', [None])[0]
            if not prod_id or prod_id not in productos_map:
                continue
            
            prod = productos_map[prod_id]
            key = f"{prod['tipo_fruta']}||{prod['manejo']}"
            
            if key not in agrupado:
                agrupado[key] = {
                    'tipo_fruta': prod['tipo_fruta'],
                    'manejo': prod['manejo'],
                    'kg': 0,
                    'monto': 0
                }
            
            agrupado[key]['kg'] += linea.get('quantity', 0)
            agrupado[key]['monto'] += linea.get('credit', 0) - linea.get('debit', 0)
        
        return list(agrupado.values())
    
    def _consolidar_datos(self, compras: List[Dict], ventas: List[Dict]) -> List[Dict]:
        """
        Consolida compras y ventas por tipo/manejo.
        Calcula: Merma = Compras - Ventas (cuando es positivo)
        Stock Teórico = Merma (simplificado, en realidad sería: Stock Inicial + Compras - Ventas - Merma Real)
        """
        consolidado_map = {}
        
        # Agregar compras
        for compra in compras:
            key = f"{compra['tipo_fruta']}||{compra['manejo']}"
            
            if key not in consolidado_map:
                consolidado_map[key] = {
                    'tipo_fruta': compra['tipo_fruta'],
                    'manejo': compra['manejo'],
                    'compras_kg': 0,
                    'compras_monto': 0,
                    'ventas_kg': 0,
                    'ventas_monto': 0
                }
            
            consolidado_map[key]['compras_kg'] += compra['kg']
            consolidado_map[key]['compras_monto'] += compra['monto']
        
        # Agregar ventas
        for venta in ventas:
            key = f"{venta['tipo_fruta']}||{venta['manejo']}"
            
            if key not in consolidado_map:
                consolidado_map[key] = {
                    'tipo_fruta': venta['tipo_fruta'],
                    'manejo': venta['manejo'],
                    'compras_kg': 0,
                    'compras_monto': 0,
                    'ventas_kg': 0,
                    'ventas_monto': 0
                }
            
            consolidado_map[key]['ventas_kg'] += venta['kg']
            consolidado_map[key]['ventas_monto'] += venta['monto']
        
        # Calcular métricas derivadas
        resultado = []
        
        for key, datos in consolidado_map.items():
            compras_kg = datos['compras_kg']
            compras_monto = datos['compras_monto']
            ventas_kg = datos['ventas_kg']
            ventas_monto = datos['ventas_monto']
            
            # Merma = diferencia entre compras y ventas (solo si es positiva)
            merma_kg = max(0, compras_kg - ventas_kg)
            merma_pct = (merma_kg / compras_kg * 100) if compras_kg > 0 else 0
            
            # Stock teórico = merma (simplificación; en realidad necesitaríamos stock inicial)
            stock_teorico_kg = merma_kg
            
            # Valorización del stock teórico (usando precio promedio de compras)
            precio_promedio_compra = compras_monto / compras_kg if compras_kg > 0 else 0
            stock_teorico_valor = stock_teorico_kg * precio_promedio_compra
            
            # Precio promedio de venta
            precio_promedio_venta = ventas_monto / ventas_kg if ventas_kg > 0 else 0
            
            resultado.append({
                'tipo_fruta': datos['tipo_fruta'],
                'manejo': datos['manejo'],
                'compras_kg': round(compras_kg, 2),
                'compras_monto': round(compras_monto, 2),
                'precio_promedio_compra': round(precio_promedio_compra, 2),
                'ventas_kg': round(ventas_kg, 2),
                'ventas_monto': round(ventas_monto, 2),
                'precio_promedio_venta': round(precio_promedio_venta, 2),
                'merma_kg': round(merma_kg, 2),
                'merma_pct': round(merma_pct, 2),
                'stock_teorico_kg': round(stock_teorico_kg, 2),
                'stock_teorico_valor': round(stock_teorico_valor, 2)
            })
        
        return sorted(resultado, key=lambda x: -x['compras_kg'])
    
    def _generar_resumen_general(self, resultados_por_anio: Dict, pct_merma_historico: float) -> Dict:
        """Genera resumen consolidado de todos los años."""
        total_compras_kg = 0
        total_compras_monto = 0
        total_ventas_kg = 0
        total_ventas_monto = 0
        total_merma_kg = 0
        total_stock_teorico_valor = 0
        
        for anio, data in resultados_por_anio.items():
            for item in data['datos']:
                total_compras_kg += item['compras_kg']
                total_compras_monto += item['compras_monto']
                total_ventas_kg += item['ventas_kg']
                total_ventas_monto += item['ventas_monto']
                total_merma_kg += item['merma_kg']
                total_stock_teorico_valor += item['stock_teorico_valor']
        
        return {
            'total_compras_kg': round(total_compras_kg, 2),
            'total_compras_monto': round(total_compras_monto, 2),
            'precio_promedio_compra_global': round(total_compras_monto / total_compras_kg, 2) if total_compras_kg > 0 else 0,
            'total_ventas_kg': round(total_ventas_kg, 2),
            'total_ventas_monto': round(total_ventas_monto, 2),
            'precio_promedio_venta_global': round(total_ventas_monto / total_ventas_kg, 2) if total_ventas_kg > 0 else 0,
            'total_merma_kg': round(total_merma_kg, 2),
            'pct_merma_historico': round(pct_merma_historico, 2),
            'total_stock_teorico_valor': round(total_stock_teorico_valor, 2)
        }
    
    def _generar_resumen_simple(self, datos: List[Dict]) -> Dict:
        """Genera resumen para un único rango de fechas."""
        total_compras_kg = 0
        total_compras_monto = 0
        total_ventas_kg = 0
        total_ventas_monto = 0
        total_merma_kg = 0
        total_stock_teorico_valor = 0
        
        for item in datos:
            total_compras_kg += item['compras_kg']
            total_compras_monto += item['compras_monto']
            total_ventas_kg += item['ventas_kg']
            total_ventas_monto += item['ventas_monto']
            total_merma_kg += item['merma_kg']
            total_stock_teorico_valor += item['stock_teorico_valor']
        
        return {
            'total_compras_kg': round(total_compras_kg, 2),
            'total_compras_monto': round(total_compras_monto, 2),
            'precio_promedio_compra_global': round(total_compras_monto / total_compras_kg, 2) if total_compras_kg > 0 else 0,
            'total_ventas_kg': round(total_ventas_kg, 2),
            'total_ventas_monto': round(total_ventas_monto, 2),
            'precio_promedio_venta_global': round(total_ventas_monto / total_ventas_kg, 2) if total_ventas_kg > 0 else 0,
            'total_merma_kg': round(total_merma_kg, 2),
            'total_stock_teorico_valor': round(total_stock_teorico_valor, 2)
        }
    
    def get_analisis_mensual(self, fecha_desde: str, fecha_hasta: str):
        """
        Análisis mes a mes de compras, ventas y merma.
        
        Args:
            fecha_desde: Fecha inicio en formato YYYY-MM-DD
            fecha_hasta: Fecha fin en formato YYYY-MM-DD
        
        Returns:
            List[Dict] con datos mensuales:
                - mes: YYYY-MM
                - compras_kg, compras_monto
                - ventas_kg, ventas_monto
                - merma_kg, merma_pct
        """
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        inicio = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fin = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        
        resultados = []
        fecha_actual = inicio.replace(day=1)  # Primer día del mes
        
        while fecha_actual <= fin:
            # Calcular último día del mes
            siguiente_mes = fecha_actual + relativedelta(months=1)
            ultimo_dia = siguiente_mes - relativedelta(days=1)
            
            # No pasar de la fecha final
            if ultimo_dia > fin:
                ultimo_dia = fin
            
            fecha_desde_mes = fecha_actual.strftime("%Y-%m-%d")
            fecha_hasta_mes = ultimo_dia.strftime("%Y-%m-%d")
            
            # Obtener compras del mes
            compras = self._get_compras_por_tipo_manejo(fecha_desde_mes, fecha_hasta_mes)
            ventas = self._get_ventas_por_tipo_manejo(fecha_desde_mes, fecha_hasta_mes)
            
            # Consolidar
            datos = self._consolidar_datos(compras, ventas)
            
            # Sumar totales del mes
            total_compras_kg = sum(d['compras_kg'] for d in datos)
            total_compras_monto = sum(d['compras_monto'] for d in datos)
            total_ventas_kg = sum(d['ventas_kg'] for d in datos)
            total_ventas_monto = sum(d['ventas_monto'] for d in datos)
            total_merma_kg = sum(d['merma_kg'] for d in datos)
            
            merma_pct = (total_merma_kg / total_compras_kg * 100) if total_compras_kg > 0 else 0
            
            resultados.append({
                'mes': fecha_actual.strftime("%Y-%m"),
                'compras_kg': round(total_compras_kg, 2),
                'compras_monto': round(total_compras_monto, 2),
                'ventas_kg': round(total_ventas_kg, 2),
                'ventas_monto': round(total_ventas_monto, 2),
                'merma_kg': round(total_merma_kg, 2),
                'merma_pct': round(merma_pct, 2)
            })
            
            fecha_actual = siguiente_mes
        
        return resultados
    
    def get_comparativa_anual(self, anio1: int, anio2: int):
        """
        Comparativa año vs año por tipo de fruta y manejo.
        
        Args:
            anio1: Año base (ej: 2024)
            anio2: Año a comparar (ej: 2025)
        
        Returns:
            List[Dict] con comparativa:
                - tipo_fruta, manejo
                - compras_kg_anio1, compras_kg_anio2, delta_compras_kg, delta_compras_pct
                - ventas_kg_anio1, ventas_kg_anio2, delta_ventas_kg, delta_ventas_pct
                - merma_pct_anio1, merma_pct_anio2, delta_merma_pct
        """
        # Temporada = nov año-1 a oct año
        fecha_desde_1 = f"{anio1 - 1}-11-01"
        fecha_hasta_1 = f"{anio1}-10-31"
        
        fecha_desde_2 = f"{anio2 - 1}-11-01"
        fecha_hasta_2 = f"{anio2}-10-31"
        
        # Si anio2 es el año actual, ajustar hasta hoy
        if anio2 == datetime.now().year:
            fecha_hasta_2 = datetime.now().strftime("%Y-%m-%d")
        
        # Obtener datos de ambos años
        compras_1 = self._get_compras_por_tipo_manejo(fecha_desde_1, fecha_hasta_1)
        ventas_1 = self._get_ventas_por_tipo_manejo(fecha_desde_1, fecha_hasta_1)
        datos_1 = self._consolidar_datos(compras_1, ventas_1)
        
        compras_2 = self._get_compras_por_tipo_manejo(fecha_desde_2, fecha_hasta_2)
        ventas_2 = self._get_ventas_por_tipo_manejo(fecha_desde_2, fecha_hasta_2)
        datos_2 = self._consolidar_datos(compras_2, ventas_2)
        
        # Crear índice por tipo+manejo
        map_1 = {f"{d['tipo_fruta']}||{d['manejo']}": d for d in datos_1}
        map_2 = {f"{d['tipo_fruta']}||{d['manejo']}": d for d in datos_2}
        
        # Unir todas las claves
        todas_keys = set(map_1.keys()) | set(map_2.keys())
        
        resultados = []
        for key in todas_keys:
            tipo, manejo = key.split('||')
            
            d1 = map_1.get(key, {'compras_kg': 0, 'ventas_kg': 0, 'merma_kg': 0})
            d2 = map_2.get(key, {'compras_kg': 0, 'ventas_kg': 0, 'merma_kg': 0})
            
            compras_1_kg = d1['compras_kg']
            compras_2_kg = d2['compras_kg']
            ventas_1_kg = d1['ventas_kg']
            ventas_2_kg = d2['ventas_kg']
            merma_1_kg = d1['merma_kg']
            merma_2_kg = d2['merma_kg']
            
            # Calcular deltas
            delta_compras_kg = compras_2_kg - compras_1_kg
            delta_compras_pct = ((compras_2_kg / compras_1_kg - 1) * 100) if compras_1_kg > 0 else 0
            
            delta_ventas_kg = ventas_2_kg - ventas_1_kg
            delta_ventas_pct = ((ventas_2_kg / ventas_1_kg - 1) * 100) if ventas_1_kg > 0 else 0
            
            merma_pct_1 = (merma_1_kg / compras_1_kg * 100) if compras_1_kg > 0 else 0
            merma_pct_2 = (merma_2_kg / compras_2_kg * 100) if compras_2_kg > 0 else 0
            delta_merma_pct = merma_pct_2 - merma_pct_1
            
            resultados.append({
                'tipo_fruta': tipo,
                'manejo': manejo,
                f'compras_kg_{anio1}': round(compras_1_kg, 2),
                f'compras_kg_{anio2}': round(compras_2_kg, 2),
                'delta_compras_kg': round(delta_compras_kg, 2),
                'delta_compras_pct': round(delta_compras_pct, 2),
                f'ventas_kg_{anio1}': round(ventas_1_kg, 2),
                f'ventas_kg_{anio2}': round(ventas_2_kg, 2),
                'delta_ventas_kg': round(delta_ventas_kg, 2),
                'delta_ventas_pct': round(delta_ventas_pct, 2),
                f'merma_pct_{anio1}': round(merma_pct_1, 2),
                f'merma_pct_{anio2}': round(merma_pct_2, 2),
                'delta_merma_pct': round(delta_merma_pct, 2)
            })
        
        return resultados
