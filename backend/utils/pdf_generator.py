from fpdf import FPDF
import datetime
import pandas as pd

class CommercialReport(FPDF):
    def header(self):
        # Logo placeholder (Optional: could add actual logo)
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(27, 79, 114) # COLOR_NAVY
        self.cell(0, 15, 'RIO FUTURO', 0, 1, 'L')
        
        self.set_y(10)
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, 'HISTORIAL COMERCIAL DETALLADO', 0, 1, 'R')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()} / {{nb}} - Reporte Confidencial Rio Futuro', 0, 0, 'C')

def generate_commercial_pdf(df, kpis, filters):
    pdf = CommercialReport()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    # --- CLIENT INFORMATION HEADER ---
    pdf.set_fill_color(27, 79, 114)
    pdf.set_text_color(255)
    pdf.set_font('Helvetica', 'B', 12)
    client_name = filters.get('cliente', ['CLIENTE GENERAL'])[0]
    pdf.cell(0, 10, f'   CLIENTE: {client_name.upper()}', 0, 1, 'L', True)
    
    pdf.set_text_color(0)
    pdf.set_font('Helvetica', '', 10)
    pdf.ln(2)
    years = ", ".join(map(str, filters.get('anio', ['Todos'])))
    pdf.cell(0, 7, f'Período: {years}', 0, 1)
    
    pdf.ln(5)
    
    # --- KPI SUMMARY BOXES ---
    # Draw simple boxes for KPIs
    pdf.set_fill_color(240, 244, 248)
    pdf.set_draw_color(200, 200, 200)
    
    # KPI 1 - Total Ventas (dinámico)
    x = pdf.get_x()
    y = pdf.get_y()
    pdf.rect(x, y, 60, 20, 'F')
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(27, 79, 114)
    kpi_label = kpis.get('kpi_label', 'Total Ventas')
    pdf.text(x+5, y+7, f'{kpi_label.upper()} (CLP)')
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0)
    pdf.text(x+5, y+15, f"${kpis.get('total_ventas', 0):,.0f}")
    
    # KPI 2 - Total Kilos (dinámico)
    pdf.rect(x+65, y, 60, 20, 'F')
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(27, 79, 114)
    pdf.text(x+70, y+7, f'{kpi_label.upper()} (KG)')
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0)
    pdf.text(x+70, y+15, f"{kpis.get('total_kilos', 0):,.0f}")
    
    # KPI 3 - Total Comprometido
    pdf.rect(x+130, y, 60, 20, 'F')
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(27, 79, 114)
    pdf.text(x+135, y+7, 'TOTAL COMPROMETIDO (CLP)')
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0)
    pdf.text(x+135, y+15, f"${kpis.get('total_comprometido', 0):,.0f}")
    
    pdf.ln(25)
    
    # --- TIMELINE OF MOVEMENTS ---
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(27, 79, 114)
    pdf.cell(0, 10, 'LÍNEA DE TIEMPO DE DOCUMENTOS', 0, 1, 'L')
    pdf.set_draw_color(27, 79, 114)
    pdf.line(pdf.get_x(), pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    if df.empty:
        pdf.set_font('Helvetica', 'I', 10)
        pdf.cell(0, 10, 'No se encontraron movimientos para el período seleccionado.', 0, 1)
        return bytes(pdf.output())

    # Agrupar por Documento
    df_sorted = df.sort_values(['date', 'documento'], ascending=[False, False])
    grouped = df_sorted.groupby(['documento', 'date', 'tipo'], sort=False)
    
    for (doc, date, tipo), group in grouped:
        # Header of the document (The "Timeline Node")
        if pdf.get_y() > 240: pdf.add_page()
        
        if tipo == 'Comprometido':
            pdf.set_fill_color(254, 249, 231) # Amarillo claro para comprometido
        else:
            pdf.set_fill_color(235, 245, 251) # Azul claro para facturas/NC
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(0)
        
        # Draw a square bullet point (compatibility fix)
        pdf.set_fill_color(27, 79, 114)
        pdf.rect(14, pdf.get_y() + 3, 2, 2, 'F')
        
        pdf.set_x(20)
        color_tipo = tipo.upper()
        pdf.cell(0, 8, f"{date}  |  {doc}  |  {color_tipo}", 0, 1, 'L')
        
        # Table of items for this document
        pdf.set_x(25)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(40, 7, 'Especie', 1, 0, 'C', True)
        pdf.cell(30, 7, 'Manejo', 1, 0, 'C', True)
        pdf.cell(30, 7, 'Programa', 1, 0, 'C', True)
        pdf.cell(30, 7, 'Kilos', 1, 0, 'C', True)
        pdf.cell(35, 7, 'Monto (CLP)', 1, 1, 'C', True)
        
        pdf.set_font('Helvetica', '', 8)
        doc_total_monto = 0
        doc_total_kilos = 0
        
        for _, row in group.iterrows():
            if pdf.get_y() > 270: pdf.add_page()
            pdf.set_x(25)
            pdf.cell(40, 6, str(row['especie']), 1, 0, 'L')
            pdf.cell(30, 6, str(row['manejo']), 1, 0, 'L')
            pdf.cell(30, 6, str(row['programa']), 1, 0, 'L')
            pdf.cell(30, 6, f"{row['kilos']:,.0f}", 1, 0, 'R')
            pdf.cell(35, 6, f"${row['monto']:,.0f}", 1, 1, 'R')
            doc_total_monto += row['monto']
            doc_total_kilos += row['kilos']
            
        # Summary line for the document
        pdf.set_x(25)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.cell(100, 6, 'TOTAL DOCUMENTO', 1, 0, 'R', True)
        pdf.cell(30, 6, f"{doc_total_kilos:,.0f}", 1, 0, 'R', True)
        pdf.cell(35, 6, f"${doc_total_monto:,.0f}", 1, 1, 'R', True)
        
        pdf.ln(5)

    return bytes(pdf.output())
