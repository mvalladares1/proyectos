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
        """
        # Líneas de facturas de proveedor - SOLO diario "Facturas Proveedores"
        lineas = self.odoo.search_read(
            'account.move.line',
            [
                ['move_id.move_type', '=', 'in_invoice'],
                ['move_id.state', '=', 'posted'],
                ['move_id.journal_id.name', 'ilike', 'Facturas Proveedores'],
                ['product_id', '!=', False],
                ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTO'],
                ['date', '>=', fecha_desde],
                ['date', '<=', fecha_hasta],
                ['quantity', '>', 0],
                ['debit', '>', 0]
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
        
        productos = self.odoo.search_read(
            'product.product',
            [['id', 'in', prod_ids]],
            ['id', 'product_tmpl_id', 'categ_id'],
            limit=100000
        )
        
        print(f"[DEBUG COMPRAS] Productos únicos: {len(productos)}")
        
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
        
        # Obtener templates con campos tipo y manejo
        template_map = {}
        if template_ids:
            templates = self.odoo.search_read(
                'product.template',
                [['id', 'in', list(template_ids)]],
                ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
                limit=100000
            )
            
            for tmpl in templates:
                # Parsear tipo de fruta
                tipo = tmpl.get('x_studio_sub_categora')
                if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
                    tipo_str = tipo[1]
                elif isinstance(tipo, str) and tipo:
                    tipo_str = tipo
                else:
                    tipo_str = None
                
                # Parsear manejo
                manejo = tmpl.get('x_studio_categora_tipo_de_manejo')
                if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
                    manejo_str = manejo[1]
                elif isinstance(manejo, str) and manejo:
                    manejo_str = manejo
                else:
                    manejo_str = None
                
                template_map[tmpl['id']] = {
                    'nombre': tmpl.get('name', ''),
                    'tipo_fruta': tipo_str,
                    'manejo': manejo_str,
                    'tiene_ambos': bool(tipo_str and manejo_str)
                }
        
        # Mapear productos - MP + PSP (materia prima y semi-procesado que ENTRA)
        productos_map = {}
        productos_incluidos = 0
        productos_excluidos = 0
        
        for prod_id, prod_data in product_to_template.items():
            tmpl_id = prod_data['tmpl_id']
            categ = prod_data['categ']
            categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
            
            # MP + PSP (lo que entra a la empresa para procesar)
            es_compra = ('PRODUCTOS / MP' in categ_name or 
                        'PRODUCTOS / PSP' in categ_name)
            
            if tmpl_id in template_map:
                tmpl_info = template_map[tmpl_id]
                
                if es_compra:
                    # Incluir MP + PSP
                    # Si no tienen tipo/manejo, usar "Sin clasificar"
                    productos_map[prod_id] = {
                        'tipo_fruta': tmpl_info['tipo_fruta'] or 'Sin clasificar',
                        'manejo': tmpl_info['manejo'] or 'Sin clasificar',
                        'nombre': tmpl_info['nombre'],
                        'categoria': categ_name
                    }
                    productos_incluidos += 1
                else:
                    productos_excluidos += 1
        
        print(f"[DEBUG COMPRAS] Templates únicos: {len(template_ids)}")
        print(f"[DEBUG COMPRAS] Productos MP+PSP incluidos: {productos_incluidos}")
        print(f"[DEBUG COMPRAS] Productos excluidos: {productos_excluidos}")
        print(f"[DEBUG COMPRAS] Productos mapeados: {len(productos_map)}")
        
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
            agrupado[key]['monto'] += linea.get('debit', 0)
        
        return list(agrupado.values())
    
    def _get_ventas_por_tipo_manejo(self, fecha_desde: str, fecha_hasta: str) -> List[Dict]:
        """
        Obtiene ventas agrupadas por tipo de fruta y manejo.
        ACTUALIZADO: Usa product.template + filtra por diario "Facturas de Cliente" + categoría producto.
        """
        # Líneas de facturas de cliente - SOLO diario "Facturas de Cliente"
        lineas = self.odoo.search_read(
            'account.move.line',
            [
                ['move_id.move_type', '=', 'out_invoice'],
                ['move_id.state', '=', 'posted'],
                ['move_id.journal_id.name', 'ilike', 'Facturas de Cliente'],
                ['product_id', '!=', False],
                ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTO'],
                ['date', '>=', fecha_desde],
                ['date', '<=', fecha_hasta],
                ['quantity', '>', 0],
                ['credit', '>', 0]
            ],
            ['product_id', 'quantity', 'credit'],
            limit=100000
        )
        
        print(f"[DEBUG VENTAS] Fecha: {fecha_desde} a {fecha_hasta}")
        print(f"[DEBUG VENTAS] Líneas encontradas (diario Facturas de Cliente): {len(lineas)}")
        
        if not lineas:
            return []
        
        # Obtener product.product
        prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas if l.get('product_id')]))
        
        productos = self.odoo.search_read(
            'product.product',
            [['id', 'in', prod_ids]],
            ['id', 'product_tmpl_id', 'categ_id'],
            limit=100000
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
        
        # Obtener templates con campos tipo y manejo
        template_map = {}
        if template_ids:
            templates = self.odoo.search_read(
                'product.template',
                [['id', 'in', list(template_ids)]],
                ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
                limit=100000
            )
            
            for tmpl in templates:
                # Parsear tipo de fruta
                tipo = tmpl.get('x_studio_sub_categora')
                if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
                    tipo_str = tipo[1]
                elif isinstance(tipo, str) and tipo:
                    tipo_str = tipo
                else:
                    tipo_str = None
                
                # Parsear manejo
                manejo = tmpl.get('x_studio_categora_tipo_de_manejo')
                if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
                    manejo_str = manejo[1]
                elif isinstance(manejo, str) and manejo:
                    manejo_str = manejo
                else:
                    manejo_str = None
                
                template_map[tmpl['id']] = {
                    'nombre': tmpl.get('name', ''),
                    'tipo_fruta': tipo_str,
                    'manejo': manejo_str,
                    'tiene_ambos': bool(tipo_str and manejo_str)
                }
        
        # Mapear productos - PRODUCTOS terminados/semi-procesados que SALEN
        productos_map = {}
        productos_incluidos = 0
        productos_excluidos = 0
        
        for prod_id, prod_data in product_to_template.items():
            tmpl_id = prod_data['tmpl_id']
            categ = prod_data['categ']
            categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
            
            # Todo lo que sea PRODUCTOS (PTT, PSP, RETAIL, JUGO, etc.) - excluir solo MP
            es_venta = 'PRODUCTOS' in categ_name.upper() and 'PRODUCTOS / MP' not in categ_name
            
            if tmpl_id in template_map:
                tmpl_info = template_map[tmpl_id]
                
                if es_venta:
                    # Incluir todos los productos terminados/procesados que venden
                    # Si no tienen tipo/manejo, usar "Sin clasificar"
                    productos_map[prod_id] = {
                        'tipo_fruta': tmpl_info['tipo_fruta'] or 'Sin clasificar',
                        'manejo': tmpl_info['manejo'] or 'Sin clasificar',
                        'nombre': tmpl_info['nombre'],
                        'categoria': categ_name
                    }
                    productos_incluidos += 1
                else:
                    productos_excluidos += 1
        
        print(f"[DEBUG VENTAS] Templates únicos: {len(template_ids)}")
        print(f"[DEBUG VENTAS] Productos incluidos: {productos_incluidos}")
        print(f"[DEBUG VENTAS] Productos excluidos: {productos_excluidos}")
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
            agrupado[key]['monto'] += linea.get('credit', 0)
        
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

