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
        
        # Asegurar enteros en exclusión
        if cuentas_efectivo_ids:
            try:
                cuentas_efectivo_ids = [int(x) for x in cuentas_efectivo_ids if str(x).isdigit()]
            except:
                pass
        
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
    
    def get_lineas_cuenta_periodo(self, account_codes: List[str], 
                                 fecha_inicio: str, fecha_fin: str) -> List[Dict]:
        """
        Obtiene líneas de cuentas CxC usando x_studio_fecha_de_pago como ÚNICO criterio.
        
        LÓGICA DE FECHA DE PAGO:
        - Si el move tiene x_studio_fecha_de_pago → usa ESA fecha
        - Si NO tiene x_studio_fecha_de_pago → usa date (fecha contable) como fallback
        
        Esto permite que facturas de Agosto con pago acordado en Sept aparezcan en Sept,
        y facturas de Sept con pago en Octubre NO aparezcan en Sept.
        
        IMPORTANTE: Cada línea devuelta incluye 'fecha_efectiva' = la fecha que determina
        en qué período se muestra (fecha_pago si existe, sino fecha contable).
        
        FILTROS APLICADOS:
        - Solo FACTURAS DE CLIENTE (out_invoice, out_refund)
        
        REGLA DE BORRADORES:
        - Del PASADO: Solo publicados (excluir borradores)
        - Del PERÍODO ACTUAL: Incluir borradores para proyección
        """
        if not account_codes:
            return []
            
        try:
            # 1. Obtener IDs de cuentas
            cuentas = self.odoo.search_read(
                'account.account',
                [['code', 'in', account_codes]],
                ['id', 'code']
            )
            account_ids = [c['id'] for c in cuentas]
            
            if not account_ids:
                return []
            
            print(f"[CxC Query] Buscando para cuentas {account_codes} en período {fecha_inicio} a {fecha_fin}")
                
            # 2. Buscar MOVES que cumplan criterios:
            #    - FACTURAS DE CLIENTE (out_invoice, out_refund)
            #    - PUBLICADOS: cualquier fecha que caiga en rango
            #    - BORRADORES: solo si su fecha está DENTRO del período (proyección)
            #
            # Lógica: (posted AND fecha_en_rango) OR (draft AND fecha_en_rango)
            # Simplificado: fecha_en_rango AND (posted OR draft)
            # Facturas publicadas con fecha en rango
            # Usamos payment_state para identificar proyección (pendientes de cobro)
            # payment_state: not_paid, in_payment, partial = PROYECCIÓN (no cobradas)
            # payment_state: paid, reversed = YA COBRADAS (historial)
            
            domain_moves = [
                ['move_type', 'in', ['out_invoice', 'out_refund']],  # Solo facturas de cliente
                ['state', '=', 'posted'],  # Solo publicadas
                '|',
                # Caso A: Tiene fecha_de_pago en rango
                '&', '&',
                    ['x_studio_fecha_de_pago', '!=', False],
                    ['x_studio_fecha_de_pago', '>=', fecha_inicio],
                    ['x_studio_fecha_de_pago', '<=', fecha_fin],
                # Caso B: NO tiene fecha_de_pago, usar date contable en rango
                '&', '&',
                    ['x_studio_fecha_de_pago', '=', False],
                    ['date', '>=', fecha_inicio],
                    ['date', '<=', fecha_fin],
            ]
            
            moves = self.odoo.search_read(
                'account.move',
                domain_moves,
                ['id', 'name', 'x_studio_fecha_de_pago', 'date', 'move_type', 'state', 'payment_state', 'partner_id', 'amount_total', 'amount_residual']
            )
            
            # Crear diccionario de move_id -> (fecha_efectiva, es_proyeccion)
            # FECHA EFECTIVA = fecha_pago si existe, sino fecha contable
            # PROYECCIÓN = payment_state in ['not_paid', 'in_payment', 'partial']
            move_fecha_efectiva = {}
            move_info = {}  # Para guardar info adicional del move
            cobradas_count = 0
            proyeccion_count = 0
            
            ESTADOS_PROYECCION = ['not_paid', 'in_payment', 'partial']
            
            # Recopilar partner_ids para consulta de categorías
            partner_ids_set = set()
            
            for m in moves:
                fecha_pago = m.get('x_studio_fecha_de_pago')
                fecha_contable = m.get('date')
                payment_state = m.get('payment_state', 'not_paid')
                es_proyeccion = payment_state in ESTADOS_PROYECCION
                
                partner_data = m.get('partner_id', [0, 'Sin partner'])
                partner_id = partner_data[0] if isinstance(partner_data, (list, tuple)) and len(partner_data) > 0 else 0
                partner_name = partner_data[1] if isinstance(partner_data, (list, tuple)) and len(partner_data) > 1 else 'Sin partner'
                
                if partner_id:
                    partner_ids_set.add(partner_id)
                
                move_fecha_efectiva[m['id']] = fecha_pago if fecha_pago else fecha_contable
                move_info[m['id']] = {
                    'name': m.get('name'),
                    'payment_state': payment_state,
                    'es_proyeccion': es_proyeccion,
                    'partner_name': partner_name,
                    'partner_id': partner_id,
                    'amount_total': float(m.get('amount_total') or 0.0),
                    'amount_residual': float(m.get('amount_residual') or 0.0)
                }
                
                if es_proyeccion:
                    proyeccion_count += 1
                else:
                    cobradas_count += 1
            
            # Consultar categorías de contacto por partner (batch)
            # IMPORTANTE: Si el partner es un contacto hijo (invoice address, etc.),
            # buscar la categoría del PADRE
            partners_categorias = {}
            if partner_ids_set:
                try:
                    partners_data = self.odoo.search_read(
                        'res.partner',
                        [['id', 'in', list(partner_ids_set)]],
                        ['id', 'x_studio_categora_de_contacto', 'parent_id'],
                    )
                    
                    # Primera pasada: asignar categorías directas
                    partners_sin_cat = []  # Partners sin categoría que tienen parent
                    for p in partners_data:
                        cat = p.get('x_studio_categora_de_contacto', False)
                        parent = p.get('parent_id', False)
                        if isinstance(cat, (list, tuple)) and len(cat) > 1:
                            partners_categorias[p['id']] = cat[1]
                        elif isinstance(cat, str) and cat:
                            partners_categorias[p['id']] = cat
                        elif parent and isinstance(parent, (list, tuple)) and parent[0]:
                            # Sin categoría pero tiene padre → buscar del padre
                            partners_sin_cat.append((p['id'], parent[0]))
                        else:
                            partners_categorias[p['id']] = 'Sin Categoría'
                    
                    # Segunda pasada: buscar categorías de padres
                    if partners_sin_cat:
                        parent_ids = list(set(pid for _, pid in partners_sin_cat))
                        parents_data = self.odoo.search_read(
                            'res.partner',
                            [['id', 'in', parent_ids]],
                            ['id', 'x_studio_categora_de_contacto'],
                        )
                        parent_cats = {}
                        for pp in parents_data:
                            pcat = pp.get('x_studio_categora_de_contacto', False)
                            if isinstance(pcat, (list, tuple)) and len(pcat) > 1:
                                parent_cats[pp['id']] = pcat[1]
                            elif isinstance(pcat, str) and pcat:
                                parent_cats[pp['id']] = pcat
                        
                        for child_id, parent_id in partners_sin_cat:
                            partners_categorias[child_id] = parent_cats.get(parent_id, 'Sin Categoría')
                    
                    print(f"[CxC Query] Categorías asignadas: {len(partners_categorias)} partners, {len(partners_sin_cat)} heredaron del padre")
                except Exception as e:
                    print(f"[CxC Query] Error obteniendo categorías de partners: {e}")
            
            # Enriquecer move_info con categoría
            for mid, info in move_info.items():
                info['partner_categoria'] = partners_categorias.get(info.get('partner_id', 0), 'Sin Categoría')
            
            move_ids = list(move_fecha_efectiva.keys())
            
            print(f"[CxC Query] Encontrados {len(move_ids)} facturas cliente ({cobradas_count} cobradas, {proyeccion_count} pendientes/proyección)")
            
            if not move_ids:
                return []

            # 3. Buscar líneas de esos moves en las cuentas objetivo
            lineas = []
            chunk_size = 5000
            for i in range(0, len(move_ids), chunk_size):
                chunk = move_ids[i:i + chunk_size]
                domain_lines = [
                    ['account_id', 'in', account_ids],
                    ['move_id', 'in', chunk]
                ]
                
                chunk_lines = self.odoo.search_read(
                    'account.move.line',
                    domain_lines,
                    ['account_id', 'name', 'balance', 'date', 'move_id'],
                    limit=10000
                )
                lineas.extend(chunk_lines)
            
            print(f"[CxC Query] Encontradas {len(lineas)} líneas en cuentas CxC")
            
            # 4. Enriquecer cada línea con:
            #    - 'name': etiqueta (nombre del move/factura)
            #    - 'fecha_efectiva': fecha a usar para agrupar (fecha_pago o fecha_contable)
            #    - 'es_proyeccion': True si payment_state in [not_paid, in_payment, partial]
            #    - 'payment_state': estado de pago de la factura
            for linea in lineas:
                move_data = linea.get('move_id')
                move_id = move_data[0] if isinstance(move_data, (list, tuple)) else move_data
                move_name = move_data[1] if isinstance(move_data, (list, tuple)) else ''
                
                # Etiqueta: SIEMPRE usar nombre del move (factura) para nivel 3
                # Esto agrupa todas las líneas de una factura bajo su nombre
                if move_name:
                    label = move_name
                else:
                    label = linea.get('name', '') or 'Sin etiqueta'
                
                linea['name'] = label
                
                # FECHA EFECTIVA: usar la del move (fecha_pago si existe, sino fecha_contable)
                linea['fecha_efectiva'] = move_fecha_efectiva.get(move_id, linea.get('date'))
                
                # Info adicional del move para proyección
                info = move_info.get(move_id, {})
                linea['es_proyeccion'] = info.get('es_proyeccion', False)
                linea['payment_state'] = info.get('payment_state', 'not_paid')
                linea['partner_name'] = info.get('partner_name', 'Sin partner')
                linea['partner_categoria'] = info.get('partner_categoria', 'Sin Categoría')
                linea['amount_total'] = float(info.get('amount_total') or 0.0)
                linea['amount_residual'] = float(info.get('amount_residual') or 0.0)
            
            return lineas
        except Exception as e:
            print(f"[OdooQueryManager] Error obteniendo líneas CxC con fecha pago: {e}")
            import traceback
            traceback.print_exc()
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
        
        try:
            # Buscar líneas de los asientos en las cuentas especificadas
            # NO filtrar por journal_id para incluir todos los diarios (ventas, bancos, ajustes, etc.)
            domain = [
                ['move_id', 'in', asientos_ids],
                ['account_id', 'in', account_ids]
            ]
            
            # Usar search_read para obtener move_id (con nombre del asiento)
            lineas = self.odoo.search_read(
                'account.move.line',
                domain,
                ['account_id', 'name', 'balance', 'date', 'move_id'],
                limit=10000
            )
            
            # Agrupar manualmente
            agrupados = {}
            for linea in (lineas or []):
                acc_data = linea.get('account_id')
                if not acc_data: 
                    continue
                acc_id = acc_data[0] if isinstance(acc_data, (list, tuple)) else acc_data
                
                # Label: usar name de la línea, o si está vacío, usar move_id.name
                line_name = linea.get('name', '')
                move_data = linea.get('move_id')
                move_name = move_data[1] if isinstance(move_data, (list, tuple)) else ''
                
                label = line_name.strip() if line_name and line_name.strip() else move_name
                
                if not label:
                    label = 'Sin etiqueta'
                
                # Periodo
                fecha = linea.get('date', '')
                if agrupacion == 'semanal':
                    try:
                        from datetime import datetime
                        fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
                        y, w, d = fecha_dt.isocalendar()
                        period = f"{y}-W{w:02d}"
                    except:
                        continue
                else:
                    period = fecha[:7] if fecha else ''
                
                balance = linea.get('balance', 0)
                
                key = (acc_id, label, period)
                
                if key not in agrupados:
                    agrupados[key] = {
                        'account_id': acc_data,
                        'name': label,
                        'date:month': period if agrupacion == 'mensual' else None,
                        'date:week': period if agrupacion == 'semanal' else None,
                        'balance': balance
                    }
                else:
                    agrupados[key]['balance'] += balance
            
            return list(agrupados.values())
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
