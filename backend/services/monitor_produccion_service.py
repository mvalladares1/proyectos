"""
Servicio de Monitor de Producción Diario
Almacena y gestiona snapshots de procesos para tracking de avance
"""
import json
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from shared.odoo_client import OdooClient
from backend.utils import clean_record


class MonitorProduccionService:
    """
    Servicio para monitorear procesos de producción en tiempo real.
    Almacena snapshots para tracking histórico de avance.
    """
    
    SNAPSHOTS_DIR = Path(__file__).parent.parent / "data" / "monitor_snapshots"
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
        # Crear directorio de snapshots si no existe
        self.SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    
    def get_procesos_activos(self, fecha: str, planta: Optional[str] = None,
                             sala: Optional[str] = None, 
                             producto: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene procesos activos (ni done ni cancel) - TODOS los pendientes actuales.
        
        Args:
            fecha: Fecha en formato YYYY-MM-DD (referencia, no filtra)
            planta: Filtrar por planta (VILKUN, RIO FUTURO, Todas)
            sala: Filtrar por sala de proceso
            producto: Filtrar por nombre de producto
        
        Returns:
            Dict con procesos activos, estadísticas y metadata
        """
        # Construir dominio base: TODOS los procesos no cerrados ni cancelados
        domain = [
            ['state', 'not in', ['done', 'cancel']]
        ]
        
        # Filtro por sala
        if sala and sala != "Todas":
            domain.append(['x_studio_sala_de_proceso', 'ilike', sala])
        
        # Filtro por producto
        if producto and producto != "Todos":
            domain.append(['product_id', 'ilike', producto])
        
        ordenes = self.odoo.search_read(
            'mrp.production',
            domain,
            ['name', 'product_id', 'product_qty', 'qty_produced', 'state', 
             'date_start', 'date_finished', 'date_planned_start', 'user_id',
             'x_studio_sala_de_proceso', 'x_studio_inicio_de_proceso',
             'x_studio_termino_de_proceso', 'x_studio_dotacin'],
            limit=1000,
            order='x_studio_inicio_de_proceso desc'
        )
        
        procesos = [clean_record(o) for o in ordenes]
        
        # Aplicar filtro de planta
        if planta and planta != "Todas":
            procesos = self._filtrar_por_planta(procesos, planta)
        
        # Calcular estadísticas
        stats = self._calcular_estadisticas(procesos)
        
        return {
            "procesos": procesos,
            "estadisticas": stats,
            "fecha": fecha,
            "filtros": {
                "planta": planta,
                "sala": sala,
                "producto": producto
            }
        }
    
    def get_procesos_cerrados_dia(self, fecha: str, planta: Optional[str] = None,
                                   sala: Optional[str] = None,
                                   fecha_fin: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene procesos que se cerraron (pasaron a done) en un rango de fechas.
        Usa date_finished como campo principal (momento real de cierre en Odoo).
        
        Args:
            fecha: Fecha inicio en formato YYYY-MM-DD
            planta: Filtrar por planta
            sala: Filtrar por sala
            fecha_fin: Fecha fin en formato YYYY-MM-DD (opcional, si no se da usa fecha)
        
        Returns:
            Dict con procesos cerrados y estadísticas
        """
        # Usar fecha_fin si se proporciona, sino usar fecha
        fecha_hasta = fecha_fin or fecha
        
        # Procesos cerrados: estado done y date_finished en el rango
        # date_finished es el campo real que indica cuándo se cerró el proceso
        domain = [
            ['state', '=', 'done'],
            ['date_finished', '>=', fecha],
            ['date_finished', '<=', fecha_hasta + ' 23:59:59']
        ]
        
        if sala and sala != "Todas":
            domain.append(['x_studio_sala_de_proceso', 'ilike', sala])
        
        ordenes = self.odoo.search_read(
            'mrp.production',
            domain,
            ['name', 'product_id', 'product_qty', 'qty_produced', 'state', 
             'date_start', 'date_finished', 'date_planned_start', 'user_id',
             'x_studio_sala_de_proceso', 'x_studio_inicio_de_proceso',
             'x_studio_termino_de_proceso'],
            limit=500,
            order='date_finished asc'
        )
        
        procesos = [clean_record(o) for o in ordenes]
        
        if planta and planta != "Todas":
            procesos = self._filtrar_por_planta(procesos, planta)
        
        stats = self._calcular_estadisticas(procesos)
        
        return {
            "procesos": procesos,
            "estadisticas": stats,
            "fecha": fecha
        }
    
    def get_evolucion_rango(self, fecha_inicio: str, fecha_fin: str,
                            planta: Optional[str] = None,
                            sala: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene la evolución de procesos creados vs cerrados en un rango de fechas.
        
        Args:
            fecha_inicio: Fecha inicio YYYY-MM-DD
            fecha_fin: Fecha fin YYYY-MM-DD
            planta: Filtrar por planta
            sala: Filtrar por sala
        
        Returns:
            Dict con datos de evolución por día
        """
        evolucion = []
        
        # Obtener todos los procesos creados en el rango (usando x_studio_inicio_de_proceso)
        domain_creados = [
            ['state', '!=', 'cancel'],
            '|',
            '&', ['x_studio_inicio_de_proceso', '>=', fecha_inicio],
                 ['x_studio_inicio_de_proceso', '<=', fecha_fin + ' 23:59:59'],
            '&', ['x_studio_inicio_de_proceso', '=', False],
            '&', ['date_planned_start', '>=', fecha_inicio],
                 ['date_planned_start', '<=', fecha_fin + ' 23:59:59']
        ]
        
        if sala and sala != "Todas":
            domain_creados.append(['x_studio_sala_de_proceso', 'ilike', sala])
        
        procesos_creados = self.odoo.search_read(
            'mrp.production',
            domain_creados,
            ['name', 'product_id', 'product_qty', 'qty_produced', 'state',
             'date_planned_start', 'date_finished', 'x_studio_sala_de_proceso',
             'x_studio_inicio_de_proceso', 'x_studio_termino_de_proceso'],
            limit=2000,
            order='x_studio_inicio_de_proceso asc'
        )
        
        procesos_creados = [clean_record(o) for o in procesos_creados]
        
        if planta and planta != "Todas":
            procesos_creados = self._filtrar_por_planta(procesos_creados, planta)
        
        # Obtener procesos cerrados en el rango (usando x_studio_termino_de_proceso)
        domain_cerrados = [
            ['state', '=', 'done'],
            '|',
            '&', ['x_studio_termino_de_proceso', '>=', fecha_inicio],
                 ['x_studio_termino_de_proceso', '<=', fecha_fin + ' 23:59:59'],
            '&', ['x_studio_termino_de_proceso', '=', False],
            '&', ['date_finished', '>=', fecha_inicio],
                 ['date_finished', '<=', fecha_fin + ' 23:59:59']
        ]
        
        if sala and sala != "Todas":
            domain_cerrados.append(['x_studio_sala_de_proceso', 'ilike', sala])
        
        procesos_cerrados = self.odoo.search_read(
            'mrp.production',
            domain_cerrados,
            ['name', 'product_id', 'product_qty', 'qty_produced', 'state',
             'date_finished', 'x_studio_sala_de_proceso',
             'x_studio_inicio_de_proceso', 'x_studio_termino_de_proceso'],
            limit=2000,
            order='x_studio_termino_de_proceso asc'
        )
        
        procesos_cerrados = [clean_record(o) for o in procesos_cerrados]
        
        if planta and planta != "Todas":
            procesos_cerrados = self._filtrar_por_planta(procesos_cerrados, planta)
        
        # Agrupar por día
        fecha_actual = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_final = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        while fecha_actual <= fecha_final:
            fecha_str = fecha_actual.strftime('%Y-%m-%d')
            
            # Contar creados del día (usar x_studio_inicio_de_proceso o date_planned_start)
            creados_dia = [p for p in procesos_creados 
                          if (p.get('x_studio_inicio_de_proceso', '') or p.get('date_planned_start', '') or '').startswith(fecha_str)]
            
            # Contar cerrados del día (usar x_studio_termino_de_proceso o date_finished)
            cerrados_dia = [p for p in procesos_cerrados 
                           if (p.get('x_studio_termino_de_proceso', '') or p.get('date_finished', '') or '').startswith(fecha_str)]
            
            # Calcular kg
            kg_creados = sum(p.get('product_qty', 0) or 0 for p in creados_dia)
            kg_cerrados = sum(p.get('qty_produced', 0) or 0 for p in cerrados_dia)
            
            evolucion.append({
                "fecha": fecha_str,
                "fecha_display": fecha_actual.strftime('%d/%m'),
                "procesos_creados": len(creados_dia),
                "procesos_cerrados": len(cerrados_dia),
                "kg_programados": kg_creados,
                "kg_producidos": kg_cerrados,
                "pendientes_acumulados": len(creados_dia) - len(cerrados_dia)
            })
            
            fecha_actual += timedelta(days=1)
        
        # Calcular totales
        totales = {
            "total_creados": sum(e["procesos_creados"] for e in evolucion),
            "total_cerrados": sum(e["procesos_cerrados"] for e in evolucion),
            "total_kg_programados": sum(e["kg_programados"] for e in evolucion),
            "total_kg_producidos": sum(e["kg_producidos"] for e in evolucion),
        }
        
        return {
            "evolucion": evolucion,
            "totales": totales,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin
        }
    
    def guardar_snapshot(self, fecha: str, planta: Optional[str] = None) -> Dict[str, Any]:
        """
        Guarda un snapshot del estado actual de procesos para una fecha.
        
        Args:
            fecha: Fecha del snapshot YYYY-MM-DD
            planta: Planta específica o None para todas
        
        Returns:
            Confirmación del snapshot guardado
        """
        # Obtener datos actuales
        activos = self.get_procesos_activos(fecha, planta)
        cerrados = self.get_procesos_cerrados_dia(fecha, planta)
        
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "fecha": fecha,
            "planta": planta or "Todas",
            "procesos_activos": activos["estadisticas"],
            "procesos_cerrados": cerrados["estadisticas"],
            "detalle_activos": activos["procesos"],
            "detalle_cerrados": cerrados["procesos"]
        }
        
        # Guardar en archivo JSON
        filename = f"snapshot_{fecha}_{planta or 'todas'}_{datetime.now().strftime('%H%M%S')}.json"
        filepath = self.SNAPSHOTS_DIR / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2, default=str)
        
        return {
            "success": True,
            "filename": filename,
            "filepath": str(filepath),
            "snapshot": snapshot
        }
    
    def obtener_snapshots(self, fecha: Optional[str] = None, 
                          limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtiene snapshots guardados.
        
        Args:
            fecha: Filtrar por fecha específica (opcional)
            limit: Límite de resultados
        
        Returns:
            Lista de snapshots
        """
        snapshots = []
        
        # Listar archivos JSON
        for filepath in sorted(self.SNAPSHOTS_DIR.glob("snapshot_*.json"), reverse=True):
            if len(snapshots) >= limit:
                break
            
            # Filtrar por fecha si se especifica
            if fecha and fecha not in filepath.name:
                continue
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data["_filename"] = filepath.name
                    snapshots.append(data)
            except Exception as e:
                continue
        
        return snapshots
    
    def get_salas_disponibles(self) -> List[str]:
        """Obtiene la lista de salas de proceso disponibles."""
        try:
            # Buscar valores únicos de x_studio_sala_de_proceso
            procesos = self.odoo.search_read(
                'mrp.production',
                [['x_studio_sala_de_proceso', '!=', False]],
                ['x_studio_sala_de_proceso'],
                limit=1000
            )
            
            salas = set()
            for p in procesos:
                sala = p.get('x_studio_sala_de_proceso')
                if sala and sala is not False:
                    salas.add(sala)
            
            return sorted(list(salas))
        except Exception:
            return []
    
    def get_productos_disponibles(self) -> List[str]:
        """Obtiene la lista de productos de fabricación disponibles."""
        try:
            procesos = self.odoo.search_read(
                'mrp.production',
                [],
                ['product_id'],
                limit=500
            )
            
            productos = set()
            for p in procesos:
                prod = p.get('product_id')
                if prod:
                    if isinstance(prod, (list, tuple)):
                        productos.add(prod[1])  # (id, name)
                    elif isinstance(prod, dict):
                        productos.add(prod.get('name', ''))
            
            return sorted(list(productos))
        except Exception:
            return []
    
    def _filtrar_por_planta(self, procesos: List[Dict], planta: str) -> List[Dict]:
        """
        Filtra procesos por planta basándose en el NOMBRE de la OF y/o la SALA.
        - VILKUN: nombre empieza con 'VLK/' o sala contiene 'VILKUN' o 'VLK'
        - SAN JOSE: sala contiene 'SAN JOSE' o 'SALA SAN JOSE'
        - RIO FUTURO: todo lo demás
        """
        resultado = []
        for p in procesos:
            nombre = str(p.get('name', '') or '').upper()
            sala = str(p.get('x_studio_sala_de_proceso', '') or '').upper()
            
            # Determinar planta del proceso
            es_vilkun = nombre.startswith('VLK/') or '/VLK/' in nombre or 'VILKUN' in sala or 'VLK' in sala
            es_san_jose = 'SAN JOSE' in sala or 'SAN JOSÉ' in sala
            
            if planta == "VILKUN":
                if es_vilkun:
                    resultado.append(p)
            elif planta == "SAN JOSE":
                if es_san_jose:
                    resultado.append(p)
            elif planta == "RIO FUTURO":
                # Todo lo que NO es VILKUN ni SAN JOSE
                if not es_vilkun and not es_san_jose:
                    resultado.append(p)
        return resultado
    
    def _calcular_estadisticas(self, procesos: List[Dict]) -> Dict[str, Any]:
        """Calcula estadísticas de una lista de procesos."""
        total = len(procesos)
        kg_programados = sum(p.get('product_qty', 0) or 0 for p in procesos)
        kg_producidos = sum(p.get('qty_produced', 0) or 0 for p in procesos)
        kg_pendientes = kg_programados - kg_producidos
        
        # Agrupar por estado
        estados = {}
        for p in procesos:
            estado = p.get('state', 'unknown')
            estados[estado] = estados.get(estado, 0) + 1
        
        # Agrupar por sala
        salas = {}
        for p in procesos:
            sala = p.get('x_studio_sala_de_proceso') or 'Sin Sala'
            if sala not in salas:
                salas[sala] = {"cantidad": 0, "kg": 0}
            salas[sala]["cantidad"] += 1
            salas[sala]["kg"] += p.get('product_qty', 0) or 0
        
        return {
            "total_procesos": total,
            "kg_programados": kg_programados,
            "kg_producidos": kg_producidos,
            "kg_pendientes": kg_pendientes,
            "avance_porcentaje": (kg_producidos / kg_programados * 100) if kg_programados > 0 else 0,
            "por_estado": estados,
            "por_sala": salas
        }
