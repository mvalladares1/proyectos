"""
Módulo de queries a Odoo para Flujo de Caja.
Maneja todas las consultas a la base de datos de Odoo.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class OdooQueryManager:
    """Gestiona queries a Odoo para obtener datos contables."""
    
    def __init__(self, odoo_client):
        """
        Args:
            odoo_client: Instancia de OdooClient
        """
        self.odoo = odoo_client
        self._cache_cuentas_efectivo = None
    
    def get_cuentas_efectivo(self, config: Dict = None) -> List[int]:
        """
        Obtiene los IDs de cuentas de efectivo basado en configuración.
        
        Args:
            config: Configuración de cuentas efectivo {
                "efectivo": {"prefijos": [], "codigos_incluir": [], "codigos_excluir": []},
                "equivalentes": {...}
            }
            
        Returns:
            Lista de IDs de cuentas de efectivo
        """
        if self._cache_cuentas_efectivo:
            return self._cache_cuentas_efectivo
        
        if config is None:
            config = {}
        
        # Recopilar todos los prefijos, incluir y excluir de ambos tipos
        all_prefijos = []
        all_incluir = []
        all_excluir = []
        
        for tipo in ["efectivo", "equivalentes"]:
            tipo_config = config.get(tipo, {})
            all_prefijos.extend(tipo_config.get("prefijos", []))
            all_incluir.extend(tipo_config.get("codigos_incluir", []))
            all_excluir.extend(tipo_config.get("codigos_excluir", []))
        
        # Fallback para estructura anterior
        if not all_prefijos and "prefijos" in config:
            all_prefijos = config.get("prefijos", ["110", "111"])
        
        if not all_prefijos:
            all_prefijos = ["110", "111"]
        
        # Construir dominio OR para prefijos
        domain = ['|'] * (len(all_prefijos) - 1) if len(all_prefijos) > 1 else []
        for prefijo in all_prefijos:
            domain.append(['code', '=like', f'{prefijo}%'])
        
        try:
            cuentas = self.odoo.search_read(
                'account.account',
                domain,
                ['id', 'code', 'name'],
                limit=200
            )
            
            # Aplicar lógica de override: excluir > incluir > prefijos
            resultado_ids = []
            codigos_encontrados = set()
            
            for c in cuentas:
                codigo = c.get('code', '')
                # Excluir tiene prioridad máxima
                if codigo in all_excluir:
                    continue
                resultado_ids.append(c['id'])
                codigos_encontrados.add(codigo)
            
            # Agregar codigos_incluir que no fueron encontrados por prefijo
            codigos_faltantes = [c for c in all_incluir if c not in codigos_encontrados]
            if codigos_faltantes:
                try:
                    cuentas_extra = self.odoo.search_read(
                        'account.account',
                        [['code', 'in', codigos_faltantes]],
                        ['id', 'code'],
                        limit=50
                    )
                    for c in cuentas_extra:
                        if c.get('code') not in all_excluir:
                            resultado_ids.append(c['id'])
                except:
                    pass
            
            self._cache_cuentas_efectivo = resultado_ids
            return self._cache_cuentas_efectivo
        except Exception as e:
            print(f"[OdooQueryManager] Error obteniendo cuentas efectivo: {e}")
            return []
    
    def get_saldo_efectivo(self, fecha: str, cuentas_efectivo_ids: List[int]) -> float:
        """
        Obtiene el saldo de efectivo a una fecha específica usando agregación server-side.
        
        Args:
            fecha: Fecha en formato YYYY-MM-DD
            cuentas_efectivo_ids: IDs de cuentas de efectivo
            
        Returns:
            Saldo total de efectivo
        """
        if not cuentas_efectivo_ids:
            return 0.0
        
        try:
            # OPTIMIZADO: Usar read_group para agregar en servidor
            result = self.odoo.models.execute_kw(
                self.odoo.db, self.odoo.uid, self.odoo.password,
                'account.move.line', 'read_group',
                [[
                    ['account_id', 'in', cuentas_efectivo_ids],
                    ['parent_state', '=', 'posted'],
                    ['date', '<=', fecha]
                ]],
                {'fields': ['balance:sum'], 'groupby': [], 'lazy': False}
            )
            
            if result and len(result) > 0:
                return result[0].get('balance', 0) or 0.0
            return 0.0
        except Exception as e:
            # Fallback al método anterior si read_group no está disponible
            print(f"[OdooQueryManager] read_group failed, using fallback: {e}")
            try:
                moves = self.odoo.search_read(
                    'account.move.line',
                    [
                        ['account_id', 'in', cuentas_efectivo_ids],
                        ['parent_state', '=', 'posted'],
                        ['date', '<=', fecha]
                    ],
                    ['balance'],
                    limit=50000
                )
                return sum(m.get('balance', 0) for m in moves)
            except:
                return 0.0
    
    def get_movimientos_efectivo_periodo(self, fecha_inicio: str, fecha_fin: str, 
                                         cuentas_efectivo_ids: List[int],
                                         company_id: int = None,
                                         incluir_draft: bool = False) -> Tuple[List[Dict], List[int]]:
        """
        Obtiene movimientos de cuentas de efectivo y sus IDs de asiento.
        
        Args:
            fecha_inicio: Fecha inicio YYYY-MM-DD
            fecha_fin: Fecha fin YYYY-MM-DD
            cuentas_efectivo_ids: IDs de cuentas de efectivo
            company_id: ID de compañía (opcional)
            incluir_draft: Si incluir asientos en borrador
            
        Returns:
            Tuple (movimientos, asientos_ids)
        """
        if not cuentas_efectivo_ids:
            return [], []
        
        states = ['posted', 'draft'] if incluir_draft else ['posted']
        
        domain = [
            ['account_id', 'in', cuentas_efectivo_ids],
            ['parent_state', 'in', states],
            ['date', '>=', fecha_inicio],
            ['date', '<=', fecha_fin]
        ]
        if company_id:
            domain.append(['company_id', '=', company_id])
        
        try:
            movimientos = self.odoo.search_read(
                'account.move.line',
                domain,
                ['move_id', 'date', 'name', 'ref', 'balance', 'account_id', 'partner_id'],
                limit=50000,
                order='date desc'
            )
            
            # Extraer IDs únicos de asientos
            asientos_ids = list(set(
                m['move_id'][0] if isinstance(m.get('move_id'), (list, tuple)) else m.get('move_id')
                for m in movimientos if m.get('move_id')
            ))
            
            return movimientos, asientos_ids
        except Exception as e:
            print(f"[OdooQueryManager] Error obteniendo movimientos: {e}")
            return [], []
    
    def get_contrapartidas_agrupadas(self, asientos_ids: List[int], 
                                     cuentas_efectivo_ids: List[int],
                                     groupby_key: str = 'account_id') -> List[Dict]:
        """
        Obtiene contrapartidas agrupadas por cuenta usando read_group.
        
        Args:
            asientos_ids: IDs de asientos contables
            cuentas_efectivo_ids: IDs de cuentas de efectivo (para excluir)
            groupby_key: Campo de agrupación ('account_id' o 'date:month')
            
        Returns:
            Lista de grupos con balance agregado
        """
        if not asientos_ids:
            return []
        
        resultados = []
        chunk_size = 5000
        
        for i in range(0, len(asientos_ids), chunk_size):
            chunk = asientos_ids[i:i + chunk_size]
            
            try:
                grupos = self.odoo.models.execute_kw(
                    self.odoo.db, self.odoo.uid, self.odoo.password,
                    'account.move.line', 'read_group',
                    [[
                        ['move_id', 'in', chunk],
                        ['account_id', 'not in', cuentas_efectivo_ids]
                    ]],
                    {
                        'fields': ['balance', 'account_id'], 
                        'groupby': [groupby_key], 
                        'lazy': False
                    }
                )
                resultados.extend(grupos)
            except Exception as e:
                print(f"[OdooQueryManager] Error en read_group: {e}")
        
        return resultados
    
    def get_contrapartidas_agrupadas_mensual(self, asientos_ids: List[int],
                                             cuentas_efectivo_ids: List[int],
                                             agrupacion: str = 'mensual') -> List[Dict]:
        """
        Obtiene contrapartidas agrupadas por cuenta Y mes/semana.
        
        Args:
            asientos_ids: IDs de asientos
            cuentas_efectivo_ids: IDs de cuentas de efectivo (excluir)
            agrupacion: 'mensual' o 'semanal'
            
        Returns:
            Lista de grupos {account_id, date:month/week, balance}
        """
        if not asientos_ids:
            return []
        
        groupby_key = 'date:week' if agrupacion == 'semanal' else 'date:month'
        
        resultados = []
        chunk_size = 5000
        
        for i in range(0, len(asientos_ids), chunk_size):
            chunk = asientos_ids[i:i + chunk_size]
            
            try:
                grupos = self.odoo.models.execute_kw(
                    self.odoo.db, self.odoo.uid, self.odoo.password,
                    'account.move.line', 'read_group',
                    [[
                        ['move_id', 'in', chunk],
                        ['account_id', 'not in', cuentas_efectivo_ids]
                    ]],
                    {
                        'fields': ['balance', 'account_id', 'date'], 
                        'groupby': ['account_id', groupby_key],
                        'lazy': False
                    }
                )
                resultados.extend(grupos)
            except Exception as e:
                print(f"[OdooQueryManager] Error en read_group mensual: {e}")
        
        return resultados
    
    def get_facturas_draft(self, fecha_inicio: str, fecha_fin: str,
                          company_id: int = None) -> List[Dict]:
        """
        Obtiene facturas para proyección:
        - Facturas en borrador (draft)
        - Facturas posted con payment_state pendiente (not_paid, in_payment, partial)
        
        Args:
            fecha_inicio: Fecha inicio
            fecha_fin: Fecha fin
            company_id: ID de compañía
            
        Returns:
            Lista de facturas para proyección
        """
        # Dominio: draft O (posted con payment pendiente)
        # Usamos invoice_date_due para facturas pendientes
        domain = [
            ['move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']],
            '|',
            # Facturas draft
            ['state', '=', 'draft'],
            # Facturas posted pendientes de pago
            '&',
            ['state', '=', 'posted'],
            ['payment_state', 'in', ['not_paid', 'in_payment', 'partial']]
        ]
        
        if company_id:
            domain.append(['company_id', '=', company_id])
        
        # Filtro por fecha: usar invoice_date_due para proyección
        domain_con_fecha = domain + [
            '|',
            '&', ['invoice_date_due', '>=', fecha_inicio], ['invoice_date_due', '<=', fecha_fin],
            '&', ['date', '>=', fecha_inicio], ['date', '<=', fecha_fin]
        ]
        
        try:
            facturas = self.odoo.search_read(
                'account.move',
                domain_con_fecha,
                ['id', 'move_type', 'invoice_date', 'invoice_date_due', 'line_ids', 'date', 
                 'state', 'payment_state', 'amount_total', 'amount_residual'],
                limit=5000
            )
            return facturas or []
        except Exception as e:
            print(f"[OdooQueryManager] Error obteniendo facturas para proyección: {e}")
            return []
    
    def get_lineas_facturas(self, line_ids: List[int]) -> List[Dict]:
        """
        Obtiene líneas de factura por IDs.
        
        Args:
            line_ids: IDs de líneas
            
        Returns:
            Lista de líneas con account_id, balance, name
        """
        if not line_ids:
            return []
        
        try:
            lineas = self.odoo.search_read(
                'account.move.line',
                [['id', 'in', line_ids]],
                ['id', 'account_id', 'balance', 'debit', 'credit', 'move_id', 'name'],
                limit=50000
            )
            return lineas or []
        except Exception as e:
            print(f"[OdooQueryManager] Error obteniendo líneas: {e}")
            return []
    
    def get_lineas_cuentas_parametrizadas(self, codigos_cuentas: List[str],
                                          fecha_inicio: str, fecha_fin: str,
                                          excluir_asientos: List[int] = None) -> List[Dict]:
        """
        Obtiene líneas de cuentas parametrizadas que NO tocaron efectivo.
        
        Args:
            codigos_cuentas: Códigos de cuentas a buscar
            fecha_inicio: Fecha inicio
            fecha_fin: Fecha fin
            excluir_asientos: IDs de asientos a excluir (ya procesados)
            
        Returns:
            Lista de líneas
        """
        if not codigos_cuentas:
            return []
        
        domain = [
            ['account_id.code', 'in', codigos_cuentas],
            ['parent_state', '=', 'posted'],
            ['date', '>=', fecha_inicio],
            ['date', '<=', fecha_fin]
        ]
        
        if excluir_asientos:
            domain.append(['move_id', 'not in', excluir_asientos])
        
        try:
            lineas = self.odoo.search_read(
                'account.move.line',
                domain,
                ['account_id', 'name', 'balance', 'date'],
                limit=10000
            )
            return lineas or []
        except Exception as e:
            print(f"[OdooQueryManager] Error obteniendo líneas parametrizadas: {e}")
            return []
    
    def get_etiquetas_por_mes(self, asientos_ids: List[int],
                             account_ids: List[int],
                             agrupacion: str = 'mensual') -> List[Dict]:
        """
        Obtiene etiquetas (campo 'name') por cuenta y mes.
        
        Args:
            asientos_ids: IDs de asientos
            account_ids: IDs de cuentas
            agrupacion: 'mensual' o 'semanal'
            
        Returns:
            Lista de grupos {account_id, name, date:month, balance}
        """
        if not asientos_ids or not account_ids:
            return []
        
        groupby_key = 'date:week' if agrupacion == 'semanal' else 'date:month'
        
        try:
            grupos = self.odoo.models.execute_kw(
                self.odoo.db, self.odoo.uid, self.odoo.password,
                'account.move.line', 'read_group',
                [[
                    ['move_id', 'in', asientos_ids],
                    ['account_id', 'in', account_ids]
                ]],
                {
                    'fields': ['balance', 'account_id', 'name', 'date'],
                    'groupby': ['account_id', 'name', groupby_key],
                    'lazy': False
                }
            )
            return grupos or []
        except Exception as e:
            print(f"[OdooQueryManager] Error obteniendo etiquetas: {e}")
            return []
    
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
        
        try:
            cuentas = self.odoo.search_read(
                'account.account',
                [['id', 'in', list(set(account_ids))]],
                ['id', 'code', 'name']
            )
            
            return {
                c['id']: {'code': c.get('code', ''), 'name': c.get('name', '')}
                for c in (cuentas or [])
            }
        except Exception as e:
            print(f"[OdooQueryManager] Error obteniendo info cuentas: {e}")
            return {}
    
    def invalidar_cache(self):
        """Invalida el caché de cuentas de efectivo."""
        self._cache_cuentas_efectivo = None
