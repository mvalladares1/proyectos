"""
Módulo de cálculo de REAL/PROYECTADO/PPTO para Flujo de Caja.

Calcula los valores para las columnas especiales:
- REAL: Valores efectivamente realizados (pagados/cobrados)
- PROYECTADO: Valores pendientes (adeudado)
- PPTO: Presupuesto (vacío por ahora, se alimentará después)

Conceptos soportados:
- 1.2.1: Pagos a proveedores (diario Facturas de Proveedores)
- 1.2.6: IVA Exportador (cuenta 11060108 con partner Tesorería)

ESTRUCTURA JERÁRQUICA (igual que 1.1.1):
- Nivel 1: Concepto (ej: 1.2.1 - Pagos a proveedores)
- Nivel 2: Cuenta/Estado de pago (Facturas Pagadas, Parcialmente Pagadas, etc.)
- Nivel 3: Etiquetas/Proveedores individuales
"""
from typing import Dict, List, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
from backend.services.currency_service import CurrencyService


class RealProyectadoCalculator:
    """Calculadora de valores REAL/PROYECTADO/PPTO."""
    
    # IDs conocidos de Odoo
    CUENTA_IVA_EXPORTADOR_CODE = '11060108'
    PARTNER_TESORERIA_ID = 10
    
    # Mapeo de payment_state a etiqueta amigable
    ESTADO_LABELS = {
        'paid': 'Facturas Pagadas',
        'partial': 'Facturas Parcialmente Pagadas',
        'in_payment': 'En Proceso de Pago',
        'not_paid': 'Facturas No Pagadas',
        'reversed': 'Facturas Revertidas'
    }
    
    # Iconos por estado
    ESTADO_ICONS = {
        'paid': '✅',
        'partial': '⏳',
        'in_payment': '🔄',
        'not_paid': '❌',
        'reversed': '↩️'
    }
    
    def __init__(self, odoo_client):
        """
        Args:
            odoo_client: Instancia de OdooClient
        """
        self.odoo = odoo_client
        self._cuenta_iva_id = None
    
    def _fecha_a_periodo(self, fecha: str, periodos_lista: List[str] = None) -> str:
        """
        Convierte una fecha a período (mes o semana) según el formato de periodos_lista.
        
        Args:
            fecha: Fecha en formato YYYY-MM-DD
            periodos_lista: Lista de períodos (ej: ['2026-01', ...] o ['2026-W01', ...])
        
        Returns:
            Período en formato YYYY-MM o YYYY-Www
        """
        if not fecha:
            return ''
        
        # Por defecto, retornar mes
        if not periodos_lista or len(periodos_lista) == 0:
            return fecha[:7]  # YYYY-MM
        
        # Detectar si es vista semanal
        primer_periodo = str(periodos_lista[0])
        es_semanal = 'W' in primer_periodo or '-W' in primer_periodo
        
        if es_semanal:
            # Convertir fecha a semana ISO
            try:
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
                isocalendar = fecha_dt.isocalendar()
                year = isocalendar[0]
                week = isocalendar[1]
                return f"{year}-W{week:02d}"
            except Exception as e:
                print(f"[RealProyectado] Error convirtiendo fecha a semana: {e}")
                return fecha[:7]  # Fallback a mes
        else:
            return fecha[:7]  # YYYY-MM
    
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
    
    def calcular_pagos_proveedores(self, fecha_inicio: str, fecha_fin: str, meses_lista: List[str] = None) -> Dict:
        """
        Calcula REAL y PROYECTADO para 1.2.1 - Pagos a proveedores.
        
        NUEVA LÓGICA BASADA EN MATCHING_NUMBER:
        - PAGADAS (AXXXXX): Buscar fecha de pago real
        - PARCIALES (P): Monto pagado y pendiente
        - NO PAGADAS (blank): Todo va a proyectado con fecha +30
        
        ESTRUCTURA JERÁRQUICA:
        - Nivel 2: Por estado (Pagadas, Parciales, No Pagadas)
        - Nivel 3: Por proveedor
        """
        try:
            # PASO 1: Buscar facturas de proveedor desde diario específico
            facturas = self.odoo.search_read(
                'account.move',
                [
                    ['move_type', 'in', ['in_invoice', 'in_refund']],
                    ['journal_id', '=', 2],  # Facturas de Proveedores
                    ['date', '>=', fecha_inicio],
                    ['date', '<=', fecha_fin],
                    ['state', '=', 'posted']
                ],
                ['id', 'name', 'move_type', 'date', 'invoice_date', 'invoice_date_due',
                 'amount_total', 'amount_residual', 'payment_state', 'partner_id', 'x_studio_fecha_estimada_de_pago'],
                limit=5000
            )
            
            real_total = 0.0
            proyectado_total = 0.0
            real_por_periodo = defaultdict(float)
            proyectado_por_periodo = defaultdict(float)
            
            # PASO 1.5: Obtener información de partners con categoría de contacto
            partner_ids = list(set([f.get('partner_id')[0] if isinstance(f.get('partner_id'), (list, tuple)) else f.get('partner_id') 
                                   for f in facturas if f.get('partner_id')]))
            
            partners_info = {}
            if partner_ids:
                partners_data = self.odoo.search_read(
                    'res.partner',
                    [['id', 'in', partner_ids]],
                    ['id', 'name', 'x_studio_categora_de_contacto'],
                    limit=10000
                )
                for p in partners_data:
                    categoria = p.get('x_studio_categora_de_contacto', False)
                    if categoria and isinstance(categoria, (list, tuple)):
                        categoria = categoria[1]  # Obtener el nombre si es selection
                    elif not categoria or categoria == 'False':
                        categoria = 'Sin Categoría'
                    
                    partners_info[p['id']] = {
                        'name': p.get('name', 'Sin nombre'),
                        'categoria': categoria
                    }
            
            # Estructura jerárquica: {estado: {categoria: {proveedor: {datos}}}}
            # Las N/C se integran en las mismas categorías con signo invertido
            estados = {
                'PAGADAS': {
                    'codigo': 'pagadas',
                    'nombre': '✅ Facturas Pagadas',
                    'monto': 0.0,
                    'montos_por_mes': defaultdict(float),
                    'categorias': {},  # Nivel 3: Categorías de contacto
                    'es_cuenta_cxp': True,
                    'orden': 1
                },
                'PARCIALES': {
                    'codigo': 'parciales',
                    'nombre': '⏳ Facturas Parcialmente Pagadas',
                    'monto': 0.0,
                    'montos_por_mes': defaultdict(float),
                    'monto_real': 0.0,
                    'montos_real_por_mes': defaultdict(float),
                    'categorias': {},  # Nivel 3: Categorías de contacto
                    'es_cuenta_cxp': True,
                    'orden': 2
                },
                'NO_PAGADAS': {
                    'codigo': 'no_pagadas',
                    'nombre': '❌ Facturas No Pagadas',
                    'monto': 0.0,
                    'montos_por_mes': defaultdict(float),
                    'categorias': {},  # Nivel 3: Categorías de contacto
                    'es_cuenta_cxp': True,
                    'orden': 3
                },
                'PROYECTADAS_COMPRAS': {
                    'codigo': 'proyectadas_compras',
                    'nombre': '📦 Facturas Proyectadas (Modulo Compras)',
                    'monto': 0.0,
                    'montos_por_mes': defaultdict(float),
                    'categorias': {},
                    'es_cuenta_cxp': True,
                    'orden': 4
                }
            }
            
            # PASO 2: Buscar TODAS las líneas de las facturas de una sola vez
            factura_ids = [f['id'] for f in facturas]
            todas_lineas = self.odoo.search_read(
                'account.move.line',
                [['move_id', 'in', factura_ids]],
                ['id', 'move_id', 'matching_number', 'date', 'debit', 'credit'],
                limit=50000
            )
            
            # Agrupar líneas por factura
            lineas_por_factura = defaultdict(list)
            for linea in todas_lineas:
                move_id = linea.get('move_id')
                if isinstance(move_id, (list, tuple)):
                    move_id = move_id[0]
                lineas_por_factura[move_id].append(linea)
            
            # PASO 3: Clasificar cada factura por matching_number
            for f in facturas:
                # Obtener líneas de esta factura
                lineas = lineas_por_factura.get(f['id'], [])

                
                # Detectar matching_number
                matching_number = None
                for linea in lineas:
                    match = linea.get('matching_number')
                    if match and match not in ['False', False, '', None]:
                        matching_number = match
                        break
                
                # Datos básicos de la factura
                amount_total = f.get('amount_total', 0) or 0
                amount_residual = f.get('amount_residual', 0) or 0
                move_type = f.get('move_type', '')
                partner_data = f.get('partner_id', [0, 'Sin proveedor'])
                partner_name = partner_data[1] if isinstance(partner_data, (list, tuple)) and len(partner_data) > 1 else 'Sin proveedor'
                
                # Signo: N/C invierten el signo (devuelven dinero)
                signo = -1 if move_type == 'in_refund' else 1
                es_nc = (move_type == 'in_refund')
                
                # CLASIFICACIÓN POR MATCHING_NUMBER
                # Las N/C se clasifican en las mismas categorías que facturas, pero con signo invertido
                if matching_number and str(matching_number).startswith('A'):
                    # ===== CASO 1: PAGADAS CON MATCHING AXXXXX =====
                    estado_key = 'PAGADAS'
                    
                    # Monto REAL = lo ya pagado (negativo = salida para facturas, positivo = ingreso para N/C)
                    monto_real = -(amount_total - amount_residual) * signo
                    monto_proyectado = 0  # Ya está pagado/devuelto
                    
                    # Buscar fecha de pago en las líneas de esta factura
                    fecha_real = f.get('date', '')
                    for linea in lineas:
                        if linea.get('debit', 0) > 0:
                            fecha_real = linea.get('date', fecha_real)
                            break
                    
                    periodo_real = self._fecha_a_periodo(fecha_real, meses_lista)
                    periodo_proyectado = None
                    
                elif matching_number == 'P':
                    # ===== CASO 2: PARCIALES CON MATCHING P =====
                    estado_key = 'PARCIALES'
                    
                    # Monto REAL = lo ya pagado
                    monto_real = -(amount_total - amount_residual) * signo
                    # Monto PROYECTADO = lo que falta
                    monto_proyectado = -amount_residual * signo
                    
                    # Fecha REAL = fecha de la factura
                    fecha_real = f.get('date', '')
                    periodo_real = self._fecha_a_periodo(fecha_real, meses_lista)
                    
                    # Fecha PROYECTADA = x_studio_fecha_estimada_de_pago > invoice_date_due > +30 días
                    fecha_estimada = f.get('x_studio_fecha_estimada_de_pago')
                    invoice_date = f.get('invoice_date', '')
                    invoice_date_due = f.get('invoice_date_due')
                    
                    if fecha_estimada:
                        periodo_proyectado = self._fecha_a_periodo(fecha_estimada, meses_lista)
                    elif invoice_date_due:
                        periodo_proyectado = self._fecha_a_periodo(invoice_date_due, meses_lista)
                    elif invoice_date:
                        from datetime import datetime, timedelta
                        try:
                            fecha_dt = datetime.strptime(invoice_date, '%Y-%m-%d')
                            fecha_proyectada = (fecha_dt + timedelta(days=30)).strftime('%Y-%m-%d')
                            periodo_proyectado = self._fecha_a_periodo(fecha_proyectada, meses_lista)
                        except:
                            periodo_proyectado = self._fecha_a_periodo(invoice_date, meses_lista)
                    else:
                        periodo_proyectado = periodo_real
                    
                else:
                    # ===== CASO 3: NO PAGADAS (sin matching) =====
                    estado_key = 'NO_PAGADAS'
                    
                    # Monto REAL = 0 (no hay pagos/devoluciones)
                    monto_real = 0
                    # Monto PROYECTADO = todo el monto
                    monto_proyectado = -amount_total * signo
                    
                    periodo_real = None
                    
                    # Fecha PROYECTADA = x_studio_fecha_estimada_de_pago > invoice_date_due > +30 días
                    fecha_estimada = f.get('x_studio_fecha_estimada_de_pago')
                    invoice_date = f.get('invoice_date', '')
                    invoice_date_due = f.get('invoice_date_due')
                    
                    if fecha_estimada:
                        periodo_proyectado = self._fecha_a_periodo(fecha_estimada, meses_lista)
                    elif invoice_date_due:
                        periodo_proyectado = self._fecha_a_periodo(invoice_date_due, meses_lista)
                    elif invoice_date:
                        from datetime import datetime, timedelta
                        try:
                            fecha_dt = datetime.strptime(invoice_date, '%Y-%m-%d')
                            fecha_proyectada = (fecha_dt + timedelta(days=30)).strftime('%Y-%m-%d')
                            periodo_proyectado = self._fecha_a_periodo(fecha_proyectada, meses_lista)
                        except:
                            periodo_proyectado = self._fecha_a_periodo(invoice_date, meses_lista)
                    else:
                        periodo_proyectado = self._fecha_a_periodo(f.get('date', ''), meses_lista)
                
                # Acumular totales generales
                real_total += monto_real
                proyectado_total += monto_proyectado
                
                if periodo_real:
                    real_por_periodo[periodo_real] += monto_real
                if periodo_proyectado:
                    proyectado_por_periodo[periodo_proyectado] += monto_proyectado
                
                # Acumular por estado (Nivel 2)
                estado = estados[estado_key]
                estado['monto'] += monto_real + monto_proyectado
                
                if periodo_real:
                    estado['montos_por_mes'][periodo_real] += monto_real
                if periodo_proyectado:
                    estado['montos_por_mes'][periodo_proyectado] += monto_proyectado
                
                # Para PARCIALES: guardar montos reales por separado
                if estado_key == 'PARCIALES':
                    estado['monto_real'] += monto_real
                    if periodo_real:
                        estado['montos_real_por_mes'][periodo_real] += monto_real
                
                # Obtener información del partner
                partner_id = partner_data[0] if isinstance(partner_data, (list, tuple)) and len(partner_data) > 0 else 0
                partner_info = partners_info.get(partner_id, {'name': partner_name, 'categoria': 'Sin Categoría'})
                categoria_nombre = partner_info['categoria']
                
                # Nivel 3: Agrupar por categoría de contacto
                if categoria_nombre not in estado['categorias']:
                    cat_init = {
                        'nombre': categoria_nombre,
                        'monto': 0.0,
                        'montos_por_mes': defaultdict(float),
                        'proveedores': {}  # Nivel 4: Proveedores individuales
                    }
                    if estado_key == 'PARCIALES':
                        cat_init['monto_real'] = 0.0
                        cat_init['montos_real_por_mes'] = defaultdict(float)
                    estado['categorias'][categoria_nombre] = cat_init
                
                categoria = estado['categorias'][categoria_nombre]
                categoria['monto'] += monto_real + monto_proyectado
                
                if periodo_real:
                    categoria['montos_por_mes'][periodo_real] += monto_real
                if periodo_proyectado:
                    categoria['montos_por_mes'][periodo_proyectado] += monto_proyectado
                
                # Para PARCIALES: guardar montos reales por separado en categoría
                if estado_key == 'PARCIALES':
                    categoria['monto_real'] = categoria.get('monto_real', 0.0) + monto_real
                    if periodo_real:
                        if 'montos_real_por_mes' not in categoria:
                            categoria['montos_real_por_mes'] = defaultdict(float)
                        categoria['montos_real_por_mes'][periodo_real] += monto_real
                
                # Nivel 4: Agrupar por proveedor individual
                if partner_name not in categoria['proveedores']:
                    prov_init = {
                        'nombre': partner_name[:50],
                        'monto': 0.0,
                        'montos_por_mes': defaultdict(float)
                    }
                    if estado_key == 'PARCIALES':
                        prov_init['monto_real'] = 0.0
                        prov_init['montos_real_por_mes'] = defaultdict(float)
                    categoria['proveedores'][partner_name] = prov_init
                
                proveedor = categoria['proveedores'][partner_name]
                proveedor['monto'] += monto_real + monto_proyectado
                
                if periodo_real:
                    proveedor['montos_por_mes'][periodo_real] += monto_real
                if periodo_proyectado:
                    proveedor['montos_por_mes'][periodo_proyectado] += monto_proyectado
                
                # Para PARCIALES: guardar montos reales por separado en proveedor
                if estado_key == 'PARCIALES':
                    proveedor['monto_real'] = proveedor.get('monto_real', 0.0) + monto_real
                    if periodo_real:
                        if 'montos_real_por_mes' not in proveedor:
                            proveedor['montos_real_por_mes'] = defaultdict(float)
                        proveedor['montos_real_por_mes'][periodo_real] += monto_real

            # PASO 4: Agregar proyecciones desde Módulo Compras (purchase.order)
            campos_oc = [
                'id', 'name', 'partner_id', 'amount_total', 'date_order',
                'date_planned', 'date_approve', 'payment_term_id',
                'invoice_ids', 'invoice_status', 'currency_id'
            ]

            ocs_compra = []
            ocs_compra = self.odoo.search_read(
                'purchase.order',
                [['state', '=', 'purchase']],
                campos_oc,
                limit=10000
            )

            # Mapa payment_term_id -> días de plazo (máximo día de las líneas)
            payment_term_ids = []
            for oc in ocs_compra:
                pt_data = oc.get('payment_term_id')
                pt_id = pt_data[0] if isinstance(pt_data, (list, tuple)) and len(pt_data) > 0 else pt_data
                if pt_id:
                    payment_term_ids.append(pt_id)

            payment_term_days = {}
            if payment_term_ids:
                try:
                    lineas_plazo = self.odoo.search_read(
                        'account.payment.term.line',
                        [['payment_id', 'in', list(set(payment_term_ids))]],
                        ['payment_id', 'days'],
                        limit=10000
                    )

                    for linea in lineas_plazo:
                        payment_data = linea.get('payment_id')
                        payment_id = payment_data[0] if isinstance(payment_data, (list, tuple)) and len(payment_data) > 0 else payment_data
                        if not payment_id:
                            continue

                        dias = int(linea.get('days') or 0)
                        actual = payment_term_days.get(payment_id)
                        if actual is None or dias > actual:
                            payment_term_days[payment_id] = dias
                except Exception:
                    payment_term_days = {}

            # Cargar categorías de partners de OCs que no estén en cache
            partner_ids_oc = []
            for oc in ocs_compra:
                partner_data = oc.get('partner_id')
                partner_id = partner_data[0] if isinstance(partner_data, (list, tuple)) and len(partner_data) > 0 else partner_data
                if partner_id and partner_id not in partners_info:
                    partner_ids_oc.append(partner_id)

            if partner_ids_oc:
                partners_data_oc = self.odoo.search_read(
                    'res.partner',
                    [['id', 'in', list(set(partner_ids_oc))]],
                    ['id', 'name', 'x_studio_categora_de_contacto'],
                    limit=10000
                )
                for p in partners_data_oc:
                    categoria = p.get('x_studio_categora_de_contacto', False)
                    if categoria and isinstance(categoria, (list, tuple)):
                        categoria = categoria[1]
                    elif not categoria or categoria == 'False':
                        categoria = 'Sin Categoría'

                    partners_info[p['id']] = {
                        'name': p.get('name', 'Sin nombre'),
                        'categoria': categoria
                    }

            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()

            for oc in ocs_compra:
                invoice_ids = oc.get('invoice_ids') or []
                invoice_status = oc.get('invoice_status') or ''
                if invoice_ids or invoice_status == 'invoiced':
                    continue

                fecha_base = str(oc.get('date_approve') or '')[:10]
                if not fecha_base:
                    continue

                try:
                    fecha_base_dt = datetime.strptime(fecha_base, '%Y-%m-%d').date()
                except Exception:
                    continue

                pt_data = oc.get('payment_term_id')
                pt_id = pt_data[0] if isinstance(pt_data, (list, tuple)) and len(pt_data) > 0 else pt_data
                dias_plazo = payment_term_days.get(pt_id, 0)

                if dias_plazo and dias_plazo > 0:
                    fecha_proyectada_dt = fecha_base_dt + timedelta(days=dias_plazo)
                else:
                    fecha_proyectada_dt = fecha_base_dt

                fecha_proyectada = fecha_proyectada_dt.strftime('%Y-%m-%d')

                if fecha_proyectada_dt < fecha_inicio_dt or fecha_proyectada_dt > fecha_fin_dt:
                    continue

                periodo_proyectado = self._fecha_a_periodo(fecha_proyectada, meses_lista)
                if not periodo_proyectado:
                    continue

                amount_total = float(oc.get('amount_total') or 0.0)
                currency_data = oc.get('currency_id')
                currency_name = currency_data[1] if isinstance(currency_data, (list, tuple)) and len(currency_data) > 1 else ''
                if currency_name and 'USD' in str(currency_name).upper():
                    amount_total = CurrencyService.convert_usd_to_clp(amount_total)

                monto_proyectado = -amount_total
                if monto_proyectado == 0:
                    continue

                partner_data = oc.get('partner_id', [0, 'Sin proveedor'])
                partner_id = partner_data[0] if isinstance(partner_data, (list, tuple)) and len(partner_data) > 0 else 0
                partner_name = partner_data[1] if isinstance(partner_data, (list, tuple)) and len(partner_data) > 1 else 'Sin proveedor'
                partner_info = partners_info.get(partner_id, {'name': partner_name, 'categoria': 'Sin Categoría'})
                categoria_nombre = partner_info['categoria']

                proyectado_total += monto_proyectado
                proyectado_por_periodo[periodo_proyectado] += monto_proyectado

                estado = estados['PROYECTADAS_COMPRAS']
                estado['monto'] += monto_proyectado
                estado['montos_por_mes'][periodo_proyectado] += monto_proyectado

                if categoria_nombre not in estado['categorias']:
                    estado['categorias'][categoria_nombre] = {
                        'nombre': categoria_nombre,
                        'monto': 0.0,
                        'montos_por_mes': defaultdict(float),
                        'proveedores': {}
                    }

                categoria = estado['categorias'][categoria_nombre]
                categoria['monto'] += monto_proyectado
                categoria['montos_por_mes'][periodo_proyectado] += monto_proyectado

                if partner_name not in categoria['proveedores']:
                    categoria['proveedores'][partner_name] = {
                        'nombre': partner_name[:50],
                        'monto': 0.0,
                        'montos_por_mes': defaultdict(float)
                    }

                proveedor = categoria['proveedores'][partner_name]
                proveedor['monto'] += monto_proyectado
                proveedor['montos_por_mes'][periodo_proyectado] += monto_proyectado
            
            # PASO 3: Convertir estructura a 4 NIVELES EXPANDIBLES
            # Nivel 2 (cuentas): ESTADOS (expandible)
            # Nivel 3 (etiquetas): CATEGORÍAS (expandible con sub_etiquetas)
            # Nivel 4 (sub_etiquetas): PROVEEDORES (anidados bajo categoría)
            montos_por_mes_total = defaultdict(float)
            for periodo in set(real_por_periodo.keys()) | set(proyectado_por_periodo.keys()):
                montos_por_mes_total[periodo] = real_por_periodo.get(periodo, 0) + proyectado_por_periodo.get(periodo, 0)
            
            cuentas_resultado = []
            orden_estados = ['PAGADAS', 'PARCIALES', 'NO_PAGADAS', 'PROYECTADAS_COMPRAS']
            
            for estado_key in orden_estados:
                estado = estados[estado_key]
                
                # Nivel 2: ESTADO como cuenta
                etiquetas_list = []
                
                # Ordenar categorías por monto (descendente)
                categorias_ordenadas = sorted(
                    estado['categorias'].items(),
                    key=lambda x: abs(x[1]['monto']),
                    reverse=True
                )
                
                for categoria_nombre, categoria_data in categorias_ordenadas:
                    # Nivel 3: CATEGORÍA como etiqueta EXPANDIBLE con sub_etiquetas
                    # Ordenar proveedores por monto
                    proveedores_ordenados = sorted(
                        categoria_data['proveedores'].items(),
                        key=lambda x: abs(x[1]['monto']),
                        reverse=True
                    )
                    
                    # Nivel 4: PROVEEDORES como sub_etiquetas anidadas
                    sub_etiquetas_proveedores = []
                    top_proveedores = proveedores_ordenados[:30]
                    resto_proveedores = proveedores_ordenados[30:]
                    
                    for prov_nombre, prov_data in top_proveedores:
                        prov_entry = {
                            'nombre': f"↳ {prov_data['nombre']}",
                            'monto': prov_data['monto'],
                            'montos_por_mes': dict(prov_data['montos_por_mes']),
                            'tipo': 'proveedor',
                            'nivel': 4,
                            'activo': True
                        }
                        if estado_key == 'PARCIALES' and 'montos_real_por_mes' in prov_data:
                            prov_entry['monto_real'] = prov_data.get('monto_real', 0.0)
                            prov_entry['montos_real_por_mes'] = dict(prov_data['montos_real_por_mes'])
                        sub_etiquetas_proveedores.append(prov_entry)
                    
                    # Agregar fila "Otros proveedores" con los montos restantes
                    if resto_proveedores:
                        otros_monto = sum(p[1]['monto'] for p in resto_proveedores)
                        otros_montos_por_mes = {}
                        for _, p_data in resto_proveedores:
                            for mes, val in p_data['montos_por_mes'].items():
                                otros_montos_por_mes[mes] = otros_montos_por_mes.get(mes, 0) + val
                        otros_entry = {
                            'nombre': f"↳ Otros proveedores ({len(resto_proveedores)})",
                            'monto': otros_monto,
                            'montos_por_mes': otros_montos_por_mes,
                            'tipo': 'proveedor',
                            'nivel': 4,
                            'activo': True
                        }
                        if estado_key == 'PARCIALES':
                            otros_real = sum(p[1].get('monto_real', 0) for p in resto_proveedores)
                            otros_real_por_mes = {}
                            for _, p_data in resto_proveedores:
                                for mes, val in p_data.get('montos_real_por_mes', {}).items():
                                    otros_real_por_mes[mes] = otros_real_por_mes.get(mes, 0) + val
                            if otros_real != 0 or otros_real_por_mes:
                                otros_entry['monto_real'] = otros_real
                                otros_entry['montos_real_por_mes'] = otros_real_por_mes
                        sub_etiquetas_proveedores.append(otros_entry)
                    
                    cat_entry = {
                        'nombre': f"📁 {categoria_nombre}",
                        'monto': categoria_data['monto'],
                        'montos_por_mes': dict(categoria_data['montos_por_mes']),
                        'tipo': 'categoria',
                        'nivel': 3,
                        'activo': True,
                        'sub_etiquetas': sub_etiquetas_proveedores  # ANIDADOS
                    }
                    if estado_key == 'PARCIALES' and 'montos_real_por_mes' in categoria_data:
                        cat_entry['monto_real'] = categoria_data.get('monto_real', 0.0)
                        cat_entry['montos_real_por_mes'] = dict(categoria_data['montos_real_por_mes'])
                    etiquetas_list.append(cat_entry)
                
                cuenta_entry = {
                    'codigo': estado['codigo'],
                    'nombre': estado['nombre'],
                    'monto': estado['monto'],
                    'montos_por_mes': dict(estado['montos_por_mes']),
                    'etiquetas': etiquetas_list,
                    'es_cuenta_cxp': True,
                    'activo': True
                }
                if estado_key == 'PARCIALES':
                    cuenta_entry['monto_real'] = estado.get('monto_real', 0.0)
                    cuenta_entry['montos_real_por_mes'] = dict(estado.get('montos_real_por_mes', {}))
                cuentas_resultado.append(cuenta_entry)
            
            return {
                'montos_por_mes': dict(montos_por_mes_total),
                'total': real_total + proyectado_total,
                'cuentas': cuentas_resultado,
                'facturas_count': len(facturas)
            }
            
        except Exception as e:
            print(f"[RealProyectado] Error calculando pagos proveedores: {e}")
            import traceback
            traceback.print_exc()
            return {
                'montos_por_mes': {},
                'total': 0.0,
                'cuentas': [],
                'error': str(e)
            }
    
    def calcular_iva_exportador(self, fecha_inicio: str, fecha_fin: str, meses_lista: List[str] = None) -> Dict:
        """
        Calcula REAL y PROYECTADO para 1.2.6 - IVA Exportador.
        
        ESTRUCTURA JERÁRQUICA:
        - Nivel 2: Tipo de movimiento (Devoluciones recibidas por mes)
        - Nivel 3: Por documento/fecha
        
        LÓGICA:
        - REAL = Devoluciones de IVA recibidas (créditos en cuenta 11060108)
        - Solo cuando el partner es "Tesorería General de la República"
        - PROYECTADO = 0 por ahora (podría ser solicitudes pendientes)
        """
        cuenta_iva_id = self._get_cuenta_iva_id()
        
        if not cuenta_iva_id:
            return {
                'real': 0.0,
                'proyectado': 0.0,
                'ppto': 0.0,
                'real_por_mes': {},
                'proyectado_por_mes': {},
                'cuentas': [],
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
                ['id', 'move_id', 'date', 'name', 'credit', 'debit', 'ref'],
                limit=500
            )
            
            real_total = 0.0
            real_por_mes = defaultdict(float)
            
            # Estructura jerárquica para devoluciones
            devoluciones_por_mes = defaultdict(lambda: {
                'monto': 0.0,
                'documentos': []
            })
            
            for m in movimientos:
                fecha = m.get('date', '')
                if not fecha:
                    continue
                    
                periodo = self._fecha_a_periodo(fecha, meses_lista)
                
                # Para IVA Exportador, los CRÉDITOS son devoluciones recibidas
                credit = m.get('credit', 0) or 0
                
                if credit <= 0:
                    continue
                
                real_total += credit
                real_por_mes[periodo] += credit
                
                # Obtener nombre del documento
                move_data = m.get('move_id', [0, ''])
                move_name = move_data[1] if isinstance(move_data, (list, tuple)) and len(move_data) > 1 else m.get('name', 'Sin nombre')
                ref = m.get('ref', '')
                
                devoluciones_por_mes[periodo]['monto'] += credit
                devoluciones_por_mes[periodo]['documentos'].append({
                    'name': move_name,
                    'ref': ref,
                    'credit': credit,
                    'fecha': fecha
                })
            
            # Construir estructura de cuentas (por mes de devolución)
            cuentas_resultado = []
            
            # Acumular montos por período para el concepto principal
            total_por_mes = defaultdict(float)
            
            for periodo, data in sorted(devoluciones_por_mes.items()):
                # Acumular para el total del concepto
                total_por_mes[periodo] += data['monto']
                
                # Formatear nombre del período
                try:
                    if 'W' in periodo:
                        nombre_periodo = f"Semana {periodo}"
                    else:
                        fecha_mes = datetime.strptime(f"{periodo}-01", '%Y-%m-%d')
                        nombre_periodo = fecha_mes.strftime('%B %Y').title()
                except:
                    nombre_periodo = periodo
                
                etiquetas_list = []
                for doc in data['documentos']:
                    etiquetas_list.append({
                        'nombre': f"📄 {doc['name']} ({doc['fecha']})",
                        'monto': doc['credit'],
                        'real': doc['credit'],
                        'proyectado': 0,
                        'montos_por_mes': {periodo: doc['credit']},
                        'ref': doc['ref']
                    })
                
                cuentas_resultado.append({
                    'codigo': f'iva_{periodo}',
                    'nombre': f"💰 Devoluciones {nombre_periodo}",
                    'monto': data['monto'],
                    'real': data['monto'],
                    'proyectado': 0,
                    'montos_por_mes': {periodo: data['monto']},
                    'real_por_mes': {periodo: data['monto']},
                    'proyectado_por_mes': {},
                    'etiquetas': etiquetas_list,
                    'es_cuenta_iva': True
                })
            
            return {
                'real': real_total,  # Positivo porque es entrada
                'proyectado': 0.0,  # Por ahora vacío
                'ppto': 0.0,
                'real_por_mes': dict(real_por_mes),
                'proyectado_por_mes': {},
                'montos_por_mes': dict(total_por_mes),  # Sumatoria para columnas mensuales
                'total': real_total,
                'cuentas': cuentas_resultado,
                'movimientos_count': len(movimientos)
            }
            
        except Exception as e:
            print(f"[RealProyectado] Error calculando IVA exportador: {e}")
            import traceback
            traceback.print_exc()
            return {
                'real': 0.0,
                'proyectado': 0.0,
                'ppto': 0.0,
                'real_por_mes': {},
                'proyectado_por_mes': {},
                'cuentas': [],
                'error': str(e)
            }
    
    def calcular_cobros_clientes(self, fecha_inicio: str, fecha_fin: str, meses_lista: List[str] = None) -> Dict:
        """
        Calcula REAL y PROYECTADO para 1.1.1 - Cobros procedentes de ventas.
        
        ESTRUCTURA JERÁRQUICA (igual que 1.2.1):
        - Nivel 2: Por estado de pago (Pagadas, Parciales, No Pagadas)
        - Nivel 3: Por cliente/deudor
        
        LÓGICA:
        - REAL = Monto cobrado (amount_total - amount_residual)
        - PROYECTADO = Monto pendiente de cobro (amount_residual)
        """
        try:
            # Buscar facturas de cliente en el período
            facturas = self.odoo.search_read(
                'account.move',
                [
                    ['move_type', '=', 'out_invoice'],
                    ['state', '=', 'posted'],
                    ['invoice_date', '>=', fecha_inicio],
                    ['invoice_date', '<=', fecha_fin]
                ],
                ['id', 'name', 'partner_id', 'invoice_date', 'amount_total', 'amount_residual', 'payment_state'],
                limit=5000
            )
            
            real_total = 0.0
            proyectado_total = 0.0
            real_por_mes = defaultdict(float)
            proyectado_por_mes = defaultdict(float)
            
            # Estructura jerárquica: Estados -> Clientes
            estados = {}
            
            for f in facturas:
                # Datos básicos
                partner_data = f.get('partner_id', [0, 'Desconocido'])
                partner_name = partner_data[1] if isinstance(partner_data, (list, tuple)) and len(partner_data) > 1 else 'Desconocido'
                
                fecha = f.get('invoice_date', '')
                if not fecha:
                    continue
                    
                periodo = self._fecha_a_periodo(fecha, meses_lista)
                amount_total = f.get('amount_total', 0) or 0
                amount_residual = f.get('amount_residual', 0) or 0
                payment_state = f.get('payment_state', 'not_paid')
                move_type = f.get('move_type', 'out_invoice')
                
                # Calcular cobrado y pendiente (POSITIVO para ingresos)
                cobrado = amount_total - amount_residual
                pendiente = amount_residual
                
                real_total += cobrado
                proyectado_total += pendiente
                real_por_mes[periodo] += cobrado
                proyectado_por_mes[periodo] += pendiente
                
                # Agrupar por estado de pago (Nivel 2)
                estado_label = self.ESTADO_LABELS.get(payment_state, 'Otros')
                
                if estado_label not in estados:
                    estados[estado_label] = {
                        'codigo': f'estado_{payment_state}',
                        'nombre': estado_label,
                        'icon': self.ESTADO_ICONS.get(payment_state, '📋'),
                        'monto': 0.0,
                        'real': 0.0,
                        'proyectado': 0.0,
                        'montos_por_mes': defaultdict(float),
                        'real_por_mes': defaultdict(float),
                        'proyectado_por_mes': defaultdict(float),
                        'etiquetas': {},  # Clientes
                        'es_cuenta_cxc': True,
                        'orden': list(self.ESTADO_LABELS.keys()).index(payment_state) if payment_state in self.ESTADO_LABELS else 99
                    }
                
                estado = estados[estado_label]
                estado['monto'] += cobrado + pendiente
                estado['real'] += cobrado
                estado['proyectado'] += pendiente
                estado['montos_por_mes'][periodo] += cobrado + pendiente
                estado['real_por_mes'][periodo] += cobrado
                estado['proyectado_por_mes'][periodo] += pendiente
                
                # Agrupar por cliente (Nivel 3)
                if partner_name not in estado['etiquetas']:
                    estado['etiquetas'][partner_name] = {
                        'nombre': partner_name[:50],
                        'monto': 0.0,
                        'real': 0.0,
                        'proyectado': 0.0,
                        'montos_por_mes': defaultdict(float),
                        'real_por_mes': defaultdict(float),
                        'proyectado_por_mes': defaultdict(float),
                        'facturas': []
                    }
                
                cliente = estado['etiquetas'][partner_name]
                cliente['monto'] += cobrado + pendiente
                cliente['real'] += cobrado
                cliente['proyectado'] += pendiente
                cliente['montos_por_mes'][periodo] += cobrado + pendiente
                cliente['real_por_mes'][periodo] += cobrado
                cliente['proyectado_por_mes'][periodo] += pendiente
                
                # Guardar factura para drill-down
                if len(cliente['facturas']) < 50:
                    cliente['facturas'].append({
                        'name': f['name'],
                        'move_id': f['id'],
                        'tipo': move_type,
                        'total': amount_total,
                        'cobrado': cobrado,
                        'pendiente': pendiente,
                        'fecha': fecha,
                        'payment_state': payment_state
                    })
            
            # Calcular montos_por_mes como suma de real + proyectado por período
            montos_por_mes_total = defaultdict(float)
            for periodo in set(real_por_mes.keys()) | set(proyectado_por_mes.keys()):
                montos_por_mes_total[periodo] = real_por_mes.get(periodo, 0) + proyectado_por_mes.get(periodo, 0)
            
            # Convertir defaultdicts a dicts normales y ordenar
            cuentas_resultado = []
            for estado_label, estado_data in sorted(estados.items(), key=lambda x: x[1]['orden']):
                etiquetas_list = []
                for cliente_name, cliente_data in sorted(estado_data['etiquetas'].items(), key=lambda x: x[1]['monto'], reverse=True):
                    etiquetas_list.append({
                        'nombre': cliente_data['nombre'],
                        'monto': cliente_data['monto'],
                        'real': cliente_data['real'],
                        'proyectado': cliente_data['proyectado'],
                        'montos_por_mes': dict(cliente_data['montos_por_mes']),
                        'real_por_mes': dict(cliente_data['real_por_mes']),
                        'proyectado_por_mes': dict(cliente_data['proyectado_por_mes']),
                        'facturas': cliente_data['facturas'],
                        'total_facturas': len(cliente_data['facturas'])
                    })
                
                cuentas_resultado.append({
                    'codigo': estado_data['codigo'],
                    'nombre': f"{estado_data['icon']} {estado_data['nombre']}",
                    'monto': estado_data['monto'],
                    'real': estado_data['real'],
                    'proyectado': estado_data['proyectado'],
                    'montos_por_mes': dict(estado_data['montos_por_mes']),
                    'real_por_mes': dict(estado_data['real_por_mes']),
                    'proyectado_por_mes': dict(estado_data['proyectado_por_mes']),
                    'etiquetas': etiquetas_list,
                    'es_cuenta_cxc': True
                })
            
            return {
                'real': real_total,
                'proyectado': proyectado_total,
                'ppto': 0.0,
                'real_por_mes': dict(real_por_mes),
                'proyectado_por_mes': dict(proyectado_por_mes),
                'montos_por_mes': dict(montos_por_mes_total),
                'total': real_total + proyectado_total,
                'cuentas': cuentas_resultado,
                'facturas_count': len(facturas)
            }
            
        except Exception as e:
            print(f"[RealProyectado] Error calculando cobros clientes: {e}")
            import traceback
            traceback.print_exc()
            return {
                'real': 0.0,
                'proyectado': 0.0,
                'ppto': 0.0,
                'real_por_mes': {},
                'proyectado_por_mes': {},
                'montos_por_mes': {},
                'cuentas': [],
                'error': str(e)
            }
    
    def calcular_todos(self, fecha_inicio: str, fecha_fin: str, meses_lista: List[str] = None) -> Dict[str, Dict]:
        """
        Calcula REAL/PROYECTADO para todos los conceptos configurados.
        
        Args:
            fecha_inicio: Fecha inicio
            fecha_fin: Fecha fin
            meses_lista: Lista de períodos (meses o semanas)
            
        Returns:
            Dict {concepto_id: {real, proyectado, ppto, ...}}
        """
        resultados = {}
        
        # 1.1.1 - Cobros procedentes de ventas
        print(f"[RealProyectado] Calculando 1.1.1 - Cobros de clientes...")
        resultados['1.1.1'] = self.calcular_cobros_clientes(fecha_inicio, fecha_fin, meses_lista)
        
        # 1.2.1 - Pagos a proveedores
        print(f"[RealProyectado] Calculando 1.2.1 - Pagos a proveedores...")
        resultados['1.2.1'] = self.calcular_pagos_proveedores(fecha_inicio, fecha_fin, meses_lista)
        
        # 1.2.6 - IVA Exportador
        print(f"[RealProyectado] Calculando 1.2.6 - IVA Exportador...")
        resultados['1.2.6'] = self.calcular_iva_exportador(fecha_inicio, fecha_fin, meses_lista)
        
        return resultados
    
    def enriquecer_concepto(self, concepto: Dict, 
                           real_proyectado_data: Dict,
                           concepto_id: str) -> Dict:
        """
        Enriquece un concepto con datos de REAL/PROYECTADO y estructura jerárquica.
        
        Para conceptos especiales (1.2.1, 1.2.6), reemplaza las cuentas existentes
        con la estructura calculada por este módulo y actualiza montos_por_mes.
        
        Args:
            concepto: Dict del concepto existente
            real_proyectado_data: Resultado de calcular_todos()
            concepto_id: ID del concepto (ej: '1.2.1')
            
        Returns:
            Concepto enriquecido con campos real, proyectado, ppto y cuentas
        """
        if concepto_id in real_proyectado_data:
            data = real_proyectado_data[concepto_id]
            concepto['real'] = data.get('real', 0)
            concepto['proyectado'] = data.get('proyectado', 0)
            concepto['ppto'] = data.get('ppto', 0)
            concepto['real_por_mes'] = data.get('real_por_mes', {})
            concepto['proyectado_por_mes'] = data.get('proyectado_por_mes', {})
            
            # ACTUALIZAR montos_por_mes - usar directamente el calculado si existe
            montos_por_mes = data.get('montos_por_mes', {})
            if montos_por_mes:
                concepto['montos_por_mes'] = montos_por_mes
                concepto['total'] = data.get('total', sum(montos_por_mes.values()))
            
            # Si hay estructura de cuentas, reemplazar/agregar
            if 'cuentas' in data and data['cuentas']:
                concepto['cuentas'] = data['cuentas']
                concepto['tiene_estructura_especial'] = True
        else:
            # Concepto sin datos especiales - usar el total existente como REAL
            concepto['real'] = concepto.get('total', 0)
            concepto['proyectado'] = 0
            concepto['ppto'] = 0
            concepto['real_por_mes'] = concepto.get('montos_por_mes', {})
            concepto['proyectado_por_mes'] = {}
        
        return concepto
