"""
Módulo de queries a Odoo para Flujo de Caja.
Maneja todas las consultas a la base de datos de Odoo.
"""
from typing import Dict, List, Optional
from datetime import datetime


class OdooQueryManager:
    """Gestiona queries a Odoo para obtener datos contables."""
    
    def __init__(self, odoo_client):
        """
        Args:
            odoo_client: Instancia de OdooClient
        """
        self.odoo = odoo_client
    
    def get_cuentas_efectivo(self, prefijos: List[str] = None, codigos: List[str] = None) -> List[int]:
        """
        Obtiene los IDs de cuentas de efectivo.
        
        Args:
            prefijos: Lista de prefijos de código (ej: ['110', '111'])
            codigos: Lista de códigos específicos
            
        Returns:
            Lista de IDs de cuentas
        """
        if prefijos is None:
            prefijos = ['110', '111']
        if codigos is None:
            codigos = []
        
        # Construir dominio
        domain_parts = []
        
        # Agregar prefijos
        for prefijo in prefijos:
            domain_parts.append(['code', '=like', f'{prefijo}%'])
        
        # Agregar códigos específicos
        for codigo in codigos:
            domain_parts.append(['code', '=', codigo])
        
        # Combinar con OR
        if len(domain_parts) > 1:
            domain = ['|'] * (len(domain_parts) - 1) + domain_parts
        else:
            domain = domain_parts
        
        # Buscar cuentas
        cuentas = self.odoo.search_read(
            'account.account',
            domain,
            ['id', 'code', 'name']
        )
        
        return [c['id'] for c in cuentas] if cuentas else []
    
    def get_saldo_efectivo(self, fecha: str, cuentas_efectivo_ids: List[int]) -> float:
        """
        Obtiene el saldo de efectivo a una fecha específica.
        
        Args:
            fecha: Fecha en formato YYYY-MM-DD
            cuentas_efectivo_ids: IDs de cuentas de efectivo
            
        Returns:
            Saldo total de efectivo
        """
        if not cuentas_efectivo_ids:
            return 0.0
        
        # Consultar saldos
        saldos = self.odoo.search_read(
            'account.move.line',
            [
                ['account_id', 'in', cuentas_efectivo_ids],
                ['date', '<=', fecha],
                ['parent_state', '=', 'posted']
            ],
            ['debit', 'credit']
        )
        
        if not saldos:
            return 0.0
        
        # Calcular saldo
        total_debit = sum(s.get('debit', 0) for s in saldos)
        total_credit = sum(s.get('credit', 0) for s in saldos)
        
        return total_debit - total_credit
    
    def get_movimientos_periodo(self, fecha_inicio: str, fecha_fin: str, 
                                cuentas_efectivo_ids: List[int],
                                company_id: int = None) -> List[Dict]:
        """
        Obtiene movimientos contables del período que afectan efectivo.
        
        Args:
            fecha_inicio: Fecha inicio en formato YYYY-MM-DD
            fecha_fin: Fecha fin en formato YYYY-MM-DD
            cuentas_efectivo_ids: IDs de cuentas de efectivo
            company_id: ID de la compañía (opcional)
            
        Returns:
            Lista de movimientos contables
        """
        if not cuentas_efectivo_ids:
            return []
        
        # Dominio base
        domain = [
            ['date', '>=', fecha_inicio],
            ['date', '<=', fecha_fin],
            ['parent_state', '=', 'posted']
        ]
        
        # Filtrar por compañía si se especifica
        if company_id:
            domain.append(['company_id', '=', company_id])
        
        # Buscar asientos que tengan al menos una línea en cuentas de efectivo
        domain.append(['account_id', 'in', cuentas_efectivo_ids])
        
        # Obtener movimientos
        movimientos = self.odoo.search_read(
            'account.move.line',
            domain,
            ['id', 'move_id', 'account_id', 'partner_id', 'debit', 'credit', 
             'date', 'name', 'ref']
        )
        
        return movimientos or []
    
    def get_cuentas_contrapartida(self, move_ids: List[int], 
                                  excluir_cuenta_ids: List[int]) -> List[Dict]:
        """
        Obtiene las cuentas contrapartida de los movimientos.
        
        Args:
            move_ids: IDs de los movimientos contables
            excluir_cuenta_ids: IDs de cuentas a excluir (efectivo)
            
        Returns:
            Lista de líneas contrapartida
        """
        if not move_ids:
            return []
        
        # Obtener líneas contrapartida
        contrapartidas = self.odoo.search_read(
            'account.move.line',
            [
                ['move_id', 'in', move_ids],
                ['account_id', 'not in', excluir_cuenta_ids]
            ],
            ['id', 'move_id', 'account_id', 'debit', 'credit', 'name']
        )
        
        return contrapartidas or []
    
    def get_account_info_batch(self, account_ids: List[int]) -> Dict[int, Dict]:
        """
        Obtiene información de cuentas en batch.
        
        Args:
            account_ids: Lista de IDs de cuentas
            
        Returns:
            Diccionario {account_id: {code, name}}
        """
        if not account_ids:
            return {}
        
        cuentas = self.odoo.search_read(
            'account.account',
            [['id', 'in', list(set(account_ids))]],
            ['id', 'code', 'name']
        )
        
        return {
            c['id']: {'code': c.get('code', ''), 'name': c.get('name', '')}
            for c in (cuentas or [])
        }
    
    def get_facturas_periodo(self, fecha_inicio: str, fecha_fin: str,
                            company_id: int = None) -> List[Dict]:
        """
        Obtiene facturas del período para proyección.
        
        Args:
            fecha_inicio: Fecha inicio
            fecha_fin: Fecha fin
            company_id: ID de compañía
            
        Returns:
            Lista de facturas
        """
        domain = [
            ['invoice_date', '>=', fecha_inicio],
            ['invoice_date', '<=', fecha_fin],
            ['state', 'in', ['posted', 'draft']]
        ]
        
        if company_id:
            domain.append(['company_id', '=', company_id])
        
        facturas = self.odoo.search_read(
            'account.move',
            domain,
            ['id', 'name', 'invoice_date', 'invoice_date_due', 
             'amount_total', 'amount_residual', 'move_type', 'state']
        )
        
        return facturas or []
