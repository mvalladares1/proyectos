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
        Genera una etiqueta individual.
        
        Args:
            datos: Dict con campos:
                - cliente: str
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
        y = self.PAGE_HEIGHT - 1 * cm
        margin_left = 0.5 * cm
        
        # Cliente (centrado, negrita)
        c.setFont("Helvetica-Bold", 11)
        cliente_text = datos.get('cliente', '')
        text_width = c.stringWidth(cliente_text, "Helvetica-Bold", 11)
        c.drawString((self.PAGE_WIDTH - text_width) / 2, y, cliente_text)
        y -= 0.6 * cm
        
        # Nombre producto (centrado, negrita)
        c.setFont("Helvetica-Bold", 10)
        producto_text = datos.get('nombre_producto', '')
        # Dividir en múltiples líneas si es muy largo
        max_width = self.PAGE_WIDTH - 1 * cm
        if c.stringWidth(producto_text, "Helvetica-Bold", 10) > max_width:
            # Dividir en palabras
            palabras = producto_text.split()
            linea_actual = ""
            for palabra in palabras:
                test_linea = linea_actual + (" " if linea_actual else "") + palabra
                if c.stringWidth(test_linea, "Helvetica-Bold", 10) <= max_width:
                    linea_actual = test_linea
                else:
                    # Dibujar línea actual
                    text_width = c.stringWidth(linea_actual, "Helvetica-Bold", 10)
                    c.drawString((self.PAGE_WIDTH - text_width) / 2, y, linea_actual)
                    y -= 0.5 * cm
                    linea_actual = palabra
            # Última línea
            if linea_actual:
                text_width = c.stringWidth(linea_actual, "Helvetica-Bold", 10)
                c.drawString((self.PAGE_WIDTH - text_width) / 2, y, linea_actual)
                y -= 0.7 * cm
        else:
            text_width = c.stringWidth(producto_text, "Helvetica-Bold", 10)
            c.drawString((self.PAGE_WIDTH - text_width) / 2, y, producto_text)
            y -= 0.7 * cm
        
        # Campos de información (negrita)
        c.setFont("Helvetica-Bold", 9)
        
        # CODIGO PRODUCTO
        c.drawString(margin_left, y, f"CODIGO PRODUCTO: {datos.get('codigo_producto', '')}")
        y -= 0.6 * cm
        
        # PESO PALLET
        c.drawString(margin_left, y, f"PESO PALLET: {datos.get('peso_pallet_kg', 0)} KG")
        y -= 0.6 * cm
        
        # CANTIDAD CAJAS
        c.drawString(margin_left, y, f"CANTIDAD CAJAS: {datos.get('cantidad_cajas', 0)}")
        y -= 0.6 * cm
        
        # FECHA ELABORACION
        c.drawString(margin_left, y, f"FECHA ELABORACION: {datos.get('fecha_elaboracion', '')}")
        y -= 0.6 * cm
        
        # FECHA VENCIMIENTO
        c.drawString(margin_left, y, f"FECHA VENCIMIENTO: {datos.get('fecha_vencimiento', '')}")
        y -= 0.6 * cm
        
        # LOTE PRODUCCION
        c.drawString(margin_left, y, f"LOTE PRODUCCION: {datos.get('lote_produccion', '')}")
        y -= 0.6 * cm
        
        # NUMERO DE PALLET
        c.drawString(margin_left, y, f"NUMERO DE PALLET: {datos.get('numero_pallet', '')}")
        y -= 1 * cm
        
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
                
                # Centrar código de barras
                barcode_width = barcode.width
                barcode_x = (self.PAGE_WIDTH - barcode_width) / 2
                barcode.drawOn(c, barcode_x, y - 1.5 * cm)
                
            except Exception as e:
                # Si falla el código de barras, mostrar texto
                c.setFont("Helvetica", 8)
                text = numero_pallet
                text_width = c.stringWidth(text, "Helvetica", 8)
                c.drawString((self.PAGE_WIDTH - text_width) / 2, y, text)
        
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
        """Dibuja una etiqueta en el canvas actual."""
        # Posición inicial
        y = self.PAGE_HEIGHT - 1 * cm
        margin_left = 0.5 * cm
        
        # Cliente (centrado, negrita)
        c.setFont("Helvetica-Bold", 11)
        cliente_text = datos.get('cliente', '')
        text_width = c.stringWidth(cliente_text, "Helvetica-Bold", 11)
        c.drawString((self.PAGE_WIDTH - text_width) / 2, y, cliente_text)
        y -= 0.6 * cm
        
        # Nombre producto (centrado, negrita)
        c.setFont("Helvetica-Bold", 10)
        producto_text = datos.get('nombre_producto', '')
        max_width = self.PAGE_WIDTH - 1 * cm
        
        if c.stringWidth(producto_text, "Helvetica-Bold", 10) > max_width:
            palabras = producto_text.split()
            linea_actual = ""
            for palabra in palabras:
                test_linea = linea_actual + (" " if linea_actual else "") + palabra
                if c.stringWidth(test_linea, "Helvetica-Bold", 10) <= max_width:
                    linea_actual = test_linea
                else:
                    text_width = c.stringWidth(linea_actual, "Helvetica-Bold", 10)
                    c.drawString((self.PAGE_WIDTH - text_width) / 2, y, linea_actual)
                    y -= 0.5 * cm
                    linea_actual = palabra
            if linea_actual:
                text_width = c.stringWidth(linea_actual, "Helvetica-Bold", 10)
                c.drawString((self.PAGE_WIDTH - text_width) / 2, y, linea_actual)
                y -= 0.7 * cm
        else:
            text_width = c.stringWidth(producto_text, "Helvetica-Bold", 10)
            c.drawString((self.PAGE_WIDTH - text_width) / 2, y, producto_text)
            y -= 0.7 * cm
        
        # Campos de información
        c.setFont("Helvetica-Bold", 9)
        
        c.drawString(margin_left, y, f"CODIGO PRODUCTO: {datos.get('codigo_producto', '')}")
        y -= 0.6 * cm
        
        c.drawString(margin_left, y, f"PESO PALLET: {datos.get('peso_pallet_kg', 0)} KG")
        y -= 0.6 * cm
        
        c.drawString(margin_left, y, f"CANTIDAD CAJAS: {datos.get('cantidad_cajas', 0)}")
        y -= 0.6 * cm
        
        c.drawString(margin_left, y, f"FECHA ELABORACION: {datos.get('fecha_elaboracion', '')}")
        y -= 0.6 * cm
        
        c.drawString(margin_left, y, f"FECHA VENCIMIENTO: {datos.get('fecha_vencimiento', '')}")
        y -= 0.6 * cm
        
        c.drawString(margin_left, y, f"LOTE PRODUCCION: {datos.get('lote_produccion', '')}")
        y -= 0.6 * cm
        
        c.drawString(margin_left, y, f"NUMERO DE PALLET: {datos.get('numero_pallet', '')}")
        y -= 1 * cm
        
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
                barcode_width = barcode.width
                barcode_x = (self.PAGE_WIDTH - barcode_width) / 2
                barcode.drawOn(c, barcode_x, y - 1.5 * cm)
            except Exception:
                c.setFont("Helvetica", 8)
                text = numero_pallet
                text_width = c.stringWidth(text, "Helvetica", 8)
                c.drawString((self.PAGE_WIDTH - text_width) / 2, y, text)
