"""
Generador de etiquetas PDF para pallets
Usa ReportLab para generar etiquetas con código de barras
"""
import io
from datetime import datetime
from typing import Dict, List
from reportlab.lib.pagesizes import A6, landscape
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.graphics.barcode import code128
from reportlab.graphics import renderPDF


class GeneradorEtiquetasPDF:
    """
    Genera etiquetas PDF con formato específico para pallets.
    Tamaño aproximado: 10cm x 15cm
    """
    
    # Tamaño de página (10cm x 15cm)
    PAGE_WIDTH = 10 * cm
    PAGE_HEIGHT = 15 * cm
    
    def __init__(self):
        self.buffer = io.BytesIO()
    
    def generar_etiqueta(self, datos: Dict) -> bytes:
        """
        Genera una etiqueta individual con fondo blanco sin bordes.
        
        Args:
            datos: Dict con campos:
                - nombre_producto: str
                - codigo_producto: str
                - peso_pallet_kg: int
                - cantidad_cajas: int
                - fecha_elaboracion: str (formato dd.mm.yyyy)
                - fecha_vencimiento: str (formato dd.mm.yyyy)
                - lote_produccion: str
                - numero_pallet: str
        
        Returns:
            bytes del PDF generado
        """
        # Crear canvas
        c = canvas.Canvas(self.buffer, pagesize=(self.PAGE_WIDTH, self.PAGE_HEIGHT))
        
        # Posición inicial
        y = self.PAGE_HEIGHT - 1.5 * cm
        margin_left = 0.5 * cm
        
        # Nombre producto (negrita)
        c.setFont("Helvetica-Bold", 11)
        producto_text = datos.get('nombre_producto', '')
        c.drawString(margin_left, y, producto_text)
        y -= 0.8 * cm
        
        # Campos de información (negrita)
        c.setFont("Helvetica-Bold", 10)
        
        # CODIGO PRODUCTO
        c.drawString(margin_left, y, f"CODIGO PRODUCTO: {datos.get('codigo_producto', '')}")
        y -= 0.7 * cm
        
        # PESO PALLET
        c.drawString(margin_left, y, f"PESO PALLET: {datos.get('peso_pallet_kg', 0)} KG")
        y -= 0.7 * cm
        
        # CANTIDAD CAJAS
        c.drawString(margin_left, y, f"CANTIDAD CAJAS: {datos.get('cantidad_cajas', 0)}")
        y -= 0.7 * cm
        
        # FECHA ELABORACION
        c.drawString(margin_left, y, f"FECHA ELABORACION: {datos.get('fecha_elaboracion', '')}")
        y -= 0.7 * cm
        
        # FECHA VENCIMIENTO
        c.drawString(margin_left, y, f"FECHA VENCIMIENTO: {datos.get('fecha_vencimiento', '')}")
        y -= 0.7 * cm
        
        # LOTE PRODUCCION
        c.drawString(margin_left, y, f"LOTE PRODUCCION: {datos.get('lote_produccion', '')}")
        y -= 0.7 * cm
        
        # NUMERO DE PALLET
        c.drawString(margin_left, y, f"NUMERO DE PALLET: {datos.get('numero_pallet', '')}")
        y -= 1.2 * cm
        
        # Código de barras
        numero_pallet = datos.get('numero_pallet', '')
        if numero_pallet:
            try:
                # Crear código de barras Code128
                barcode = code128.Code128(
                    numero_pallet,
                    barWidth=0.4 * cm,
                    barHeight=1.5 * cm,
                    humanReadable=True
                )
                
                # Dibujar código de barras
                barcode.drawOn(c, margin_left, y - 1.5 * cm)
                
            except Exception as e:
                # Si falla el código de barras, mostrar texto
                c.setFont("Helvetica", 8)
                c.drawString(margin_left, y, numero_pallet)
        
        # Finalizar página
        c.showPage()
        c.save()
        
        # Retornar PDF
        pdf_bytes = self.buffer.getvalue()
        self.buffer.seek(0)
        return pdf_bytes
    
    def generar_etiquetas_multiples(self, lista_datos: List[Dict]) -> bytes:
        """
        Genera un PDF con múltiples etiquetas (una por página).
        
        Args:
            lista_datos: Lista de dicts con datos de cada etiqueta
        
        Returns:
            bytes del PDF con todas las etiquetas
        """
        # Crear canvas
        c = canvas.Canvas(self.buffer, pagesize=(self.PAGE_WIDTH, self.PAGE_HEIGHT))
        
        for datos in lista_datos:
            self._dibujar_etiqueta_en_canvas(c, datos)
            c.showPage()
        
        c.save()
        
        # Retornar PDF
        pdf_bytes = self.buffer.getvalue()
        self.buffer.seek(0)
        return pdf_bytes
    
    def _dibujar_etiqueta_en_canvas(self, c: canvas.Canvas, datos: Dict):
        """Dibuja una etiqueta en el canvas actual (fondo blanco sin bordes)."""
        # Posición inicial
        y = self.PAGE_HEIGHT - 1.5 * cm
        margin_left = 0.5 * cm
        
        # Nombre producto (negrita)
        c.setFont("Helvetica-Bold", 11)
        producto_text = datos.get('nombre_producto', '')
        c.drawString(margin_left, y, producto_text)
        y -= 0.8 * cm
        
        # Campos de información (negrita)
        c.setFont("Helvetica-Bold", 10)
        
        # CODIGO PRODUCTO
        c.drawString(margin_left, y, f"CODIGO PRODUCTO: {datos.get('codigo_producto', '')}")
        y -= 0.7 * cm
        
        # PESO PALLET
        c.drawString(margin_left, y, f"PESO PALLET: {datos.get('peso_pallet_kg', 0)} KG")
        y -= 0.7 * cm
        
        # CANTIDAD CAJAS
        c.drawString(margin_left, y, f"CANTIDAD CAJAS: {datos.get('cantidad_cajas', 0)}")
        y -= 0.7 * cm
        
        # FECHA ELABORACION
        c.drawString(margin_left, y, f"FECHA ELABORACION: {datos.get('fecha_elaboracion', '')}")
        y -= 0.7 * cm
        
        # FECHA VENCIMIENTO
        c.drawString(margin_left, y, f"FECHA VENCIMIENTO: {datos.get('fecha_vencimiento', '')}")
        y -= 0.7 * cm
        
        # LOTE PRODUCCION
        c.drawString(margin_left, y, f"LOTE PRODUCCION: {datos.get('lote_produccion', '')}")
        y -= 0.7 * cm
        
        # NUMERO DE PALLET
        c.drawString(margin_left, y, f"NUMERO DE PALLET: {datos.get('numero_pallet', '')}")
        y -= 1.2 * cm
        
        # Código de barras
        numero_pallet = datos.get('numero_pallet', '')
        if numero_pallet:
            try:
                barcode = code128.Code128(
                    numero_pallet,
                    barWidth=0.4 * cm,
                    barHeight=1.5 * cm,
                    humanReadable=True
                )
                barcode.drawOn(c, margin_left, y - 1.5 * cm)
            except Exception as e:
                c.setFont("Helvetica", 8)
                c.drawString(margin_left, y, numero_pallet)
                text_width = c.stringWidth(text, "Helvetica", 8)
                c.drawString((self.PAGE_WIDTH - text_width) / 2, y, text)
