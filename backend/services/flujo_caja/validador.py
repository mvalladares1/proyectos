"""
Módulo de validación y diagnóstico para Flujo de Caja.
Maneja validación de flujos y diagnóstico de cuentas no clasificadas.
"""
from typing import Dict, List, Optional
from collections import defaultdict


class ValidadorFlujo:
    """Valida y diagnostica flujos de efectivo."""
    
    def __init__(self, clasificador, catalogo: Dict):
        """
        Args:
            clasificador: Instancia de ClasificadorCuentas
            catalogo: Catálogo de conceptos NIIF
        """
        self.clasificador = clasificador
        self.catalogo = catalogo
    
    def validar_flujo(self, flujos_por_linea: Dict, 
                     saldo_inicial: float, 
                     saldo_final: float) -> Dict:
        """
        Valida la cuadratura del flujo de efectivo.
        
        Args:
            flujos_por_linea: Diccionario de flujos por concepto
            saldo_inicial: Saldo inicial de efectivo
            saldo_final: Saldo final de efectivo
            
        Returns:
            Resultado de validación con estado y diferencias
        """
        from .constants import CATEGORIA_UNCLASSIFIED, CATEGORIA_PENDIENTE, CATEGORIA_FX_EFFECT
        
        # Calcular totales por actividad
        total_operacion = 0.0
        total_inversion = 0.0
        total_financiamiento = 0.0
        total_fx = 0.0
        total_pendiente = 0.0
        total_unclassified = 0.0
        
        conceptos = self.catalogo.get('conceptos', [])
        
        for concepto_id, monto in flujos_por_linea.items():
            concepto = next((c for c in conceptos if c.get('id') == concepto_id), None)
            
            if not concepto:
                if concepto_id == CATEGORIA_FX_EFFECT:
                    total_fx += monto
                elif concepto_id == CATEGORIA_PENDIENTE:
                    total_pendiente += monto
                elif concepto_id == CATEGORIA_UNCLASSIFIED:
                    total_unclassified += monto
                continue
            
            actividad = concepto.get('actividad', '')
            
            if actividad == 'operacion':
                total_operacion += monto
            elif actividad == 'inversion':
                total_inversion += monto
            elif actividad == 'financiamiento':
                total_financiamiento += monto
        
        # Variación neta calculada
        variacion_calculada = total_operacion + total_inversion + total_financiamiento + total_fx
        
        # Variación real
        variacion_real = saldo_final - saldo_inicial
        
        # Diferencia
        diferencia = variacion_real - variacion_calculada
        
        # Estado
        cuadra = abs(diferencia) < 1.0  # Tolerancia de 1 peso
        
        return {
            'cuadra': cuadra,
            'saldo_inicial': round(saldo_inicial, 2),
            'saldo_final': round(saldo_final, 2),
            'variacion_real': round(variacion_real, 2),
            'variacion_calculada': round(variacion_calculada, 2),
            'diferencia': round(diferencia, 2),
            'actividades': {
                'operacion': round(total_operacion, 2),
                'inversion': round(total_inversion, 2),
                'financiamiento': round(total_financiamiento, 2),
                'fx_effect': round(total_fx, 2)
            },
            'pendientes': {
                'pendiente_clasificar': round(total_pendiente, 2),
                'no_clasificado': round(total_unclassified, 2)
            }
        }
    
    def diagnosticar_no_clasificados(self, movimientos_detalle: List[Dict],
                                    cuentas_info: Dict[int, Dict] = None) -> Dict:
        """
        Genera diagnóstico de cuentas no clasificadas.
        
        Args:
            movimientos_detalle: Lista de movimientos con clasificación
            cuentas_info: Información adicional de cuentas
            
        Returns:
            Diagnóstico con cuentas no clasificadas y sugerencias
        """
        from .constants import CATEGORIA_UNCLASSIFIED, CATEGORIA_PENDIENTE
        
        # Filtrar no clasificados
        no_clasificados = [
            m for m in movimientos_detalle 
            if m.get('concepto_id') in [CATEGORIA_UNCLASSIFIED, CATEGORIA_PENDIENTE]
        ]
        
        if not no_clasificados:
            return {
                'total_cuentas': 0,
                'total_monto': 0,
                'cuentas': [],
                'sugerencias_mapeo': {}
            }
        
        # Agrupar por cuenta
        cuentas_agrupadas = defaultdict(lambda: {'monto_total': 0, 'movimientos': 0, 'nombre': ''})
        
        for mov in no_clasificados:
            codigo = mov.get('account_code', '')
            cuentas_agrupadas[codigo]['monto_total'] += mov.get('monto', 0)
            cuentas_agrupadas[codigo]['movimientos'] += 1
            if not cuentas_agrupadas[codigo]['nombre'] and mov.get('account_name'):
                cuentas_agrupadas[codigo]['nombre'] = mov.get('account_name', '')
        
        # Ordenar por monto absoluto
        cuentas_ordenadas = sorted(
            [
                {
                    'codigo': k,
                    'nombre': v['nombre'],
                    'monto_total': round(v['monto_total'], 2),
                    'movimientos': v['movimientos']
                }
                for k, v in cuentas_agrupadas.items()
            ],
            key=lambda x: abs(x['monto_total']),
            reverse=True
        )
        
        # Generar sugerencias
        sugerencias = {}
        for cuenta in cuentas_ordenadas:
            codigo = cuenta['codigo']
            sugerencia = self.clasificador.sugerir_categoria_por_prefijo(
                codigo, 
                cuenta['nombre']
            )
            sugerencias[codigo] = {
                'nombre': cuenta['nombre'],
                'monto': cuenta['monto_total'],
                'sugerencia': sugerencia,
                'prefijo': codigo[:2] if len(codigo) >= 2 else codigo
            }
        
        total_monto = sum(abs(c['monto_total']) for c in cuentas_ordenadas)
        
        return {
            'total_cuentas': len(cuentas_ordenadas),
            'total_monto': round(total_monto, 2),
            'cuentas': cuentas_ordenadas[:50],  # Top 50
            'sugerencias_mapeo': sugerencias
        }
    
    def identificar_anomalias(self, flujos_agregados: List[Dict]) -> List[Dict]:
        """
        Identifica posibles anomalías en los flujos.
        
        Args:
            flujos_agregados: Flujos agregados por concepto
            
        Returns:
            Lista de anomalías detectadas
        """
        anomalias = []
        
        # Buscar montos inusuales
        for flujo in flujos_agregados:
            monto = flujo.get('monto', 0)
            nombre = flujo.get('nombre', '')
            
            # Anomalía 1: Montos muy grandes en operación
            if abs(monto) > 100000000:  # 100M
                anomalias.append({
                    'tipo': 'monto_alto',
                    'concepto': nombre,
                    'monto': monto,
                    'descripcion': f'Monto inusualmente alto: {monto:,.0f}'
                })
            
            # Anomalía 2: Flujos negativos donde deberían ser positivos
            actividad = flujo.get('actividad', '')
            if actividad == 'operacion' and 'cobros' in nombre.lower() and monto < 0:
                anomalias.append({
                    'tipo': 'signo_invertido',
                    'concepto': nombre,
                    'monto': monto,
                    'descripcion': 'Cobros con monto negativo (revisar)'
                })
        
        return anomalias
