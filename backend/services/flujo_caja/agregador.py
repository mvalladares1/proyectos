"""
Módulo de agregación de flujos de caja.
Procesa y agrega movimientos por concepto y período.
"""
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class AgregadorFlujo:
    """Agrega flujos de efectivo por concepto y período."""
    
    def __init__(self, clasificador, catalogo: Dict, meses_lista: List[str]):
        """
        Args:
            clasificador: Instancia con método clasificar_cuenta()
            catalogo: Catálogo de conceptos NIIF
            meses_lista: Lista de períodos ['2026-01', '2026-02', ...]
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
            cuentas_monitoreadas: Códigos de cuentas a filtrar (None = todas)
            parse_periodo_fn: Función para parsear período Odoo a YYYY-MM
        """
        filtrar_monitoreadas = bool(cuentas_monitoreadas)
        
        for grupo in grupos:
            acc_data = grupo.get('account_id')
            balance = grupo.get('balance', 0)
            
            # Parsear período (mensual o semanal)
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
            
            # Extraer código de cuenta del display "[code] name"
            acc_display = acc_data[1] if len(acc_data) > 1 else "Unknown"
            codigo_cuenta = acc_display.split(' ')[0] if ' ' in acc_display else acc_display
            
            # Filtrar por cuentas monitoreadas
            if filtrar_monitoreadas and codigo_cuenta not in cuentas_monitoreadas:
                continue
            
            # Clasificar cuenta
            concepto_id, es_pendiente = self.clasificador(codigo_cuenta)
            
            # Invertir signo para cuentas de ingreso (41) y costo (51)
            # En contabilidad: ingresos son créditos (negativos), pero en flujo de efectivo
            # representan entradas de dinero (positivos)
            # TAMBIEN: Cuentas por cobrar (1103) que se acreditan al cobrar (entrada)
            monto_efectivo = balance
            if codigo_cuenta.startswith('41') or codigo_cuenta.startswith('1103'):
                monto_efectivo = -balance  # Invertir: crédito -> ingreso de efectivo
            
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
            parse_periodo_fn: Función para parsear período
        """
        # Crear mapeo account_id → (concepto_id, codigo_cuenta)
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
            
            # Parsear período
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
        Procesa líneas de cuentas parametrizadas.
        
        Args:
            lineas: Líneas de account.move.line
            clasificar_fn: Función de clasificación
            agrupacion: 'mensual' o 'semanal'
        """
        for linea in lineas:
            acc_data = linea.get('account_id')
            if not acc_data:
                continue
            
            codigo_cuenta = acc_data[1].split(' ')[0] if ' ' in acc_data[1] else acc_data[1]
            balance = linea.get('balance', 0)
            fecha = linea.get('date', '')
            
            # Determinar período
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
            etiqueta = linea.get('name', 'Sin descripción')
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
        Procesa líneas de Cuentas por Cobrar (CxC) para flujo de caja proyectado.
        
        LÓGICA DE FLUJO DE CAJA PARA CxC (11030101):
        
        En contabilidad:
        - Débito en CxC (balance positivo) = Factura emitida → INGRESO ESPERADO
        - Crédito en CxC (balance negativo) = Pago recibido o NC → REDUCCIÓN de CxC
        
        Para flujo de caja PROYECTADO basado en fecha_de_pago:
        - Mostramos el DÉBITO (factura) como ingreso esperado en la fecha de pago acordada
        - Los créditos (cobros ya realizados) reducen el ingreso esperado
        
        El signo final:
        - Balance positivo (débito/factura) → Flujo POSITIVO (esperamos cobrar)
        - Balance negativo (crédito/cobro) → Flujo NEGATIVO (ya se redujo la cuenta)
        
        IMPORTANTE: Usa 'fecha_efectiva' de la línea (fecha_pago si existe, sino fecha_contable)
        
        Args:
            lineas: Líneas de account.move.line con fecha_efectiva enriquecida
            clasificar_fn: Función de clasificación
            agrupacion: 'mensual' o 'semanal'
        """
        for linea in lineas:
            acc_data = linea.get('account_id')
            if not acc_data:
                continue
            
            codigo_cuenta = acc_data[1].split(' ')[0] if ' ' in acc_data[1] else acc_data[1]
            balance = linea.get('balance', 0)
            
            # USAR FECHA_EFECTIVA (fecha pago si existe, sino fecha contable)
            fecha = linea.get('fecha_efectiva') or linea.get('date', '')
            
            # Determinar período basado en fecha_efectiva
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
            
            # SIGNO PARA CxC en Flujo Proyectado:
            # - Balance positivo (débito) = factura → INGRESO esperado (mantener positivo)
            # - Balance negativo (crédito) = pago/NC → Ya cobrado o reducido (mantener negativo)
            # NO invertimos signo para CxC porque queremos mostrar el movimiento real
            monto_efectivo = balance
            
            # Acumular
            if concepto_id not in self.montos_por_concepto_mes:
                self.montos_por_concepto_mes[concepto_id] = {m: 0.0 for m in self.meses_lista}
            
            self.montos_por_concepto_mes[concepto_id][mes_str] += monto_efectivo
            
            # Trackear cuenta
            self._agregar_cuenta(concepto_id, codigo_cuenta, acc_data[1], monto_efectivo, mes_str, acc_data[0])
            
            # Agregar etiqueta (ya viene enriquecida desde get_lineas_cuenta_periodo)
            etiqueta = linea.get('name', 'Sin etiqueta')
            etiqueta_limpia = ' '.join(str(etiqueta).split())[:60] if etiqueta else "Sin etiqueta"
            
            cuenta = self.cuentas_por_concepto[concepto_id][codigo_cuenta]
            if 'etiquetas' not in cuenta:
                cuenta['etiquetas'] = {}
            
            if etiqueta_limpia not in cuenta['etiquetas']:
                cuenta['etiquetas'][etiqueta_limpia] = {
                    'monto': 0.0,
                    'montos_por_mes': {m: 0.0 for m in self.meses_lista}
                }
            
            cuenta['etiquetas'][etiqueta_limpia]['monto'] += monto_efectivo
            if mes_str in self.meses_lista:
                cuenta['etiquetas'][etiqueta_limpia]['montos_por_mes'][mes_str] += monto_efectivo
    
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
                
                # Para out_refund (notas de crédito), invertir signo
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
                
                continue  # No procesar líneas para facturas cliente
            
            # FACTURAS DE PROVEEDOR -> Procesar por línea y cuenta
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
        Retorna los resultados de la agregación.
        
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
        """Formatea cuentas de un concepto para resultado."""
        if concepto_id not in self.cuentas_por_concepto:
            return []
        
        # Ordenar por monto absoluto
        sorted_cuentas = sorted(
            self.cuentas_por_concepto[concepto_id].items(),
            key=lambda x: abs(x[1].get('monto', 0)),
            reverse=True
        )[:15]  # Top 15
        
        resultado = []
        for k, v in sorted_cuentas:
            # Formatear etiquetas - SOLO las que tienen monto en el período consultado
            etiquetas_dict = v.get("etiquetas", {})
            
            # Filtrar etiquetas que tienen al menos un monto != 0 en algún mes del rango
            etiquetas_filtradas = []
            for nombre, datos in etiquetas_dict.items():
                if isinstance(datos, dict):
                    montos_mes = datos.get("montos_por_mes", {})
                    # Solo incluir si tiene algún valor en los meses del rango
                    tiene_valor = any(montos_mes.get(m, 0) != 0 for m in self.meses_lista)
                    if tiene_valor:
                        etiquetas_filtradas.append((nombre, datos))
                elif datos != 0:  # Si es solo un número
                    etiquetas_filtradas.append((nombre, datos))
            
            # Ordenar por mes cronológico y luego por monto dentro del mes
            # Esto agrupa las facturas por el mes en que tienen valor
            def orden_etiqueta(item):
                nombre, datos = item
                if not isinstance(datos, dict):
                    return (len(self.meses_lista), 0)
                montos_mes = datos.get("montos_por_mes", {})
                # Encontrar el primer mes con valor
                for idx, mes in enumerate(self.meses_lista):
                    if montos_mes.get(mes, 0) != 0:
                        # Retornar (índice_mes, -monto_absoluto) para ordenar por mes y luego por monto desc
                        return (idx, -abs(montos_mes.get(mes, 0)))
                return (len(self.meses_lista), 0)
            
            etiquetas_ordenadas = sorted(etiquetas_filtradas, key=orden_etiqueta)[:20]
            
            etiquetas_lista = []
            for nombre, datos in etiquetas_ordenadas:
                if isinstance(datos, dict):
                    etiquetas_lista.append({
                        "nombre": nombre[:60],
                        "monto": round(datos.get("monto", 0), 0),
                        "montos_por_mes": {m: round(datos.get("montos_por_mes", {}).get(m, 0), 0) for m in self.meses_lista}
                    })
                else:
                    etiquetas_lista.append({
                        "nombre": nombre[:60],
                        "monto": round(datos, 0),
                        "montos_por_mes": {m: 0 for m in self.meses_lista}
                    })
            
            resultado.append({
                "codigo": k,
                "nombre": v.get("nombre"),
                "monto": round(v.get("monto", 0), 0),
                "cantidad": v.get("cantidad"),
                "montos_por_mes": {m: round(v.get("montos_por_mes", {}).get(m, 0), 0) for m in self.meses_lista},
                "etiquetas": etiquetas_lista
            })
        
        return resultado
