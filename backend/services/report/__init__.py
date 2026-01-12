"""
Módulo de generación de reportes PDF.
"""
from backend.services.report_service import (
    generate_recepcion_report_pdf,
    generate_bandejas_report_pdf
)

__all__ = [
    'generate_recepcion_report_pdf',
    'generate_bandejas_report_pdf'
]
