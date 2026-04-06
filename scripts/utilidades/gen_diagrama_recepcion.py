"""
Genera diagrama de flujo del procedimiento PRO-RF-0023
Recepción de Materia Prima - Río Futuro
Exporta como PNG de alta resolución
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import textwrap

def draw_box(ax, x, y, text, box_type='process', width=2.8, height=0.7):
    """Dibuja una caja del diagrama de flujo"""
    colors = {
        'start':    ('#4CAF50', '#FFFFFF', 'round,pad=0.1'),
        'end':      ('#4CAF50', '#FFFFFF', 'round,pad=0.1'),
        'process':  ('#E3F2FD', '#1565C0', 'round,pad=0.05'),
        'decision': ('#FFF3E0', '#E65100', 'round,pad=0.05'),
        'reject':   ('#FFEBEE', '#C62828', 'round,pad=0.05'),
        'quality':  ('#F3E5F5', '#6A1B9A', 'round,pad=0.05'),
        'iqf':      ('#E3F2FD', '#1565C0', 'round,pad=0.05'),
        'block':    ('#FFF3E0', '#E65100', 'round,pad=0.05'),
        'organic':  ('#E8F5E9', '#2E7D32', 'round,pad=0.05'),
        'storage':  ('#E0F7FA', '#00695C', 'round,pad=0.05'),
    }
    
    facecolor, textcolor, boxstyle = colors.get(box_type, colors['process'])
    
    if box_type == 'decision':
        # Rombo para decisiones
        diamond_w = width * 0.52
        diamond_h = height * 0.95
        diamond = plt.Polygon([
            (x, y + diamond_h/2),
            (x + diamond_w/2, y),
            (x, y - diamond_h/2),
            (x - diamond_w/2, y),
        ], closed=True, facecolor='#FFF3E0', edgecolor='#E65100', linewidth=1.5, zorder=3)
        ax.add_patch(diamond)
        wrapped = textwrap.fill(text, width=18)
        ax.text(x, y, wrapped, ha='center', va='center', fontsize=6.5,
                fontweight='bold', color=textcolor, zorder=4)
        return
    
    box = FancyBboxPatch((x - width/2, y - height/2), width, height,
                          boxstyle=boxstyle, facecolor=facecolor,
                          edgecolor=textcolor, linewidth=1.3, zorder=3)
    ax.add_patch(box)
    
    wrapped = textwrap.fill(text, width=32)
    fontsize = 7 if len(text) > 60 else 7.5
    ax.text(x, y, wrapped, ha='center', va='center', fontsize=fontsize,
            fontweight='bold' if box_type in ('start', 'end') else 'normal',
            color=textcolor, zorder=4)

def draw_arrow(ax, x1, y1, x2, y2, label='', color='#555555'):
    """Dibuja flecha entre cajas"""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=1.3),
                zorder=2)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        offset_x = 0.15 if x1 != x2 else 0
        offset_y = 0.08 if y1 == y2 else 0
        ax.text(mx + offset_x, my + offset_y, label, fontsize=6.5,
                ha='center', va='center', color='#C62828', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.15', facecolor='white', edgecolor='#ddd', alpha=0.9),
                zorder=5)

def main():
    fig, ax = plt.subplots(1, 1, figsize=(16, 28))
    ax.set_xlim(-5, 5)
    ax.set_ylim(-30, 2)
    ax.axis('off')
    
    # ===== TÍTULO =====
    ax.text(0, 1.5, 'PRO-RF-0023  RECEPCIÓN DE MATERIA PRIMA', 
            ha='center', va='center', fontsize=16, fontweight='bold', color='#1B5E20',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#E8F5E9', edgecolor='#4CAF50', linewidth=2))
    ax.text(0, 0.85, 'Río Futuro Procesos — Diagrama de Flujo del Procedimiento',
            ha='center', va='center', fontsize=10, color='#555555', style='italic')

    # ===== COLUMNA CENTRAL (flujo principal) =====
    cx = 0  # centro X
    
    # 1. INICIO
    y = 0
    draw_box(ax, cx, y, 'LLEGADA DEL TRANSPORTE A PLANTA', 'start', 3.2, 0.6)
    
    # 2. Decisión: Guía de despacho
    y1 = -1.2
    draw_box(ax, cx, y1, '¿Trae Guía de\nDespacho?', 'decision', 3, 1.0)
    draw_arrow(ax, cx, y - 0.3, cx, y1 + 0.5)
    
    # 3. Rechazo (derecha)
    rx = 3.5
    draw_box(ax, rx, y1, 'RECHAZAR INGRESO\nNotificar a Jefe de Planta', 'reject', 2.6, 0.65)
    draw_arrow(ax, cx + 0.75, y1, rx - 1.3, y1, 'No')
    
    # 4. Verificar datos guía
    y2 = -2.6
    draw_box(ax, cx, y2, 'Verificar datos de la Guía de Despacho:\n• Productor  • Nº Bandejas  • Fecha\n• Producto  • Variedad  • Calidad\n• Chofer  • Patente camión', 'process', 3.2, 0.95)
    draw_arrow(ax, cx, y1 - 0.5, cx, y2 + 0.48, 'Sí')
    
    # 5. Decisión: Datos correctos
    y3 = -4.0
    draw_box(ax, cx, y3, '¿Datos completos\ny correctos?', 'decision', 3, 1.0)
    draw_arrow(ax, cx, y2 - 0.48, cx, y3 + 0.5)
    
    # Rechazo datos incorrectos (derecha)
    draw_box(ax, rx, y3, 'RECHAZAR INGRESO\nSolicitar corrección de guía', 'reject', 2.6, 0.65)
    draw_arrow(ax, cx + 0.75, y3, rx - 1.3, y3, 'No')
    
    # 6. Autorizar ingreso
    y4 = -5.3
    draw_box(ax, cx, y4, 'Autorizar ingreso del camión\na la zona de descarga', 'process', 3.0, 0.6)
    draw_arrow(ax, cx, y3 - 0.5, cx, y4 + 0.3, 'Sí')
    
    # 7. Descarga
    y5 = -6.4
    draw_box(ax, cx, y5, 'Descarga de Pallets\nen zona de recepción', 'process', 3.0, 0.6)
    draw_arrow(ax, cx, y4 - 0.3, cx, y5 + 0.3)
    
    # 8. Pesaje
    y6 = -7.7
    draw_box(ax, cx, y6, 'Pesaje de cada Pallet\nPeso Bruto − Tara (~18 kg) = Peso Neto', 'process', 3.2, 0.7)
    draw_arrow(ax, cx, y5 - 0.3, cx, y6 + 0.35)
    
    # 9. Registro peso
    y7 = -8.9
    draw_box(ax, cx, y7, 'Registrar peso neto por pallet\nen planilla de recepción', 'process', 3.0, 0.6)
    draw_arrow(ax, cx, y6 - 0.35, cx, y7 + 0.3)
    
    # 10. Decisión: orgánica?
    y8 = -10.2
    draw_box(ax, cx, y8, '¿Es Materia Prima\nOrgánica?', 'decision', 3, 1.0)
    draw_arrow(ax, cx, y7 - 0.3, cx, y8 + 0.5)
    
    # 11. Orgánica (izquierda)
    lx = -3.5
    draw_box(ax, lx, y8, 'Separar e identificar como\nMP ORGÁNICA\n(zona exclusiva, sin mezcla)', 'organic', 2.8, 0.8)
    draw_arrow(ax, cx - 0.75, y8, lx + 1.4, y8, 'Sí')
    
    # 12. Convencional (derecha)
    draw_box(ax, rx, y8, 'Identificar como\nMP CONVENCIONAL', 'process', 2.6, 0.6)
    draw_arrow(ax, cx + 0.75, y8, rx - 1.3, y8, 'No')
    
    # Flechas convergentes al muestreo
    y9 = -11.8
    draw_arrow(ax, lx, y8 - 0.4, cx - 0.3, y9 + 0.5)
    draw_arrow(ax, rx, y8 - 0.3, cx + 0.3, y9 + 0.5)
    
    # 13. Muestreo
    draw_box(ax, cx, y9, 'MUESTREO según cantidad de pallets', 'quality', 3.2, 0.6)
    
    # 14. Tabla de muestreo (derecha)
    y10 = -13.3
    draw_box(ax, cx, y10, 
             'REGLA DE MUESTREO:\n'
             '1-2 pallets → 1 análisis\n'
             '3-5 pallets → 2 análisis\n'
             '6-8 pallets → 3 análisis\n'
             '9-12 pallets → 4 análisis\n'
             '13-15 pallets → 5 análisis\n'
             '>15 pallets → 6 análisis',
             'quality', 3.0, 1.5)
    draw_arrow(ax, cx, y9 - 0.3, cx, y10 + 0.75)
    
    # 15. Análisis calidad
    y11 = -14.9
    draw_box(ax, cx, y11, 'Análisis de Calidad en Laboratorio\n(% fruta IQF vs defectos)', 'quality', 3.2, 0.7)
    draw_arrow(ax, cx, y10 - 0.75, cx, y11 + 0.35)
    
    # 16. Decisión resultado
    y12 = -16.3
    draw_box(ax, cx, y12, '¿Resultado\nde Calidad?', 'decision', 3, 1.0)
    draw_arrow(ax, cx, y11 - 0.35, cx, y12 + 0.5)
    
    # 17. IQF (izquierda)
    draw_box(ax, lx, y12, 'Clasificar como\nCALIDAD IQF\n(70% - 100% fruta apta)', 'iqf', 2.8, 0.8)
    draw_arrow(ax, cx - 0.75, y12, lx + 1.4, y12, 'IQF\n70-100%')
    
    # 18. Block (derecha)
    draw_box(ax, rx, y12, 'Clasificar como\nCALIDAD BLOCK\n(0% - 69% fruta apta)', 'block', 2.8, 0.8)
    draw_arrow(ax, cx + 0.75, y12, rx - 1.4, y12, 'Block\n0-69%')
    
    # 19. Rechazada (abajo derecha)
    y_rej = -17.8
    draw_box(ax, rx, y_rej, 'RECHAZADA\nNotificar rechazo al proveedor', 'reject', 2.8, 0.65)
    draw_arrow(ax, cx + 0.5, y12 - 0.5, rx - 0.5, y_rej + 0.33, 'Rechazada')
    
    # Rechazo → devolución
    y_dev = -19.0
    draw_box(ax, rx, y_dev, 'Devolución o disposición\nde MP rechazada\nDocumentar y notificar', 'reject', 2.8, 0.8)
    draw_arrow(ax, rx, y_rej - 0.33, rx, y_dev + 0.4)
    
    # 20. Asignar Lote (convergencia IQF y Block)
    y13 = -18.2
    draw_box(ax, cx - 0.3, y13, 'Asignar Nº de Lote\n(Correlativo interno planta)', 'process', 3.0, 0.65)
    draw_arrow(ax, lx, y12 - 0.4, cx - 0.7, y13 + 0.33)
    draw_arrow(ax, rx - 0.5, y12 - 0.4, cx + 0.1, y13 + 0.33)
    
    # 21. Etiquetado
    y14 = -19.5
    draw_box(ax, cx - 0.3, y14, 'Etiquetado de cada Pallet:\n• Nº Lote  • Producto  • Variedad\n• Peso Neto  • Fecha recepción\n• Calidad (IQF/Block)  • Productor', 'process', 3.2, 0.95)
    draw_arrow(ax, cx - 0.3, y13 - 0.33, cx - 0.3, y14 + 0.48)
    
    # 22. Cámara de frío
    y15 = -20.9
    draw_box(ax, cx - 0.3, y15, 'Ingreso a Cámara de Frío\n(Almacenamiento refrigerado)', 'storage', 3.0, 0.65)
    draw_arrow(ax, cx - 0.3, y14 - 0.48, cx - 0.3, y15 + 0.33)
    
    # 23. Registro Odoo
    y16 = -22.1
    draw_box(ax, cx - 0.3, y16, 'Registro en Sistema Odoo ERP\n(Recepción completada)', 'end', 3.0, 0.65)
    draw_arrow(ax, cx - 0.3, y15 - 0.33, cx - 0.3, y16 + 0.33)
    
    # ===== LEYENDA =====
    legend_y = -23.5
    ax.text(-4.2, legend_y, 'LEYENDA:', fontsize=9, fontweight='bold', color='#333')
    
    legend_items = [
        ('#E3F2FD', '#1565C0', 'Proceso / Actividad'),
        ('#FFF3E0', '#E65100', 'Decisión'),
        ('#FFEBEE', '#C62828', 'Rechazo'),
        ('#F3E5F5', '#6A1B9A', 'Control de Calidad'),
        ('#E8F5E9', '#2E7D32', 'MP Orgánica'),
        ('#E0F7FA', '#00695C', 'Almacenamiento'),
        ('#4CAF50', '#FFFFFF', 'Inicio / Fin'),
    ]
    
    for i, (fc, ec, label) in enumerate(legend_items):
        lx_pos = -4.2 + (i % 4) * 2.3
        ly_pos = legend_y - 0.55 - (i // 4) * 0.55
        box = FancyBboxPatch((lx_pos, ly_pos - 0.15), 0.4, 0.3,
                              boxstyle='round,pad=0.05', facecolor=fc, edgecolor=ec, linewidth=1.2)
        ax.add_patch(box)
        ax.text(lx_pos + 0.55, ly_pos, label, fontsize=7.5, va='center', color='#333')
    
    # Pie de página
    ax.text(0, -25.2, 'Río Futuro Procesos  •  Procedimiento de Recepción de Materia Prima  •  PRO-RF-0023',
            ha='center', va='center', fontsize=8, color='#999', style='italic')
    
    plt.tight_layout()
    output_path = r'c:\Users\HP\Desktop\dash\proyectos\Diagrama_Recepcion_MP_PRO-RF-0023.png'
    fig.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    print(f"✅ Diagrama guardado en: {output_path}")

if __name__ == '__main__':
    main()
