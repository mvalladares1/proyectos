"""
MÃ³dulo de agregaciÃ³n de flujos de caja.
Procesa y agrega movimientos por concepto y perÃ­odo.
"""
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import unicodedata


def _texto_orden_alfabetico(valor: str) -> str:
    """Normaliza texto para orden alfabético estable (sin acentos/símbolos)."""
    texto = str(valor or '').strip()
    texto = texto.replace('📁', '').replace('↳', '').strip()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(ch for ch in texto if not unicodedata.combining(ch))
    return texto.casefold()


class AgregadorFlujo:
    """Agrega flujos de efectivo por concepto y perÃ­odo."""
    
    def __init__(self, clasificador, catalogo: Dict, meses_lista: List[str]):
        """
        Args:
            clasificador: Instancia con mÃ©todo clasificar_cuenta()
            catalogo: CatÃ¡logo de conceptos NIIF
            meses_lista: Lista de perÃ­odos ['2026-01', '2026-02', ...]
        """
        self.clasificador = clasificador
        self.catalogo = catalogo
        self.meses_lista = meses_lista
        
        # Inicializar estructuras
        self.montos_por_concepto_mes = self._inicializar_montos()
        self.cuentas_por_concepto = {}  # {concepto_id: {codigo_cuenta: {...}}}
    
    def _inicializar_montos(self) -> Dict[str, Dict[str, float]]:
        """Inicializa estructura de montos por concepto y mes."""
        montos = {}
        for c in self.catalogo.get("conceptos", []):
            if c.get("tipo") == "LINEA":
                montos[c["id"]] = {m: 0.0 for m in self.meses_lista}
        return montos
    
    def procesar_grupos_contrapartida(self, grupos: List[Dict], 
                                      cuentas_monitoreadas: List[str] = None,
                                      parse_periodo_fn=None) -> None:
        """
        Procesa grupos de read_group y acumula por concepto/mes.
        
        Args:
            grupos: Resultado de read_group [{account_id, date:month, balance}, ...]
            cuentas_monitoreadas: CÃ³digos de cuentas a filtrar (None = todas)
            parse_periodo_fn: FunciÃ³n para parsear perÃ­odo Odoo a YYYY-MM
        """
        filtrar_monitoreadas = bool(cuentas_monitoreadas)
        
        for grupo in grupos:
            acc_data = grupo.get('account_id')
            balance = grupo.get('balance', 0)
            
            # Parsear perÃ­odo (mensual o semanal)
            periodo_val = grupo.get('date:month') or grupo.get('date:week', '')
            if not acc_data or not periodo_val:
                continue
            
            # Parsear mes
            if parse_periodo_fn:
                mes_str = parse_periodo_fn(periodo_val)
            else:
                mes_str = periodo_val
            
            if not mes_str or mes_str not in self.meses_lista:
                continue
            
            # Extraer cÃ³digo de cuenta del display "[code] name"
            acc_display = acc_data[1] if len(acc_data) > 1 else "Unknown"
            codigo_cuenta = acc_display.split(' ')[0] if ' ' in acc_display else acc_display
            
            # Filtrar por cuentas monitoreadas
            if filtrar_monitoreadas and codigo_cuenta not in cuentas_monitoreadas:
                continue
            
            # Clasificar cuenta
            concepto_id, es_pendiente = self.clasificador(codigo_cuenta)
            
            # Invertir signo para cuentas de ingreso (41) y costo (51)
            # En contabilidad: ingresos son crÃ©ditos (negativos), pero en flujo de efectivo
            # representan entradas de dinero (positivos)
            # TAMBIEN: Cuentas por cobrar (1103) que se acreditan al cobrar (entrada)
            monto_efectivo = balance
            if codigo_cuenta.startswith('41') or codigo_cuenta.startswith('1103'):
                monto_efectivo = -balance  # Invertir: crÃ©dito -> ingreso de efectivo
            
            # Acumular monto
            if concepto_id not in self.montos_por_concepto_mes:
                self.montos_por_concepto_mes[concepto_id] = {m: 0.0 for m in self.meses_lista}
            
            self.montos_por_concepto_mes[concepto_id][mes_str] += monto_efectivo
            
            # Trackear cuenta para drill-down
            self._agregar_cuenta(concepto_id, codigo_cuenta, acc_display, monto_efectivo, mes_str, acc_data[0])
    
    def _agregar_cuenta(self, concepto_id: str, codigo: str, display: str, 
                       monto: float, mes: str, account_id: int):
        """Agrega cuenta al tracking de concepto."""
        if concepto_id not in self.cuentas_por_concepto:
            self.cuentas_por_concepto[concepto_id] = {}
        
        if codigo not in self.cuentas_por_concepto[concepto_id]:
            nombre = display.split(' ', 1)[1] if ' ' in display else display
            self.cuentas_por_concepto[concepto_id][codigo] = {
                'nombre': nombre[:50],
                'monto': 0.0,
                'cantidad': 0,
                'montos_por_mes': {m: 0.0 for m in self.meses_lista},
                'etiquetas': {},
                'account_id': account_id
            }
        
        cuenta = self.cuentas_por_concepto[concepto_id][codigo]
        cuenta['monto'] += monto
        cuenta['cantidad'] += 1
        if mes in self.meses_lista:
            cuenta['montos_por_mes'][mes] += monto
    
    def procesar_etiquetas(self, grupos_etiquetas: List[Dict], 
                          parse_periodo_fn=None) -> None:
        """
        Procesa etiquetas (campo 'name') por cuenta y mes.
        
        Args:
            grupos_etiquetas: Resultado de read_group con name
            parse_periodo_fn: FunciÃ³n para parsear perÃ­odo
        """
        # Crear mapeo account_id â†’ (concepto_id, codigo_cuenta)
        account_id_to_codigo = {}
        for concepto_id, cuentas in self.cuentas_por_concepto.items():
            for codigo, cuenta_data in cuentas.items():
                if cuenta_data.get('account_id'):
                    account_id_to_codigo[cuenta_data['account_id']] = (concepto_id, codigo)
        
        for grupo in grupos_etiquetas:
            acc_data = grupo.get('account_id')
            etiqueta_name = grupo.get('name', '')
            balance = grupo.get('balance', 0)
            periodo_val = grupo.get('date:month') or grupo.get('date:week', '')
            
            if not acc_data or not etiqueta_name:
                continue
            
            account_id = acc_data[0] if isinstance(acc_data, (list, tuple)) else acc_data
            
            # Parsear perÃ­odo
            if parse_periodo_fn:
                mes_str = parse_periodo_fn(periodo_val)
            else:
                mes_str = periodo_val
            
            if account_id not in account_id_to_codigo:
                continue
            
            concepto_id, codigo_cuenta = account_id_to_codigo[account_id]
            
            # Limpiar nombre de etiqueta
            etiqueta_limpia = ' '.join(str(etiqueta_name).split())[:60] if etiqueta_name else "Sin etiqueta"
            
            # Asegurar estructura
            if 'etiquetas' not in self.cuentas_por_concepto[concepto_id][codigo_cuenta]:
                self.cuentas_por_concepto[concepto_id][codigo_cuenta]['etiquetas'] = {}
            
            etiquetas = self.cuentas_por_concepto[concepto_id][codigo_cuenta]['etiquetas']
            
            if etiqueta_limpia not in etiquetas:
                etiquetas[etiqueta_limpia] = {
                    'monto': 0.0,
                    'montos_por_mes': {m: 0.0 for m in self.meses_lista}
                }
            
            # Invertir signo si es cuenta de ingreso (41) o CxC (1103)
            monto_etiqueta = balance
            if codigo_cuenta.startswith('41') or codigo_cuenta.startswith('1103'):
                monto_etiqueta = -balance
            
            etiquetas[etiqueta_limpia]['monto'] += monto_etiqueta
            if mes_str and mes_str in self.meses_lista:
                etiquetas[etiqueta_limpia]['montos_por_mes'][mes_str] += monto_etiqueta
    
    def procesar_lineas_parametrizadas(self, lineas: List[Dict], 
                                       clasificar_fn,
                                       agrupacion: str = 'mensual') -> None:
        """
        Procesa lÃ­neas de cuentas parametrizadas.
        
        Args:
            lineas: LÃ­neas de account.move.line
            clasificar_fn: FunciÃ³n de clasificaciÃ³n
            agrupacion: 'mensual' o 'semanal'
        """
        for linea in lineas:
            acc_data = linea.get('account_id')
            if not acc_data:
                continue
            
            codigo_cuenta = acc_data[1].split(' ')[0] if ' ' in acc_data[1] else acc_data[1]
            balance = linea.get('balance', 0)
            fecha = linea.get('date', '')
            
            # Determinar perÃ­odo
            if agrupacion == 'semanal':
                try:
                    fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
                    y, w, d = fecha_dt.isocalendar()
                    mes_str = f"{y}-W{w:02d}"
                except:
                    continue
            else:
                mes_str = fecha[:7] if fecha else None
            
            if not mes_str or mes_str not in self.meses_lista:
                continue
            
            # Clasificar
            concepto_id, es_pendiente = clasificar_fn(codigo_cuenta)
            if concepto_id is None:
                continue
            
            # Acumular
            if concepto_id not in self.montos_por_concepto_mes:
                self.montos_por_concepto_mes[concepto_id] = {m: 0.0 for m in self.meses_lista}
            
            self.montos_por_concepto_mes[concepto_id][mes_str] += balance
            
            # Trackear cuenta
            self._agregar_cuenta(concepto_id, codigo_cuenta, acc_data[1], balance, mes_str, acc_data[0])
            
            # Agregar etiqueta
            etiqueta = linea.get('name', 'Sin descripciÃ³n')
            etiqueta_limpia = ' '.join(str(etiqueta).split())[:60] if etiqueta else "Sin etiqueta"
            
            cuenta = self.cuentas_por_concepto[concepto_id][codigo_cuenta]
            if 'etiquetas' not in cuenta:
                cuenta['etiquetas'] = {}
            
            if etiqueta_limpia not in cuenta['etiquetas']:
                cuenta['etiquetas'][etiqueta_limpia] = {
                    'monto': 0.0,
                    'montos_por_mes': {m: 0.0 for m in self.meses_lista}
                }
            
            cuenta['etiquetas'][etiqueta_limpia]['monto'] += balance
            if mes_str in self.meses_lista:
                cuenta['etiquetas'][etiqueta_limpia]['montos_por_mes'][mes_str] += balance
    
    def procesar_lineas_cxc(self, lineas: List[Dict], 
                           clasificar_fn,
                           agrupacion: str = 'mensual') -> None:
        """
        Procesa lÃ­neas de Cuentas por Cobrar (CxC) para flujo de caja proyectado.
        
        NUEVA ESTRUCTURA: Agrupa por ESTADO DE PAGO (payment_state) en lugar de facturas individuales.
        
        Nivel 2: Cuenta (11030101 - Deudores por Ventas)
        Nivel 3: Estado de Pago:
            - "Facturas Pagadas" (payment_state = 'paid')
            - "Facturas Parcialmente Pagadas" (payment_state = 'partial')
            - "En Proceso de Pago" (payment_state = 'in_payment')
            - "Facturas No Pagadas" (payment_state = 'not_paid')
        
        Cada estado incluye lista de facturas para modal drill-down.
        
        Args:
            lineas: LÃ­neas de account.move.line con fecha_efectiva y payment_state enriquecidos
            clasificar_fn: FunciÃ³n de clasificaciÃ³n
            agrupacion: 'mensual' o 'semanal'
        """
        # Mapeo de payment_state a etiqueta amigable
        ESTADO_LABELS = {
            'paid': 'Facturas Pagadas',
            'partial': 'Facturas Parcialmente Pagadas',
            'in_payment': 'En Proceso de Pago',
            'not_paid': 'Facturas No Pagadas'
            # 'reversed' se excluye completamente
        }
        
        # Orden de prioridad para mostrar estados
        ESTADO_ORDEN = ['paid', 'partial', 'in_payment', 'not_paid']
        
        # Agrupar líneas por factura primero para tener info completa
        facturas_por_move = {}  # {move_name: {payment_state, total, residual, fecha, lineas[]}}
        
        for linea in lineas:
            acc_data = linea.get('account_id')
            if not acc_data:
                continue
            
            codigo_cuenta = acc_data[1].split(' ')[0] if ' ' in acc_data[1] else acc_data[1]
            balance = linea.get('balance', 0)
            payment_state = linea.get('payment_state', 'not_paid')
            
            # EXCLUIR facturas revertidas completamente
            if payment_state == 'reversed':
                continue
            
            # Obtener nombre de factura
            move_data = linea.get('move_id', [0, ''])
            move_name = move_data[1] if isinstance(move_data, (list, tuple)) and len(move_data) > 1 else linea.get('name', 'Sin nombre')
            partner_name = linea.get('partner_name', 'Sin partner')
            
            # USAR FECHA_EFECTIVA (fecha pago si existe, sino fecha contable)
            fecha = linea.get('fecha_efectiva') or linea.get('date', '')
            
            # Determinar perÃ­odo basado en fecha_efectiva
            if agrupacion == 'semanal':
                try:
                    fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
                    y, w, d = fecha_dt.isocalendar()
                    mes_str = f"{y}-W{w:02d}"
                except:
                    continue
            else:
                mes_str = fecha[:7] if fecha else None
            
            if not mes_str or mes_str not in self.meses_lista:
                continue
            
            # Clasificar
            concepto_id, es_pendiente = clasificar_fn(codigo_cuenta)
            if concepto_id is None:
                continue
            
            # SIGNO PARA CxC en Flujo Proyectado
            monto_efectivo = balance
            
            # ===== NUEVA LÓGICA: Para PARCIALES, separar parte pagada y residual =====
            # Para facturas parcialmente pagadas: la parte ya cobrada va a "Pagadas"
            # y solo el residual queda en "Parcialmente Pagadas"
            amount_total_move = linea.get('amount_total', 0.0)
            amount_residual_move = linea.get('amount_residual', 0.0)
            
            monto_pagado_parcial = 0.0  # Parte pagada de facturas parciales → va a Pagadas
            
            if payment_state == 'partial' and amount_total_move > 0:
                # Calcular ratio para esta línea
                residual_ratio = amount_residual_move / amount_total_move
                monto_residual = balance * residual_ratio
                monto_pagado_parcial = balance - monto_residual  # Parte ya cobrada
                monto_efectivo = monto_residual  # Solo el residual va a PARCIALES
                print(f"[CxC SPLIT] partner={partner_name[:30]}, balance={balance}, amount_total={amount_total_move}, amount_residual={amount_residual_move}, ratio={residual_ratio:.3f}, residual→PARCIALES={monto_residual:.0f}, pagado→PAGADAS={monto_pagado_parcial:.0f}")
            elif payment_state == 'partial':
                print(f"[CxC SPLIT WARNING] partial pero amount_total=0! partner={partner_name[:30]}, balance={balance}, amount_total={amount_total_move}, amount_residual={amount_residual_move}")
            
            # Acumular
            if concepto_id not in self.montos_por_concepto_mes:
                self.montos_por_concepto_mes[concepto_id] = {m: 0.0 for m in self.meses_lista}
            
            self.montos_por_concepto_mes[concepto_id][mes_str] += monto_efectivo
            
            # Trackear cuenta
            self._agregar_cuenta(concepto_id, codigo_cuenta, acc_data[1], monto_efectivo, mes_str, acc_data[0])
            
            # Obtener o crear estructura de cuenta
            cuenta = self.cuentas_por_concepto[concepto_id][codigo_cuenta]
            if 'etiquetas' not in cuenta:
                cuenta['etiquetas'] = {}
            if 'facturas_por_estado' not in cuenta:
                cuenta['facturas_por_estado'] = {}
            
            # NUEVO: Agrupar por estado de pago como etiqueta
            estado_label = ESTADO_LABELS.get(payment_state, 'Otros')
            
            # Crear estructura para estado si no existe
            if estado_label not in cuenta['etiquetas']:
                cuenta['etiquetas'][estado_label] = {
                    'monto': 0.0,
                    'montos_por_mes': {m: 0.0 for m in self.meses_lista},
                    'orden': ESTADO_ORDEN.index(payment_state) if payment_state in ESTADO_ORDEN else 99
                }
            
            # Acumular monto en el estado
            cuenta['etiquetas'][estado_label]['monto'] += monto_efectivo
            if mes_str in self.meses_lista:
                cuenta['etiquetas'][estado_label]['montos_por_mes'][mes_str] += monto_efectivo
            
            # NUEVO: Guardar detalle de factura para modal
            if payment_state not in cuenta['facturas_por_estado']:
                cuenta['facturas_por_estado'][payment_state] = {}
            
            # Obtener move_id para link a Odoo
            move_id = move_data[0] if isinstance(move_data, (list, tuple)) and len(move_data) > 0 else None
            
            # Obtener categoría del partner
            partner_categoria = linea.get('partner_categoria', 'Sin Categoría')
            
            # Agrupar por PARTNER y mes (nivel 3)
            if partner_name not in cuenta['facturas_por_estado'][payment_state]:
                cuenta['facturas_por_estado'][payment_state][partner_name] = {
                    'nombre': partner_name,
                    'move_id': move_id,
                    'monto_total': 0.0,
                    'montos_por_mes': {m: 0.0 for m in self.meses_lista},
                    'fecha': fecha,
                    'payment_state': payment_state,
                    'categoria': partner_categoria,
                    'facturas': []
                }

            # Mantener detalle de factura para trazabilidad
            cuenta['facturas_por_estado'][payment_state][partner_name]['facturas'].append({
                'nombre': move_name,
                'move_id': move_id,
                'monto': monto_efectivo,
                'fecha': fecha
            })
            
            cuenta['facturas_por_estado'][payment_state][partner_name]['monto_total'] += monto_efectivo
            if mes_str in self.meses_lista:
                cuenta['facturas_por_estado'][payment_state][partner_name]['montos_por_mes'][mes_str] += monto_efectivo
            
            # ===== ACUMULAR PARTE PAGADA DE PARCIALES EN "Facturas Pagadas" =====
            if monto_pagado_parcial != 0:
                pagadas_label = ESTADO_LABELS['paid']  # "Facturas Pagadas"
                
                # Acumular en totales generales
                self.montos_por_concepto_mes[concepto_id][mes_str] += monto_pagado_parcial
                self._agregar_cuenta(concepto_id, codigo_cuenta, acc_data[1], monto_pagado_parcial, mes_str, acc_data[0])
                
                # Crear estructura para Pagadas si no existe
                if pagadas_label not in cuenta['etiquetas']:
                    cuenta['etiquetas'][pagadas_label] = {
                        'monto': 0.0,
                        'montos_por_mes': {m: 0.0 for m in self.meses_lista},
                        'orden': ESTADO_ORDEN.index('paid')
                    }
                
                cuenta['etiquetas'][pagadas_label]['monto'] += monto_pagado_parcial
                if mes_str in self.meses_lista:
                    cuenta['etiquetas'][pagadas_label]['montos_por_mes'][mes_str] += monto_pagado_parcial
                
                # También guardar en facturas_por_estado para trazabilidad
                if 'paid' not in cuenta['facturas_por_estado']:
                    cuenta['facturas_por_estado']['paid'] = {}
                
                if partner_name not in cuenta['facturas_por_estado']['paid']:
                    cuenta['facturas_por_estado']['paid'][partner_name] = {
                        'nombre': partner_name,
                        'move_id': move_id,
                        'monto_total': 0.0,
                        'montos_por_mes': {m: 0.0 for m in self.meses_lista},
                        'fecha': fecha,
                        'payment_state': 'paid',
                        'categoria': partner_categoria,
                        'facturas': []
                    }
                
                cuenta['facturas_por_estado']['paid'][partner_name]['facturas'].append({
                    'nombre': f"{move_name} (cobrado de parcial)",
                    'move_id': move_id,
                    'monto': monto_pagado_parcial,
                    'fecha': fecha
                })
                
                cuenta['facturas_por_estado']['paid'][partner_name]['monto_total'] += monto_pagado_parcial
                if mes_str in self.meses_lista:
                    cuenta['facturas_por_estado']['paid'][partner_name]['montos_por_mes'][mes_str] += monto_pagado_parcial

    def procesar_presupuestos_ventas(self, presupuestos: List[Dict], 
                                    clasificar_fn,
                                    currency_converter,
                                    agrupacion: str = 'mensual') -> None:
        """
        Procesa presupuestos de venta (sale.order con state = draft/sent) para proyección CxC.
        
        Crea un nuevo estado "Facturas Proyectadas" (estado_projected) DENTRO de la cuenta CxC existente.
        
        Args:
            presupuestos: Lista de sale.order con state in ['draft', 'sent']
            clasificar_fn: Función de clasificación
            currency_converter: Función para convertir USD a CLP
            agrupacion: 'mensual' o 'semanal'
        """
        print(f"[Agregador] procesar_presupuestos_ventas: {len(presupuestos)} presupuestos")
        
        ESTADO_LABEL = '🔮 Facturas Proyectadas (Modulo de ventas)'
        ESTADO_CODE = 'estado_projected'
        ORDEN_ESTADO = 3.5  # Debajo de No Pagadas (3) y antes de Revertidas (4)

        # Precargar categoría de contacto por partner para agrupar nivel adicional
        partner_ids = []
        for presu in presupuestos:
            partner_data = presu.get('partner_id', [])
            partner_id = partner_data[0] if isinstance(partner_data, (list, tuple)) and len(partner_data) > 0 else None
            if partner_id:
                partner_ids.append(partner_id)

        categoria_por_partner = {}
        if partner_ids:
            try:
                partners_data = self.odoo.search_read(
                    'res.partner',
                    [['id', 'in', list(set(partner_ids))]],
                    ['id', 'x_studio_categora_de_contacto'],
                    limit=10000
                )
                for partner in partners_data:
                    categoria = partner.get('x_studio_categora_de_contacto', False)
                    if categoria and isinstance(categoria, (list, tuple)):
                        categoria = categoria[1]
                    elif not categoria or categoria == 'False':
                        categoria = 'Sin Categoría'
                    categoria_por_partner[partner['id']] = categoria
            except Exception:
                categoria_por_partner = {}
        
        # Buscar cuentas CxC existentes en el concepto 1.1.1
        concepto_id = '1.1.1'
        
        print(f"[Agregador] Buscando cuentas CxC en concepto {concepto_id}")
        
        if concepto_id not in self.cuentas_por_concepto:
            print(f"[Agregador] ERROR: Concepto {concepto_id} no existe todavía")
            return
        
        # Buscar cuenta CxC existente (priorizar 11030101)
        cuenta_cxc = None
        codigo_cxc = None

        cuentas_concepto = self.cuentas_por_concepto.get(concepto_id, {})

        # 1) Prioridad: cuenta principal deudores por ventas
        if '11030101' in cuentas_concepto:
            cuenta_cxc = cuentas_concepto['11030101']
            codigo_cxc = '11030101'
            print(f"[Agregador] Encontrada cuenta CxC principal: {codigo_cxc}")

        # 2) Fallback: cualquier cuenta 1103 existente
        if not cuenta_cxc:
            for codigo, cuenta in cuentas_concepto.items():
                if str(codigo).startswith('1103'):
                    cuenta_cxc = cuenta
                    codigo_cxc = codigo
                    print(f"[Agregador] Encontrada cuenta CxC fallback: {codigo}")
                    break
        
        if not cuenta_cxc:
            print(f"[Agregador] ERROR: No se encontró cuenta CxC en {concepto_id}")
            # Fallback extremo: crear cuenta base CxC estándar
            print(f"[Agregador] Creando cuenta base 11030101")
            self.cuentas_por_concepto[concepto_id]['11030101'] = {
                'codigo': '11030101',
                'nombre': 'DEUDORES POR VENTAS',
                'monto': 0.0,
                'cantidad': 0,
                'montos_por_mes': {m: 0.0 for m in self.meses_lista},
                'account_id': 999999,
                'etiquetas': {},
                'facturas_por_estado': {},
                'es_cuenta_cxc': True
            }
            cuenta_cxc = self.cuentas_por_concepto[concepto_id]['11030101']
            codigo_cxc = '11030101'
        
        # Inicializar estructuras si no existen
        if 'etiquetas' not in cuenta_cxc:
            cuenta_cxc['etiquetas'] = {}
        if 'facturas_por_estado' not in cuenta_cxc:
            cuenta_cxc['facturas_por_estado'] = {}
        
        # Marcar como cuenta CxC
        cuenta_cxc['es_cuenta_cxc'] = True
        
        # Crear estructura de estado proyectado
        if ESTADO_LABEL not in cuenta_cxc['etiquetas']:
            print(f"[Agregador] Creando etiqueta {ESTADO_LABEL} en cuenta {codigo_cxc}")
            cuenta_cxc['etiquetas'][ESTADO_LABEL] = {
                'monto': 0.0,
                'montos_por_mes': {m: 0.0 for m in self.meses_lista},
                'orden': ORDEN_ESTADO
            }
        
        if ESTADO_CODE not in cuenta_cxc['facturas_por_estado']:
            cuenta_cxc['facturas_por_estado'][ESTADO_CODE] = {}
        
        # Procesar cada presupuesto
        presupuestos_procesados = 0
        monto_total_procesado = 0
        
        for presu in presupuestos:
            # Fecha de clasificación: tentativa de pago (fallback date_order)
            fecha = presu.get('x_studio_fecha_tentativa_de_pago') or presu.get('date_order', '')
            if not fecha:
                continue
            
            # Determinar período
            try:
                # commitment_date suele venir como 'YYYY-MM-DD HH:MM:SS'
                fecha_base = str(fecha)[:10]
                if agrupacion == 'semanal':
                    fecha_dt = datetime.strptime(fecha_base, '%Y-%m-%d')
                    y, w, d = fecha_dt.isocalendar()
                    mes_str = f"{y}-W{w:02d}"
                else:
                    mes_str = fecha_base[:7]
            except:
                continue
            
            if mes_str not in self.meses_lista:
                continue
            
            # Obtener monto y moneda
            amount_total = presu.get('amount_total', 0)
            currency_data = presu.get('currency_id', [])
            currency_name = currency_data[1] if isinstance(currency_data, (list, tuple)) and len(currency_data) > 1 else 'CLP'
            
            # Convertir USD a CLP si es necesario
            if 'USD' in currency_name.upper():
                monto_clp = currency_converter(amount_total)
            else:
                monto_clp = amount_total
            
            # Obtener cliente
            partner_data = presu.get('partner_id', [])
            partner_id = partner_data[0] if isinstance(partner_data, (list, tuple)) and len(partner_data) > 0 else None
            cliente_nombre = partner_data[1] if isinstance(partner_data, (list, tuple)) and len(partner_data) > 1 else 'Cliente Desconocido'
            categoria_contacto = categoria_por_partner.get(partner_id, 'Sin Categoría')
            
            # Nombre del presupuesto
            presu_name = presu.get('name', 'SO-???')
            
            # Acumular en concepto y mes
            if concepto_id not in self.montos_por_concepto_mes:
                self.montos_por_concepto_mes[concepto_id] = {m: 0.0 for m in self.meses_lista}
            
            self.montos_por_concepto_mes[concepto_id][mes_str] += monto_clp
            
            # Acumular en cuenta CxC
            cuenta_cxc['monto'] += monto_clp
            cuenta_cxc['montos_por_mes'][mes_str] += monto_clp
            
            # Acumular en estado proyectado
            cuenta_cxc['etiquetas'][ESTADO_LABEL]['monto'] += monto_clp
            cuenta_cxc['etiquetas'][ESTADO_LABEL]['montos_por_mes'][mes_str] += monto_clp
            
            # Guardar detalle del presupuesto para modal
            # Agrupar por categoría de contacto (nivel 3) y luego cliente (nivel 4)
            if categoria_contacto not in cuenta_cxc['facturas_por_estado'][ESTADO_CODE]:
                cuenta_cxc['facturas_por_estado'][ESTADO_CODE][categoria_contacto] = {
                    'nombre': categoria_contacto,
                    'monto_total': 0.0,
                    'montos_por_mes': {m: 0.0 for m in self.meses_lista},
                    'clientes': {}
                }

            categoria_entry = cuenta_cxc['facturas_por_estado'][ESTADO_CODE][categoria_contacto]

            if cliente_nombre not in categoria_entry['clientes']:
                categoria_entry['clientes'][cliente_nombre] = {
                    'nombre': cliente_nombre,
                    'move_id': None,  # No es una factura, es un presupuesto
                    'monto_total': 0.0,
                    'montos_por_mes': {m: 0.0 for m in self.meses_lista},
                    'fecha': fecha,
                    'payment_state': ESTADO_CODE,
                    'presupuestos': []  # Lista de presupuestos de este cliente
                }

            # Agregar presupuesto en categoría y cliente
            categoria_entry['monto_total'] += monto_clp
            categoria_entry['montos_por_mes'][mes_str] += monto_clp

            categoria_entry['clientes'][cliente_nombre]['monto_total'] += monto_clp
            categoria_entry['clientes'][cliente_nombre]['montos_por_mes'][mes_str] += monto_clp
            categoria_entry['clientes'][cliente_nombre]['presupuestos'].append({
                'nombre': presu_name,
                'monto': round(monto_clp, 0),
                'fecha': fecha,
                'moneda_original': currency_name,
                'monto_original': amount_total
            })
            
            presupuestos_procesados += 1
            monto_total_procesado += monto_clp
        
        print(f"[Agregador] Procesados {presupuestos_procesados}/{len(presupuestos)} presupuestos")
        print(f"[Agregador] Monto total: ${monto_total_procesado:,.0f} CLP")
        print(f"[Agregador] Cuenta {codigo_cxc} monto final: ${cuenta_cxc.get('monto', 0):,.0f}")

    def procesar_facturas_draft(self, facturas: List[Dict], lineas: Dict[int, List[Dict]],
                               clasificar_fn, cuentas_info: Dict,
                               agrupacion: str = 'mensual') -> None:
        """
        Procesa facturas para proyección.
        
        - Facturas cliente (out_invoice): Usa amount_residual directo -> 1.1.1
        - Facturas proveedor (in_invoice): Procesa por línea y cuenta
        """
        from .constants import CATEGORIA_NEUTRAL
        
        for factura in facturas:
            move_id = factura['id']
            move_type = factura.get('move_type', '')
            fecha_proy = factura.get('invoice_date_due') or factura.get('invoice_date') or factura.get('date')
            
            if not fecha_proy:
                continue
            
            try:
                fecha_dt = datetime.strptime(str(fecha_proy), '%Y-%m-%d')
                if agrupacion == 'semanal':
                    y, w, d = fecha_dt.isocalendar()
                    mes_proy = f"{y}-W{w:02d}"
                else:
                    mes_proy = fecha_dt.strftime('%Y-%m')
            except:
                continue
            
            if mes_proy not in self.meses_lista:
                continue
            
            # FACTURAS DE CLIENTE -> Usar amount_residual (monto pendiente)
            if move_type in ['out_invoice', 'out_refund']:
                # Usar amount_residual para posted, amount_total para draft
                if factura.get('state') == 'posted':
                    monto = factura.get('amount_residual', 0)
                else:
                    monto = factura.get('amount_total', 0)
                
                if monto == 0:
                    continue
                
                # Para out_refund (notas de crÃ©dito), invertir signo
                if move_type == 'out_refund':
                    monto = -monto
                
                concepto_id = "1.1.1"
                
                # Acumular
                if concepto_id not in self.montos_por_concepto_mes:
                    self.montos_por_concepto_mes[concepto_id] = {m: 0.0 for m in self.meses_lista}
                
                self.montos_por_concepto_mes[concepto_id][mes_proy] += monto
                
                # Trackear como "Facturas por cobrar"
                codigo_cuenta = "CXC"
                acc_display = "CXC Cuentas por Cobrar Proyectadas"
                self._agregar_cuenta(concepto_id, codigo_cuenta, acc_display, monto, mes_proy, 0)
                
                continue  # No procesar lÃ­neas para facturas cliente
            
            # FACTURAS DE PROVEEDOR -> Procesar por lÃ­nea y cuenta
            for linea in lineas.get(move_id, []):
                acc_data = linea.get('account_id')
                if not acc_data:
                    continue
                
                acc_id = acc_data[0] if isinstance(acc_data, (list, tuple)) else acc_data
                cuenta = cuentas_info.get(acc_id, {})
                codigo_cuenta = cuenta.get('code', '')
                
                # Excluir cuentas de efectivo
                if codigo_cuenta.startswith('110') or codigo_cuenta.startswith('111'):
                    continue
                
                # Clasificar por cuenta
                concepto_id, _ = clasificar_fn(codigo_cuenta)
                if concepto_id is None or concepto_id == CATEGORIA_NEUTRAL:
                    continue
                
                # Calcular monto de efectivo
                balance = linea.get('balance', 0)
                monto_efectivo = balance
                
                # Acumular
                if concepto_id not in self.montos_por_concepto_mes:
                    self.montos_por_concepto_mes[concepto_id] = {m: 0.0 for m in self.meses_lista}
                
                self.montos_por_concepto_mes[concepto_id][mes_proy] += monto_efectivo
                
                # Trackear
                acc_display = f"{codigo_cuenta} {cuenta.get('name', '')}"
                self._agregar_cuenta(concepto_id, codigo_cuenta, acc_display, monto_efectivo, mes_proy, acc_id)
    
    def obtener_resultados(self) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict]]:
        """
        Retorna los resultados de la agregaciÃ³n.
        
        Returns:
            Tuple (montos_por_concepto_mes, cuentas_por_concepto)
        """
        return self.montos_por_concepto_mes, self.cuentas_por_concepto
    
    def construir_conceptos_por_actividad(self) -> Tuple[Dict[str, List], Dict[str, Dict]]:
        """
        Construye estructura de conceptos por actividad para resultado final.
        
        Returns:
            Tuple (conceptos_por_actividad, subtotales_por_actividad)
        """
        conceptos_por_actividad = {"OPERACION": [], "INVERSION": [], "FINANCIAMIENTO": []}
        subtotales_por_actividad = {
            "OPERACION": {m: 0.0 for m in self.meses_lista},
            "INVERSION": {m: 0.0 for m in self.meses_lista},
            "FINANCIAMIENTO": {m: 0.0 for m in self.meses_lista}
        }
        
        for concepto in self.catalogo.get("conceptos", []):
            c_id = concepto.get("id")
            c_tipo = concepto.get("tipo")
            c_actividad = concepto.get("actividad")
            
            if c_tipo != "LINEA" or c_actividad not in conceptos_por_actividad:
                continue
            
            montos_mes = self.montos_por_concepto_mes.get(c_id, {m: 0.0 for m in self.meses_lista})
            total_concepto = sum(montos_mes.values())
            
            # Obtener cuentas para drill-down
            cuentas_concepto = self._formatear_cuentas_concepto(c_id)
            
            concepto_resultado = {
                "id": c_id,
                "nombre": concepto.get("nombre"),
                "tipo": c_tipo,
                "nivel": concepto.get("nivel", 3),
                "montos_por_mes": {m: round(montos_mes.get(m, 0), 0) for m in self.meses_lista},
                "total": round(total_concepto, 0),
                "cuentas": cuentas_concepto
            }
            
            conceptos_por_actividad[c_actividad].append(concepto_resultado)
            
            # Sumar a subtotales
            for mes in self.meses_lista:
                subtotales_por_actividad[c_actividad][mes] += montos_mes.get(mes, 0)
        
        return conceptos_por_actividad, subtotales_por_actividad
    
    def _formatear_cuentas_concepto(self, concepto_id: str) -> List[Dict]:
        """Formatea cuentas de un concepto para resultado.
        
        Para cuentas CxC (monitoreadas), incluye estructura especial con:
        - Estados de pago como etiquetas (Pagadas, Parcialmente Pagadas, etc.)
        - Facturas detalladas por estado para modal drill-down
        """
        if concepto_id not in self.cuentas_por_concepto:
            return []

        # Caso especial CxC 1.1.1: exponer estados como NIVEL 2 y partners como NIVEL 3
        # (sin mostrar cuenta intermedia "DEUDORES POR VENTAS")
        if concepto_id == '1.1.1':
            cuentas_cxc = self.cuentas_por_concepto.get(concepto_id, {})
            cuenta_base = None
            for codigo, cuenta in cuentas_cxc.items():
                if cuenta.get('facturas_por_estado'):
                    cuenta_base = cuenta
                    break

            if cuenta_base:
                etiquetas_dict = cuenta_base.get('etiquetas', {})
                facturas_por_estado = cuenta_base.get('facturas_por_estado', {})

                estado_def = [
                    ('paid', '✅ Facturas Pagadas', 'Facturas Pagadas', 1),
                    ('partial', '⏳ Facturas Parcialmente Pagadas', 'Facturas Parcialmente Pagadas', 2),
                    ('in_payment', '🔄 En Proceso de Pago', 'En Proceso de Pago', 3),
                    ('not_paid', '❌ Facturas No Pagadas', 'Facturas No Pagadas', 4),
                    ('estado_projected', '🔮 Facturas Proyectadas (Modulo de ventas)', '🔮 Facturas Proyectadas (Modulo de ventas)', 4.5),
                    # 'reversed' se excluye completamente
                ]

                resultado_estados = []
                for estado_codigo, estado_nombre, estado_label, estado_orden in estado_def:
                    etiqueta_estado = etiquetas_dict.get(estado_label, {})
                    facturas_estado = facturas_por_estado.get(estado_codigo, {})

                    if not etiqueta_estado and not facturas_estado:
                        continue

                    montos_por_mes_estado = etiqueta_estado.get('montos_por_mes', {}) if isinstance(etiqueta_estado, dict) else {}
                    monto_estado = etiqueta_estado.get('monto', 0) if isinstance(etiqueta_estado, dict) else 0

                    etiquetas_partners = []
                    cantidad_estado = len(facturas_estado)

                    if estado_codigo == 'estado_projected':
                        # Facturas proyectadas ventas: nivel adicional por categoría de contacto
                        categorias_formateadas = []

                        for categoria_nombre, categoria_datos in facturas_estado.items():
                            if not isinstance(categoria_datos, dict):
                                continue

                            clientes = categoria_datos.get('clientes', {}) if isinstance(categoria_datos.get('clientes', {}), dict) else {}

                            # Compatibilidad hacia atrás: si no viene estructura por categoría, tratar item como cliente plano
                            if not clientes:
                                categorias_formateadas.append({
                                    'nombre': str(categoria_nombre),
                                    'monto': round(categoria_datos.get('monto_total', 0), 0),
                                    'montos_por_mes': {
                                        m: round(categoria_datos.get('montos_por_mes', {}).get(m, 0), 0)
                                        for m in self.meses_lista
                                    }
                                })
                                continue

                            sub_etiquetas = []
                            for partner_nombre, partner_datos in sorted(
                                clientes.items(),
                                key=lambda x: _texto_orden_alfabetico(x[0])
                            ):
                                sub_etiquetas.append({
                                    'nombre': str(partner_nombre),
                                    'monto': round(partner_datos.get('monto_total', 0), 0),
                                    'montos_por_mes': {
                                        m: round(partner_datos.get('montos_por_mes', {}).get(m, 0), 0)
                                        for m in self.meses_lista
                                    },
                                    'tipo': 'cliente',
                                    'nivel': 4,
                                    'activo': True
                                })

                            categorias_formateadas.append({
                                'nombre': f"📁 {str(categoria_nombre)}",
                                'monto': round(categoria_datos.get('monto_total', 0), 0),
                                'montos_por_mes': {
                                    m: round(categoria_datos.get('montos_por_mes', {}).get(m, 0), 0)
                                    for m in self.meses_lista
                                },
                                'tipo': 'categoria',
                                'nivel': 3,
                                'activo': True,
                                'sub_etiquetas': sub_etiquetas
                            })

                        categorias_formateadas.sort(key=lambda x: _texto_orden_alfabetico(x.get('nombre', '')))
                        etiquetas_partners = categorias_formateadas
                        cantidad_estado = sum(
                            len(v.get('clientes', {})) if isinstance(v, dict) and isinstance(v.get('clientes', {}), dict) and v.get('clientes') else 1
                            for v in facturas_estado.values()
                        )
                    else:
                        for partner_nombre, partner_datos in facturas_estado.items():
                            etiquetas_partners.append({
                                'nombre': str(partner_nombre),  # Sin truncamiento para nombres completos
                                'monto': round(partner_datos.get('monto_total', 0), 0),
                                'montos_por_mes': {
                                    m: round(partner_datos.get('montos_por_mes', {}).get(m, 0), 0)
                                    for m in self.meses_lista
                                },
                                'categoria': partner_datos.get('categoria', 'Sin Categoría')
                            })

                        etiquetas_partners.sort(key=lambda x: _texto_orden_alfabetico(x.get('nombre', '')))

                    resultado_estados.append({
                        'codigo': f'estado_{estado_codigo}' if not str(estado_codigo).startswith('estado_') else estado_codigo,
                        'nombre': estado_nombre,
                        'monto': round(monto_estado, 0),
                        'cantidad': cantidad_estado,
                        'montos_por_mes': {m: round(montos_por_mes_estado.get(m, 0), 0) for m in self.meses_lista},
                        'etiquetas': etiquetas_partners,
                        'es_cuenta_cxc': True,
                        '_orden_estado': estado_orden
                    })

                resultado_estados.sort(key=lambda x: x.get('_orden_estado', 99))
                for item in resultado_estados:
                    item.pop('_orden_estado', None)

                return resultado_estados
        
        # Ordenar por monto absoluto
        sorted_cuentas = sorted(
            self.cuentas_por_concepto[concepto_id].items(),
            key=lambda x: abs(x[1].get('monto', 0)),
            reverse=True
        )[:15]  # Top 15
        
        resultado = []
        for k, v in sorted_cuentas:
            # Formatear etiquetas - SOLO las que tienen monto en el perÃ­odo consultado
            etiquetas_dict = v.get("etiquetas", {})
            facturas_por_estado = v.get("facturas_por_estado", {})
            
            # Filtrar etiquetas que tienen al menos un monto != 0 en algÃºn mes del rango
            etiquetas_filtradas = []
            for nombre, datos in etiquetas_dict.items():
                if isinstance(datos, dict):
                    montos_mes = datos.get("montos_por_mes", {})
                    # Solo incluir si tiene algÃºn valor en los meses del rango
                    tiene_valor = any(montos_mes.get(m, 0) != 0 for m in self.meses_lista)
                    if tiene_valor:
                        etiquetas_filtradas.append((nombre, datos))
                elif datos != 0:  # Si es solo un nÃºmero
                    etiquetas_filtradas.append((nombre, datos))
            
            # Verificar si es cuenta CxC (tiene estados de pago)
            es_cuenta_cxc = bool(facturas_por_estado)
            
            if es_cuenta_cxc:
                # Ordenar por prioridad de estado (orden predefinido)
                def orden_estado(item):
                    nombre, datos = item
                    if isinstance(datos, dict):
                        return datos.get('orden', 99)
                    return 99
                
                etiquetas_ordenadas = sorted(etiquetas_filtradas, key=orden_estado)
            else:
                # Ordenar alfabéticamente por nombre de etiqueta
                etiquetas_ordenadas = sorted(
                    etiquetas_filtradas,
                    key=lambda item: _texto_orden_alfabetico(item[0])
                )[:200]
            
            # Mapeo de etiqueta a payment_state para enlazar facturas
            LABEL_TO_STATE = {
                'Facturas Pagadas': 'paid',
                'Facturas Parcialmente Pagadas': 'partial',
                'En Proceso de Pago': 'in_payment',
                'Facturas No Pagadas': 'not_paid',
                '🔮 Facturas Proyectadas (Modulo de ventas)': 'estado_projected'
                # 'Facturas Revertidas' se excluye completamente
            }
            
            etiquetas_lista = []
            for nombre, datos in etiquetas_ordenadas:
                if isinstance(datos, dict):
                    etiqueta_item = {
                        "nombre": nombre,  # Sin truncamiento para nombres completos
                        "monto": round(datos.get("monto", 0), 0),
                        "montos_por_mes": {m: round(datos.get("montos_por_mes", {}).get(m, 0), 0) for m in self.meses_lista}
                    }
                    
                    # Si es cuenta CxC, agregar facturas detalladas para modal
                    if es_cuenta_cxc and nombre in LABEL_TO_STATE:
                        payment_state = LABEL_TO_STATE[nombre]
                        facturas_estado = facturas_por_estado.get(payment_state, {})
                        
                        # Formatear lista de facturas para modal
                        facturas_lista = []
                        for fact_nombre, fact_datos in facturas_estado.items():
                            facturas_lista.append({
                                "nombre": fact_nombre,
                                "move_id": fact_datos.get("move_id"),  # ID para link a Odoo
                                "monto": round(fact_datos.get("monto_total", 0), 0),
                                "montos_por_mes": {m: round(fact_datos.get("montos_por_mes", {}).get(m, 0), 0) for m in self.meses_lista},
                                "fecha": fact_datos.get("fecha", ""),
                                "payment_state": fact_datos.get("payment_state", "")
                            })
                        
                        # Ordenar facturas alfabéticamente por nombre
                        facturas_lista.sort(key=lambda x: _texto_orden_alfabetico(x.get("nombre", "")))
                        
                        # Incluir solo las primeras 200 para no sobrecargar
                        etiqueta_item["facturas"] = facturas_lista[:200]
                        etiqueta_item["total_facturas"] = len(facturas_estado)
                    
                    etiquetas_lista.append(etiqueta_item)
                else:
                    etiquetas_lista.append({
                        "nombre": nombre,  # Sin truncamiento para nombres completos
                        "monto": round(datos, 0),
                        "montos_por_mes": {m: 0 for m in self.meses_lista}
                    })
            
            resultado.append({
                "codigo": k,
                "nombre": v.get("nombre"),
                "monto": round(v.get("monto", 0), 0),
                "cantidad": v.get("cantidad"),
                "montos_por_mes": {m: round(v.get("montos_por_mes", {}).get(m, 0), 0) for m in self.meses_lista},
                "etiquetas": etiquetas_lista,
                "es_cuenta_cxc": es_cuenta_cxc  # Flag para frontend
            })
        
        return resultado
