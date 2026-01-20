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
    
    def get_analisis_multi_anual(self, anios: List[int], fecha_corte_mes_dia: str = "10-31"):
        """
        Análisis multi-anual de compras, ventas y stock teórico.
        
        Args:
            anios: Lista de años a analizar [2023, 2024, 2025, 2026]
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
        
        # Procesar cada año
        for anio in sorted(anios):
            fecha_desde = f"{anio}-01-01"
            
            # Si el año actual es mayor al corte, usar hasta el corte
            # Si no, usar hasta fin de año
            if anio < datetime.now().year:
                fecha_hasta = f"{anio}-{fecha_corte_mes_dia}"
            elif anio == datetime.now().year:
                # Año actual: hasta el corte o hasta hoy (lo que sea menor)
                fecha_corte_completa = f"{anio}-{fecha_corte_mes_dia}"
                fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                fecha_hasta = min(fecha_corte_completa, fecha_hoy)
            else:
                # Años futuros: hasta el corte
                fecha_hasta = f"{anio}-{fecha_corte_mes_dia}"
            
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
        """Obtiene compras agrupadas por tipo de fruta y manejo."""
        # Líneas de facturas de proveedor
        lineas = self.odoo.search_read(
            'account.move.line',
            [
                ['move_id.move_type', '=', 'in_invoice'],
                ['move_id.state', '=', 'posted'],
                ['product_id', '!=', False],
                ['date', '>=', fecha_desde],
                ['date', '<=', fecha_hasta],
                ['quantity', '>', 0],
                ['debit', '>', 0],
                ['account_id.code', '=like', '21%']
            ],
            ['product_id', 'quantity', 'debit'],
            limit=100000
        )
        
        if not lineas:
            return []
        
        # Obtener info de productos
        prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas if l.get('product_id')]))
        
        productos = self.odoo.search_read(
            'product.product',
            [['id', 'in', prod_ids]],
            ['id', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo', 'categ_id'],
            limit=100000
        )
        
        # Mapear productos con tipo y manejo
        productos_map = {}
        for prod in productos:
            categ = prod.get('categ_id')
            categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
            
            # Solo MP/PSP
            if 'PRODUCTOS / MP' in categ_name or 'PRODUCTOS / PSP' in categ_name:
                tipo = prod.get('x_studio_sub_categora')
                tipo_str = tipo[1] if isinstance(tipo, (list, tuple)) and len(tipo) > 1 else None
                
                manejo = prod.get('x_studio_categora_tipo_de_manejo')
                manejo_str = manejo[1] if isinstance(manejo, (list, tuple)) and len(manejo) > 1 else None
                
                if tipo_str and manejo_str:
                    productos_map[prod['id']] = {
                        'tipo_fruta': tipo_str,
                        'manejo': manejo_str
                    }
        
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
        """Obtiene ventas agrupadas por tipo de fruta y manejo (inferido desde PTT)."""
        # Líneas de facturas de cliente
        lineas = self.odoo.search_read(
            'account.move.line',
            [
                ['move_id.move_type', '=', 'out_invoice'],
                ['move_id.state', '=', 'posted'],
                ['product_id', '!=', False],
                ['date', '>=', fecha_desde],
                ['date', '<=', fecha_hasta],
                ['quantity', '>', 0],
                ['credit', '>', 0]
            ],
            ['product_id', 'quantity', 'credit'],
            limit=100000
        )
        
        if not lineas:
            return []
        
        # Obtener info de productos
        prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas if l.get('product_id')]))
        
        productos = self.odoo.search_read(
            'product.product',
            [['id', 'in', prod_ids]],
            ['id', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo', 'categ_id'],
            limit=100000
        )
        
        # Mapear productos con tipo y manejo
        productos_map = {}
        for prod in productos:
            categ = prod.get('categ_id')
            categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
            
            # Solo PTT/RETAIL/SUBPRODUCTO
            if any(x in categ_name for x in ['PRODUCTOS / PTT', 'PRODUCTOS / RETAIL', 'PRODUCTOS / SUBPRODUCTO']):
                tipo = prod.get('x_studio_sub_categora')
                tipo_str = tipo[1] if isinstance(tipo, (list, tuple)) and len(tipo) > 1 else None
                
                manejo = prod.get('x_studio_categora_tipo_de_manejo')
                manejo_str = manejo[1] if isinstance(manejo, (list, tuple)) and len(manejo) > 1 else None
                
                if tipo_str and manejo_str:
                    productos_map[prod['id']] = {
                        'tipo_fruta': tipo_str,
                        'manejo': manejo_str
                    }
        
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
