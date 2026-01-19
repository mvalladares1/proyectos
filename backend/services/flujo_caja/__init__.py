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

__all__ = [
    'ClasificadorCuentas',
    'OdooQueryManager', 
    'ValidadorFlujo',
    'AgregadorFlujo',
    'ProyeccionFlujo'
]

