"""
Módulo de cálculo de REAL/PROYECTADO/PPTO para Flujo de Caja.

Calcula los valores para las columnas especiales:
- REAL: Valores efectivamente realizados (pagados/cobrados)
- PROYECTADO: Valores pendientes (adeudado)
- PPTO: Presupuesto (vacío por ahora, se alimentará después)

Conceptos soportados:
- 1.2.1: Pagos a proveedores (diario Facturas de Proveedores)
- 1.2.6: IVA Exportador (cuenta 11060108 con partner Tesorería)
"""
from typing import Dict, List, Tuple
from collections import defaultdict
from datetime import datetime


class RealProyectadoCalculator:
    """Calculadora de valores REAL/PROYECTADO/PPTO."""
    
    # IDs conocidos de Odoo
    CUENTA_IVA_EXPORTADOR_CODE = '11060108'
    PARTNER_TESORERIA_ID = 10
    
    def __init__(self, odoo_client):
        """
        Args:
            odoo_client: Instancia de OdooClient
        """
        self.odoo = odoo_client
        self._cuenta_iva_id = None
    
    def _get_cuenta_iva_id(self) -> int:
        """Obtiene el ID de la cuenta IVA Exportador."""
        if self._cuenta_iva_id is None:
            try:
                cuentas = self.odoo.search_read(
                    'account.account',
                    [['code', '=', self.CUENTA_IVA_EXPORTADOR_CODE]],
                    ['id'],
                    limit=1
                )
                self._cuenta_iva_id = cuentas[0]['id'] if cuentas else None
            except Exception as e:
                print(f"[RealProyectado] Error buscando cuenta IVA: {e}")
                self._cuenta_iva_id = None
        return self._cuenta_iva_id
    
    def calcular_pagos_proveedores(self, fecha_inicio: str, fecha_fin: str) -> Dict:
        """
        Calcula REAL y PROYECTADO para 1.2.1 - Pagos a proveedores.
        
        LÓGICA:
        - REAL = Monto efectivamente pagado (amount_total - amount_residual)
        - PROYECTADO = Monto pendiente de pago (amount_residual)
        
        Considera:
        - Facturas de proveedor (in_invoice)
        - Notas de crédito (in_refund) con signo invertido
        - Todos los estados (paid, partial, not_paid, reversed)
        
        Args:
            fecha_inicio: Fecha inicio YYYY-MM-DD
            fecha_fin: Fecha fin YYYY-MM-DD
            
        Returns:
            Dict con {
                'real': float,
                'proyectado': float,
                'ppto': float,
                'real_por_mes': {mes: float},
                'proyectado_por_mes': {mes: float},
                'detalle': [...]
            }
        """
        try:
            # Buscar facturas de proveedor
            facturas = self.odoo.search_read(
                'account.move',
                [
                    ['move_type', 'in', ['in_invoice', 'in_refund']],
                    ['date', '>=', fecha_inicio],
                    ['date', '<=', fecha_fin],
                    ['state', '=', 'posted']
                ],
                ['id', 'name', 'move_type', 'date', 'amount_total', 
                 'amount_residual', 'payment_state', 'partner_id'],
                limit=5000
            )
            
            real_total = 0.0
            proyectado_total = 0.0
            real_por_mes = defaultdict(float)
            proyectado_por_mes = defaultdict(float)
            detalle = []
            
            for f in facturas:
                fecha = f.get('date', '')
                if not fecha:
                    continue
                    
                mes = fecha[:7]  # YYYY-MM
                
                amount_total = f.get('amount_total', 0) or 0
                amount_residual = f.get('amount_residual', 0) or 0
                move_type = f.get('move_type', '')
                
                # Nota de crédito invierte el signo
                signo = -1 if move_type == 'in_refund' else 1
                
                # REAL = lo efectivamente pagado
                pagado = (amount_total - amount_residual) * signo
                
                # PROYECTADO = lo que falta por pagar
                pendiente = amount_residual * signo
                
                real_total += pagado
                proyectado_total += pendiente
                
                real_por_mes[mes] += pagado
                proyectado_por_mes[mes] += pendiente
                
                # Guardar detalle para debugging
                if len(detalle) < 50:
                    detalle.append({
                        'name': f['name'],
                        'tipo': move_type,
                        'total': amount_total,
                        'pagado': pagado,
                        'pendiente': pendiente,
                        'mes': mes
                    })
            
            # Los pagos a proveedores son SALIDAS de efectivo (negativo en flujo)
            return {
                'real': -real_total,  # Negativo porque es salida
                'proyectado': -proyectado_total,  # Negativo porque es salida
                'ppto': 0.0,
                'real_por_mes': {k: -v for k, v in dict(real_por_mes).items()},
                'proyectado_por_mes': {k: -v for k, v in dict(proyectado_por_mes).items()},
                'detalle': detalle,
                'facturas_count': len(facturas)
            }
            
        except Exception as e:
            print(f"[RealProyectado] Error calculando pagos proveedores: {e}")
            return {
                'real': 0.0,
                'proyectado': 0.0,
                'ppto': 0.0,
                'real_por_mes': {},
                'proyectado_por_mes': {},
                'error': str(e)
            }
    
    def calcular_iva_exportador(self, fecha_inicio: str, fecha_fin: str) -> Dict:
        """
        Calcula REAL y PROYECTADO para 1.2.6 - IVA Exportador.
        
        LÓGICA:
        - REAL = Devoluciones de IVA recibidas (créditos en cuenta 11060108)
        - Solo cuando el partner es "Tesorería General de la República"
        - PROYECTADO = 0 por ahora (podría ser solicitudes pendientes)
        
        Args:
            fecha_inicio: Fecha inicio YYYY-MM-DD
            fecha_fin: Fecha fin YYYY-MM-DD
            
        Returns:
            Dict con estructura similar a calcular_pagos_proveedores
        """
        cuenta_iva_id = self._get_cuenta_iva_id()
        
        if not cuenta_iva_id:
            return {
                'real': 0.0,
                'proyectado': 0.0,
                'ppto': 0.0,
                'real_por_mes': {},
                'proyectado_por_mes': {},
                'error': 'Cuenta IVA Exportador no encontrada'
            }
        
        try:
            # Buscar movimientos de la cuenta con el partner específico
            movimientos = self.odoo.search_read(
                'account.move.line',
                [
                    ['account_id', '=', cuenta_iva_id],
                    ['partner_id', '=', self.PARTNER_TESORERIA_ID],
                    ['parent_state', '=', 'posted'],
                    ['date', '>=', fecha_inicio],
                    ['date', '<=', fecha_fin]
                ],
                ['id', 'move_id', 'date', 'name', 'credit', 'debit'],
                limit=500
            )
            
            real_total = 0.0
            real_por_mes = defaultdict(float)
            detalle = []
            
            for m in movimientos:
                fecha = m.get('date', '')
                if not fecha:
                    continue
                    
                mes = fecha[:7]
                
                # Para IVA Exportador, los CRÉDITOS son devoluciones recibidas
                # (entrada de efectivo = positivo)
                credit = m.get('credit', 0) or 0
                
                real_total += credit
                real_por_mes[mes] += credit
                
                if len(detalle) < 20:
                    detalle.append({
                        'name': m.get('name', ''),
                        'credit': credit,
                        'fecha': fecha,
                        'mes': mes
                    })
            
            return {
                'real': real_total,  # Positivo porque es entrada
                'proyectado': 0.0,  # Por ahora vacío
                'ppto': 0.0,
                'real_por_mes': dict(real_por_mes),
                'proyectado_por_mes': {},
                'detalle': detalle,
                'movimientos_count': len(movimientos)
            }
            
        except Exception as e:
            print(f"[RealProyectado] Error calculando IVA exportador: {e}")
            return {
                'real': 0.0,
                'proyectado': 0.0,
                'ppto': 0.0,
                'real_por_mes': {},
                'proyectado_por_mes': {},
                'error': str(e)
            }
    
    def calcular_todos(self, fecha_inicio: str, fecha_fin: str) -> Dict[str, Dict]:
        """
        Calcula REAL/PROYECTADO para todos los conceptos configurados.
        
        Args:
            fecha_inicio: Fecha inicio
            fecha_fin: Fecha fin
            
        Returns:
            Dict {concepto_id: {real, proyectado, ppto, ...}}
        """
        resultados = {}
        
        # 1.2.1 - Pagos a proveedores
        print(f"[RealProyectado] Calculando 1.2.1 - Pagos a proveedores...")
        resultados['1.2.1'] = self.calcular_pagos_proveedores(fecha_inicio, fecha_fin)
        
        # 1.2.6 - IVA Exportador
        print(f"[RealProyectado] Calculando 1.2.6 - IVA Exportador...")
        resultados['1.2.6'] = self.calcular_iva_exportador(fecha_inicio, fecha_fin)
        
        return resultados
    
    def enriquecer_concepto(self, concepto: Dict, 
                           real_proyectado_data: Dict,
                           concepto_id: str) -> Dict:
        """
        Enriquece un concepto con datos de REAL/PROYECTADO.
        
        Args:
            concepto: Dict del concepto existente
            real_proyectado_data: Resultado de calcular_todos()
            concepto_id: ID del concepto (ej: '1.2.1')
            
        Returns:
            Concepto enriquecido con campos real, proyectado, ppto
        """
        if concepto_id in real_proyectado_data:
            data = real_proyectado_data[concepto_id]
            concepto['real'] = data.get('real', 0)
            concepto['proyectado'] = data.get('proyectado', 0)
            concepto['ppto'] = data.get('ppto', 0)
            concepto['real_por_mes'] = data.get('real_por_mes', {})
            concepto['proyectado_por_mes'] = data.get('proyectado_por_mes', {})
        else:
            # Concepto sin datos especiales - usar el total existente como REAL
            # y PROYECTADO = 0
            concepto['real'] = concepto.get('total', 0)
            concepto['proyectado'] = 0
            concepto['ppto'] = 0
            concepto['real_por_mes'] = concepto.get('montos_por_mes', {})
            concepto['proyectado_por_mes'] = {}
        
        return concepto
