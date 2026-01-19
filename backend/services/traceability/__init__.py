"""
Módulo de Trazabilidad - Servicios para obtener y transformar datos de trazabilidad.

Componentes:
- TraceabilityService: Obtiene datos crudos de movimientos de paquetes
- transform_to_sankey: Transforma a formato Sankey (Plotly)
- transform_to_reactflow: Transforma a formato React Flow (streamlit-flow-component)

Uso:
    from backend.services.traceability import (
        TraceabilityService,
        transform_to_sankey,
        transform_to_reactflow,
        convert_for_streamlit_flow
    )
    
    # Obtener datos crudos
    service = TraceabilityService(username, password)
    data = service.get_traceability_data(start_date, end_date)
    
    # Transformar a Sankey
    sankey_data = transform_to_sankey(data)
    
    # Transformar a React Flow
    reactflow_data = transform_to_reactflow(data)
    nodes_data, edges_data = convert_for_streamlit_flow(reactflow_data)
"""

from .traceability_service import TraceabilityService
from .sankey_transformer import transform_to_sankey
from .reactflow_transformer import transform_to_reactflow, convert_for_streamlit_flow

__all__ = [
    "TraceabilityService",
    "transform_to_sankey",
    "transform_to_reactflow",
    "convert_for_streamlit_flow",
]
