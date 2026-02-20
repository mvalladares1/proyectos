"""
Routers package initialization
"""
from . import auth
from . import produccion
from . import bandejas
from . import demo
from . import containers
from . import stock
from . import estado_resultado
from . import presupuesto
from . import permissions
from . import recepcion
from . import rendimiento
from . import compras
from . import automatizaciones
from . import comercial
from . import flujo_caja

__all__ = [
	'auth', 'produccion', 'bandejas', 'demo', 'containers',
	'stock', 'estado_resultado', 'presupuesto', 'permissions', 'recepcion',
	'rendimiento', 'compras', 'automatizaciones', 'comercial', 'flujo_caja'
]
