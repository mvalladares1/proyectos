"""
Servicio de Reconciliación de Producción
==========================================

PROBLEMA RESUELTO:
- Una ODF puede consumir materiales de MÚLTIPLES SO en un flujo continuo
- Odoo registra los hechos (stock.move.line con SO)
- Este servicio INTERPRETA y RECONCILIA la realidad operativa

ARQUITECTURA:
- Lee datos atómicos de Odoo (vía API)
- Agrupa y analiza por ventanas lógicas
- Detecta transiciones automáticas entre SO
- Calcula eficiencias reales por pedido
- Expone datos limpios para dashboards

FUENTES DE VERDAD:
1. stock.move.line → consumos reales con timestamp
2. mrp.production → contexto de fabricación
3. sale.order → contexto comercial
4. x_studio_so_linea → trazabilidad SO→línea
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


class ProduccionReconciliador:
    """
    Reconcilia la producción continua con pedidos comerciales discretos.
    
    NO modifica Odoo.
    Solo lee, agrupa, analiza y explica.
    """
    
    def __init__(self, odoo_client):
        """
        Args:
            odoo_client: Cliente configurado de Odoo (shared.odoo_client)
        """
        self.odoo = odoo_client
    
    # ========================================
    # LECTURA DE DATOS ATÓMICOS DESDE ODOO
    # ========================================
    
    def get_consumos_odf(self, odf_id: int) -> List[Dict]:
        """
        Obtiene todos los consumos de una ODF con trazabilidad completa.
        Funciona con ODFs en cualquier estado (draft, confirmed, progress, to_close, done).
        
        LÓGICA:
        1. Intenta leer stock.move.line (detalle con x_studio_so_linea)
        2. Si no hay, lee stock.move (agregado sin SO específica)
        
        Returns:
            Lista de consumos con estructura:
            {
                'timestamp': datetime,
                'producto_id': int,
                'producto_nombre': str,
                'cantidad_planeada_kg': float,
                'cantidad_ejecutada_kg': float,
                'so_id': int,           # De x_studio_so_linea (solo en move.line)
                'so_nombre': str,
                'lote': str,
                'move_line_id': int,
                'state': str,
                'source': str           # 'move.line' o 'move'
            }
        """
        # Primero intentar leer stock.move.line (con detalle y SO)
        domain = [
            ['production_id', '=', odf_id]
        ]
        
        moves_line = self.odoo.search_read(
            'stock.move.line',
            domain,
            ['date', 'product_id', 'qty_done', 'product_uom_qty', 'lot_id', 'x_studio_so_linea', 'state']
        )
        
        # Si hay stock.move.line, usarlos (tienen x_studio_so_linea)
        if moves_line:
            consumos = []
            for move in moves_line:
                # Extraer SO de x_studio_so_linea
                so_info = self._extract_so_from_move(move)
                
                # Usar cantidad ejecutada si existe, sino la planeada
                qty_ejecutada = move.get('qty_done', 0)
                qty_planeada = move.get('product_uom_qty', 0)
                
                consumos.append({
                    'timestamp': move.get('date'),
                    'producto_id': move['product_id'][0] if move.get('product_id') else None,
                    'producto_nombre': move['product_id'][1] if move.get('product_id') else 'Desconocido',
                    'cantidad_planeada_kg': qty_planeada,
                    'cantidad_ejecutada_kg': qty_ejecutada,
                    'cantidad_kg': qty_ejecutada if qty_ejecutada > 0 else qty_planeada,
                    'so_id': so_info['id'],
                    'so_nombre': so_info['nombre'],
                    'lote': move['lot_id'][1] if move.get('lot_id') else None,
                    'move_line_id': move['id'],
                    'state': move.get('state', 'unknown'),
                    'source': 'move.line'
                })
            
            return sorted(consumos, key=lambda x: x['timestamp'] or '')
        
        # Si NO hay stock.move.line, leer stock.move (sin SO específica)
        else:
            moves = self.odoo.search_read(
                'stock.move',
                [['raw_material_production_id', '=', odf_id]],
                ['date', 'product_id', 'product_uom_qty', 'quantity_done', 'state']
            )
            
            consumos = []
            for move in moves:
                qty_ejecutada = move.get('quantity_done', 0)
                qty_planeada = move.get('product_uom_qty', 0)
                
                consumos.append({
                    'timestamp': move.get('date'),
                    'producto_id': move['product_id'][0] if move.get('product_id') else None,
                    'producto_nombre': move['product_id'][1] if move.get('product_id') else 'Desconocido',
                    'cantidad_planeada_kg': qty_planeada,
                    'cantidad_ejecutada_kg': qty_ejecutada,
                    'cantidad_kg': qty_ejecutada if qty_ejecutada > 0 else qty_planeada,
                    'so_id': None,  # No hay SO específica en stock.move
                    'so_nombre': 'Sin SO asignada (nivel agregado)',
                    'lote': None,
                    'move_line_id': move['id'],
                    'state': move.get('state', 'unknown'),
                    'source': 'move'
                })
            
            return sorted(consumos, key=lambda x: x['timestamp'] or '')
    
    def _extract_so_from_move(self, move: Dict) -> Dict[str, Any]:
        """
        Extrae información de SO desde x_studio_so_linea.
        
        x_studio_so_linea es Many2one a sale_order_line.
        Necesitamos obtener el sale_order padre.
        """
        so_line_field = move.get('x_studio_so_linea')
        
        if not so_line_field:
            return {'id': None, 'nombre': 'Sin SO'}
        
        # x_studio_so_linea viene como tupla (id, display_name)
        if isinstance(so_line_field, (list, tuple)) and len(so_line_field) >= 2:
            so_line_id = so_line_field[0]
            
            # Buscar la sale_order_line para obtener su order_id
            so_line = self.odoo.search_read(
                'sale.order.line',
                [['id', '=', so_line_id]],
                ['order_id']
            )
            
            if so_line and so_line[0].get('order_id'):
                # order_id viene como (id, name)
                order_info = so_line[0]['order_id']
                return {
                    'id': order_info[0] if isinstance(order_info, (list, tuple)) else order_info,
                    'nombre': order_info[1] if isinstance(order_info, (list, tuple)) else f'SO#{order_info}',
                    'so_line_id': so_line_id
                }
        
        elif isinstance(so_line_field, int):
            # Si viene solo el ID
            so_line = self.odoo.search_read(
                'sale.order.line',
                [['id', '=', so_line_field]],
                ['order_id']
            )
            
            if so_line and so_line[0].get('order_id'):
                order_info = so_line[0]['order_id']
                return {
                    'id': order_info[0] if isinstance(order_info, (list, tuple)) else order_info,
                    'nombre': order_info[1] if isinstance(order_info, (list, tuple)) else f'SO#{order_info}',
                    'so_line_id': so_line_field
                }
        
        return {'id': None, 'nombre': 'Sin SO asignada'}
    
    # ========================================
    # DETECCIÓN DE TRANSICIONES ENTRE SO
    # ========================================
    
    def detectar_transiciones_so(self, consumos: List[Dict]) -> List[Dict]:
        """
        Detecta automáticamente dónde termina una SO y empieza otra
        en un flujo continuo.
        
        ALGORITMO:
        1. Agrupa consumos consecutivos de la misma SO
        2. Detecta cambios de SO
        3. Calcula ventanas de tiempo por SO
        4. Identifica solapamientos (si existen)
        
        Returns:
            Lista de segmentos:
            {
                'so_id': int,
                'so_nombre': str,
                'inicio': datetime,
                'fin': datetime,
                'duracion_minutos': float,
                'kg_total': float,
                'consumos_count': int,
                'productos': dict  # {producto: kg}
            }
        """
        if not consumos:
            return []
        
        segmentos = []
        current_so = None
        current_segment = None
        
        for consumo in consumos:
            so_id = consumo['so_id']
            
            # Cambio de SO o primer consumo
            if so_id != current_so:
                # Cerrar segmento anterior
                if current_segment:
                    segmentos.append(current_segment)
                
                # Iniciar nuevo segmento
                current_so = so_id
                current_segment = {
                    'so_id': so_id,
                    'so_nombre': consumo['so_nombre'],
                    'inicio': consumo['timestamp'],
                    'fin': consumo['timestamp'],
                    'kg_total': 0,
                    'consumos_count': 0,
                    'productos': defaultdict(float)
                }
            
            # Agregar consumo al segmento actual
            current_segment['fin'] = consumo['timestamp']
            current_segment['kg_total'] += consumo['cantidad_kg']
            current_segment['consumos_count'] += 1
            current_segment['productos'][consumo['producto_nombre']] += consumo['cantidad_kg']
        
        # Cerrar último segmento
        if current_segment:
            segmentos.append(current_segment)
        
        # Calcular duraciones
        for seg in segmentos:
            if seg['inicio'] and seg['fin']:
                delta = seg['fin'] - seg['inicio']
                seg['duracion_minutos'] = delta.total_seconds() / 60
            else:
                seg['duracion_minutos'] = 0
            
            # Convertir defaultdict a dict normal
            seg['productos'] = dict(seg['productos'])
        
        return segmentos
    
    # ========================================
    # ANÁLISIS Y MÉTRICAS
    # ========================================
    
    def analizar_eficiencia_por_so(
        self, 
        segmentos: List[Dict],
        odf_info: Dict
    ) -> List[Dict]:
        """
        Calcula métricas de eficiencia por cada SO.
        
        Args:
            segmentos: Segmentos detectados (de detectar_transiciones_so)
            odf_info: Info de la ODF (producido total, tiempos, etc)
        
        Returns:
            Análisis por SO:
            {
                'so_nombre': str,
                'kg_consumidos': float,
                'kg_producidos_estimado': float,  # Prorrateado
                'eficiencia_%': float,
                'tiempo_minutos': float,
                'velocidad_kg_h': float,
                'porcentaje_odf': float
            }
        """
        total_kg_consumidos = sum(s['kg_total'] for s in segmentos)
        total_producido = odf_info.get('kg_producidos', 0)
        
        analisis = []
        
        for seg in segmentos:
            kg_consumidos = seg['kg_total']
            
            # Prorratear producción según consumo
            proporcion = kg_consumidos / total_kg_consumidos if total_kg_consumidos > 0 else 0
            kg_producidos_est = total_producido * proporcion
            
            # Eficiencia
            eficiencia = (kg_producidos_est / kg_consumidos * 100) if kg_consumidos > 0 else 0
            
            # Velocidad
            horas = seg['duracion_minutos'] / 60 if seg['duracion_minutos'] > 0 else 0
            velocidad = kg_producidos_est / horas if horas > 0 else 0
            
            analisis.append({
                'so_id': seg['so_id'],
                'so_nombre': seg['so_nombre'],
                'kg_consumidos': round(kg_consumidos, 2),
                'kg_producidos_estimado': round(kg_producidos_est, 2),
                'eficiencia_%': round(eficiencia, 2),
                'tiempo_minutos': round(seg['duracion_minutos'], 2),
                'velocidad_kg_h': round(velocidad, 2),
                'porcentaje_odf': round(proporcion * 100, 2),
                'inicio': seg['inicio'],
                'fin': seg['fin']
            })
        
        return analisis
    
    # ========================================
    # RECONCILIACIÓN COMPLETA
    # ========================================
    
    def reconciliar_odf(self, odf_id: int) -> Dict:
        """
        Proceso completo de reconciliación de una ODF.
        
        Returns:
            {
                'odf_id': int,
                'odf_nombre': str,
                'producto_principal': str,        # Puede ser placeholder
                'subproductos': [...],            # Productos REALES producidos
                'consumos_raw': [...],            # Datos atómicos
                'segmentos_so': [...],            # Transiciones detectadas
                'analisis_so': [...],             # Métricas por SO
                'alertas': [...],                 # Problemas detectados
                'resumen': {...}                  # Stats generales
            }
        """
        # 1. Leer ODF de Odoo
        odf = self.odoo.search_read(
            'mrp.production',
            [['id', '=', odf_id]],
            ['name', 'product_id', 'product_qty', 'qty_produced', 'date_start', 'date_finished']
        )[0]
        
        # 2. Leer subproductos (finished products)
        subproductos = self.odoo.search_read(
            'stock.move',
            [
                ['production_id', '=', odf_id],
                ['location_dest_id.usage', '=', 'internal']
            ],
            ['product_id', 'product_uom_qty', 'quantity_done']
        )
        
        subproductos_info = [
            {
                'producto_id': sp['product_id'][0] if sp.get('product_id') else None,
                'producto_nombre': sp['product_id'][1] if sp.get('product_id') else 'Desconocido',
                'cantidad_planeada': sp.get('product_uom_qty', 0),
                'cantidad_producida': sp.get('quantity_done', 0)
            }
            for sp in subproductos
        ]
        
        # Total producido real (suma de subproductos)
        total_producido_real = sum(sp.get('quantity_done', 0) for sp in subproductos)
        
        # 3. Leer consumos atómicos
        consumos = self.get_consumos_odf(odf_id)
        
        # 4. Detectar transiciones entre SO
        segmentos = self.detectar_transiciones_so(consumos)
        
        # 5. Analizar eficiencia por SO (usar total producido real)
        odf_info = {
            'kg_producidos': total_producido_real or odf.get('qty_produced', 0)
        }
        analisis = self.analizar_eficiencia_por_so(segmentos, odf_info)
        
        # 6. Generar alertas
        alertas = self._generar_alertas(segmentos, analisis, odf)
        
        # 7. Resumen
        total_consumido = sum(s['kg_total'] for s in segmentos)
        resumen = {
            'total_so': len(segmentos),
            'total_kg_consumidos': total_consumido,
            'total_kg_producidos': odf_info['kg_producidos'],
            'eficiencia_global_%': (odf_info['kg_producidos'] / total_consumido * 100) 
                                   if total_consumido > 0 else 0,
            'so_dominante': max(segmentos, key=lambda x: x['kg_total'])['so_nombre'] if segmentos else None,
            'subproductos_count': len(subproductos_info)
        }
        
        return {
            'odf_id': odf_id,
            'odf_nombre': odf.get('name'),
            'producto_principal': odf['product_id'][1] if odf.get('product_id') else 'N/A',
            'subproductos': subproductos_info,
            'consumos_raw': consumos,
            'segmentos_so': segmentos,
            'analisis_so': analisis,
            'alertas': alertas,
            'resumen': resumen,
            'timestamp_analisis': datetime.now()
        }
    
    def _generar_alertas(
        self, 
        segmentos: List[Dict], 
        analisis: List[Dict],
        odf: Dict
    ) -> List[Dict]:
        """
        Detecta situaciones anómalas o importantes.
        """
        alertas = []
        
        # Alerta: Sin SO asignadas (datos desde stock.move agregado)
        if len(segmentos) == 1 and segmentos[0].get('so_id') is None:
            alertas.append({
                'tipo': 'WARNING',
                'mensaje': 'ODF sin SO asignadas a nivel de detalle',
                'detalle': 'Los datos vienen de stock.move (agregado). Los digitadores deben asignar x_studio_so_linea en stock.move.line para trazabilidad completa.'
            })
        
        # Alerta: Múltiples SO en una ODF
        if len(segmentos) > 1:
            alertas.append({
                'tipo': 'INFO',
                'mensaje': f'ODF con {len(segmentos)} SO diferentes',
                'detalle': ', '.join([s['so_nombre'] for s in segmentos])
            })
        
        # Alerta: Eficiencia muy baja
        for analisis_so in analisis:
            if analisis_so['eficiencia_%'] < 70:
                alertas.append({
                    'tipo': 'WARNING',
                    'mensaje': f"Eficiencia baja en {analisis_so['so_nombre']}: {analisis_so['eficiencia_%']}%",
                    'so_id': analisis_so['so_id']
                })
        
        # Alerta: SO muy corta (menos de 30 min)
        for seg in segmentos:
            if seg.get('duracion_minutos', 0) < 30 and seg.get('so_id'):  # Solo para SO reales
                alertas.append({
                    'tipo': 'INFO',
                    'mensaje': f"Segmento corto: {seg['so_nombre']} ({seg['duracion_minutos']:.0f} min)",
                    'so_id': seg['so_id']
                })
        
        return alertas


# ========================================
# FUNCIÓN DE AYUDA PARA STREAMLIT
# ========================================

def crear_reconciliador(username: str, password: str):
    """
    Factory para crear reconciliador con conexión a Odoo.
    
    Uso en Streamlit:
        reconciliador = crear_reconciliador(username, password)
        resultado = reconciliador.reconciliar_odf(123)
    """
    from shared.odoo_client import OdooClient
    
    odoo = OdooClient()
    odoo.authenticate(username, password)
    
    return ProduccionReconciliador(odoo)
