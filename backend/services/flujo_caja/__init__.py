"""
Módulo de Flujo de Caja.
Estado de Flujo de Efectivo según NIIF IAS 7 (Método Directo).

Exporta clases helper modularizadas.
"""
from .clasificador import ClasificadorCuentas
from .odoo_queries import OdooQueryManager
from .validador import ValidadorFlujo
from .agregador import AgregadorFlujo
from .proyeccion import ProyeccionFlujo
from .real_proyectado import RealProyectadoCalculator

__all__ = [
    'ClasificadorCuentas',
    'OdooQueryManager', 
    'ValidadorFlujo',
    'AgregadorFlujo',
    'ProyeccionFlujo',
    'RealProyectadoCalculator'
]

