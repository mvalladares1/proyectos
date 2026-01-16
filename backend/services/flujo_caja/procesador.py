"""
Módulo de procesamiento de flujos de caja.
Maneja el cálculo y agregación de flujos según NIIF IAS 7.
"""
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


class FlujoProcesador:
    """Procesa y calcula flujos de efectivo."""
    
    def __init__(self, clasificador, catalogo: Dict):
        """
        Args:
            clasificador: Instancia de ClasificadorCuentas
            catalogo: Catálogo de conceptos NIIF
        """
        self.clasificador = clasificador
        self.catalogo = catalogo
    
    def procesar_movimientos(self, movimientos: List[Dict], 
                            cuentas_info: Dict[int, Dict],
                            cuentas_efectivo_ids: List[int]) -> Tuple[Dict[str, float], List[Dict]]:
        """
        Procesa movimientos contables y los clasifica por concepto.
        
        Args:
            movimientos: Lista de movimientos de efectivo
            cuentas_info: Información de cuentas {id: {code, name}}
            cuentas_efectivo_ids: IDs de cuentas de efectivo
            
        Returns:
            Tuple (montos_por_concepto, movimientos_detalle)
        """
        montos_por_concepto = defaultdict(float)
        movimientos_detalle = []
        
        # Agrupar por move_id
        moves_agrupados = defaultdict(list)
        for mov in movimientos:
            moves_agrupados[mov.get('move_id', [None])[0]].append(mov)
        
        # Procesar cada asiento
        for move_id, lineas in moves_agrupados.items():
            if not move_id:
                continue
            
            # Separar líneas de efectivo y contrapartida
            lineas_efectivo = [l for l in lineas if l.get('account_id', [None])[0] in cuentas_efectivo_ids]
            lineas_contra = [l for l in lineas if l.get('account_id', [None])[0] not in cuentas_efectivo_ids]
            
            # Calcular flujo neto de efectivo
            flujo_efectivo = sum(l.get('debit', 0) - l.get('credit', 0) for l in lineas_efectivo)
            
            if abs(flujo_efectivo) < 0.01:
                continue
            
            # Clasificar por cuenta contrapartida
            for linea_contra in lineas_contra:
                account_id = linea_contra.get('account_id', [None])[0]
                if not account_id:
                    continue
                
                cuenta = cuentas_info.get(account_id, {})
                codigo = cuenta.get('code', '')
                
                # Clasificar
                concepto_id, es_explicito = self.clasificador.clasificar_cuenta(codigo)
                
                # Calcular monto proporcional
                flujo_linea = linea_contra.get('debit', 0) - linea_contra.get('credit', 0)
                monto = -flujo_linea  # Invertir porque es contrapartida
                
                # Acumular
                montos_por_concepto[concepto_id] += monto
                
                # Guardar detalle
                movimientos_detalle.append({
                    'move_id': move_id,
                    'account_code': codigo,
                    'account_name': cuenta.get('name', ''),
                    'concepto_id': concepto_id,
                    'monto': monto,
                    'fecha': lineas_efectivo[0].get('date') if lineas_efectivo else '',
                    'es_explicito': es_explicito
                })
        
        return dict(montos_por_concepto), movimientos_detalle
    
    def aggregate_by_ias7(self, montos_por_concepto: Dict[str, float],
                         incluir_intermedios: bool = False) -> List[Dict]:
        """
        Agrega montos según la estructura jerárquica IAS 7.
        
        Args:
            montos_por_concepto: Diccionario {concepto_id: monto}
            incluir_intermedios: Si incluir conceptos intermedios sin monto directo
            
        Returns:
            Lista de conceptos con montos agregados
        """
        from .helpers import aggregate_montos_by_concepto
        
        return aggregate_montos_by_concepto(
            montos_por_concepto,
            self.catalogo.get('conceptos', []),
            incluir_intermedios
        )
    
    def calcular_variacion_neta(self, flujos_agregados: List[Dict]) -> float:
        """
        Calcula la variación neta del efectivo.
        
        Args:
            flujos_agregados: Lista de flujos agregados
            
        Returns:
            Variación neta total
        """
        from .constants import ESTRUCTURA_FLUJO
        
        # Sumar actividades principales
        total = 0.0
        for actividad_key in ['operacion', 'inversion', 'financiamiento']:
            actividad = next((f for f in flujos_agregados if f.get('id') == actividad_key), None)
            if actividad:
                total += actividad.get('monto', 0)
        
        return total
    
    def generar_periodos(self, fecha_inicio: str, fecha_fin: str, 
                        agrupacion: str = 'mensual') -> List[Tuple[str, str, str]]:
        """
        Genera períodos para análisis temporal.
        
        Args:
            fecha_inicio: Fecha inicio YYYY-MM-DD
            fecha_fin: Fecha fin YYYY-MM-DD
            agrupacion: 'mensual', 'semanal', 'diario'
            
        Returns:
            Lista de tuplas (periodo_label, fecha_inicio, fecha_fin)
        """
        periodos = []
        inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
        
        if agrupacion == 'mensual':
            current = inicio.replace(day=1)
            while current <= fin:
                # Último día del mes
                if current.month == 12:
                    next_month = current.replace(year=current.year + 1, month=1)
                else:
                    next_month = current.replace(month=current.month + 1)
                
                ultimo_dia = next_month - timedelta(days=1)
                
                # Ajustar a rango
                periodo_inicio = max(current, inicio)
                periodo_fin = min(ultimo_dia, fin)
                
                label = current.strftime('%Y-%m')
                periodos.append((label, periodo_inicio.strftime('%Y-%m-%d'), periodo_fin.strftime('%Y-%m-%d')))
                
                current = next_month
        
        elif agrupacion == 'semanal':
            current = inicio
            while current <= fin:
                semana_fin = min(current + timedelta(days=6), fin)
                label = f"S{current.isocalendar()[1]}-{current.year}"
                periodos.append((label, current.strftime('%Y-%m-%d'), semana_fin.strftime('%Y-%m-%d')))
                current = semana_fin + timedelta(days=1)
        
        else:  # diario
            current = inicio
            while current <= fin:
                label = current.strftime('%Y-%m-%d')
                periodos.append((label, current.strftime('%Y-%m-%d'), current.strftime('%Y-%m-%d')))
                current += timedelta(days=1)
        
        return periodos
