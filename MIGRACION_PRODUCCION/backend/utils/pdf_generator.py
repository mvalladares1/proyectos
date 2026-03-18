from fpdf import FPDF
import pandas as pd
import datetime

class PDF(FPDF):
    def header(self):
        # Logo could be added here
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Informe de Relación Comercial', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'Página ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

def generate_commercial_pdf(df: pd.DataFrame, kpis: dict, filters: dict, currency: str = "CLP", metric_type: str = "Ventas ($)") -> bytes:
    """
    Genera un archivo PDF con el informe comercial.
    """
    try:
        pdf = PDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_font('Arial', '', 12)

        # 1. Filtros Aplicados
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Filtros Aplicados:', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        filter_text = []
        for k, v in filters.items():
            if v:
                filter_text.append(f"{k.capitalize()}: {', '.join(map(str, v))}")
        
        pdf.multi_cell(0, 7, "; ".join(filter_text) if filter_text else "Ninguno (Reporte General)")
        pdf.ln(5)

        # 2. Resumen de KPIs
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Resumen General:', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        prefix = "$" if metric_type == "Ventas ($)" else ""
        m_label = currency if metric_type == "Ventas ($)" else "Kilos"
        val_fmt = ",.2f" if currency == "USD" and metric_type == "Ventas ($)" else ",.0f"
        
        pdf.cell(60, 8, f"Total Ventas ({m_label}):", 0, 0)
        pdf.cell(0, 8, f"{prefix}{kpis.get('total_ventas', 0):{val_fmt}}", 0, 1)
        
        pdf.cell(60, 8, f"Total Kilos:", 0, 0)
        pdf.cell(0, 8, f"{kpis.get('total_kilos', 0):{val_fmt}} kg", 0, 1)
        
        pdf.cell(60, 8, f"Comprometido ({m_label}):", 0, 0)
        pdf.cell(0, 8, f"{prefix}{kpis.get('total_comprometido', 0):{val_fmt}}", 0, 1)
        pdf.ln(10)

        # 3. Detalles (Tabla simplificada)
        if not df.empty:
            df_g = df.groupby(['programa', 'especie'])[['kilos', 'monto']].sum().reset_index()
            
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 10, f'Detalle por Programa y Especie ({m_label}):', 0, 1)
            
            # Header Tabla
            pdf.set_font('Arial', 'B', 9)
            pdf.cell(40, 8, "Programa", 1, 0, 'C')
            pdf.cell(40, 8, "Especie", 1, 0, 'C')
            pdf.cell(35, 8, "Kilos", 1, 0, 'C')
            pdf.cell(40, 8, f"Monto ({m_label})", 1, 1, 'C')
            
            pdf.set_font('Arial', '', 9)
            for _, row in df_g.iterrows():
                pdf.cell(40, 8, str(row['programa']), 1, 0)
                pdf.cell(40, 8, str(row['especie']), 1, 0)
                pdf.cell(35, 8, f"{row['kilos']:,.0f}", 1, 0, 'R')
                pdf.cell(40, 8, f"{prefix}{row['monto']:{val_fmt}}", 1, 1, 'R')

        else:
            pdf.cell(0, 10, "No hay datos para mostrar con los filtros seleccionados.", 0, 1)

        return pdf.output(dest='S').encode('latin-1')

    except Exception as e:
        print(f"Error generando PDF: {e}")
        return b""
