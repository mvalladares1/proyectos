"""
PRO-RF-0023 Recepción de Materia Prima - Diagrama de Flujo Profesional
PDF vectorial - Flujo vertical principal limpio, anotaciones laterales discretas.
"""

from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas
import math, os

OUTPUT = r'c:\Users\HP\Desktop\dash\proyectos\Diagrama_Recepcion_MP_PRO-RF-0023.pdf'

# Página vertical grande (tipo poster)
PW = 42*cm
PH = 75*cm

# Paleta profesional (más suave)
BG     = HexColor('#FAFAFA')
C_MAIN = HexColor('#1A237E')  # azul oscuro principal
C_PROC = HexColor('#1565C0')  # azul proceso
C_PBGN = HexColor('#E8EAF6')  # fondo proceso
C_DEC  = HexColor('#E65100')  # naranja decisión
C_DBGN = HexColor('#FFF3E0')
C_REJ  = HexColor('#B71C1C')  # rojo rechazo
C_RBGN = HexColor('#FFEBEE')
C_QUA  = HexColor('#4A148C')  # púrpura calidad
C_QBGN = HexColor('#EDE7F6')
C_ORG  = HexColor('#1B5E20')  # verde orgánica
C_OBGN = HexColor('#E8F5E9')
C_STO  = HexColor('#004D40')  # teal almacenamiento
C_SBGN = HexColor('#E0F2F1')
C_START= HexColor('#2E7D32')  # verde inicio/fin
C_STBG = HexColor('#43A047')
C_GRY  = HexColor('#9E9E9E')
C_LGRY = HexColor('#E0E0E0')
C_TXT  = HexColor('#212121')
C_NOTE = HexColor('#78909C')  # gris azulado para notas

# ======================== DIBUJO ========================

def rr(c, x, y, w, h, r, fc, sc, sw=1):
    c.saveState(); c.setStrokeColor(sc); c.setLineWidth(sw); c.setFillColor(fc)
    c.roundRect(x-w/2, y-h/2, w, h, r, fill=1, stroke=1); c.restoreState()

def dm(c, x, y, w, h, fc, sc):
    c.saveState()
    p = c.beginPath()
    p.moveTo(x,y+h/2); p.lineTo(x+w/2,y); p.lineTo(x,y-h/2); p.lineTo(x-w/2,y); p.close()
    c.setFillColor(fc); c.setStrokeColor(sc); c.setLineWidth(1)
    c.drawPath(p, fill=1, stroke=1); c.restoreState()

def tx(c, x, y, lines, font='Helvetica', sz=8, col=black, bf=False, align='center'):
    lh = sz * 1.35
    sy = y + (len(lines)-1)*lh/2
    for i, ln in enumerate(lines):
        f = 'Helvetica-Bold' if (bf and i==0) or font=='Helvetica-Bold' else font
        c.setFont(f, sz); c.setFillColor(col)
        if align == 'center':
            c.drawCentredString(x, sy - i*lh - sz*0.35, ln)
        else:
            c.drawString(x, sy - i*lh - sz*0.35, ln)

def atip(c, x, y, ang, col, sz=5):
    A = math.pi/7
    c.setFillColor(col)
    p = c.beginPath(); p.moveTo(x,y)
    p.lineTo(x-sz*math.cos(ang-A), y-sz*math.sin(ang-A))
    p.lineTo(x-sz*math.cos(ang+A), y-sz*math.sin(ang+A))
    p.close(); c.drawPath(p, fill=1, stroke=0)

def ar(c, x1, y1, x2, y2, col=C_GRY, lw=1):
    c.saveState(); c.setStrokeColor(col); c.setLineWidth(lw)
    c.line(x1,y1,x2,y2)
    atip(c, x2, y2, math.atan2(y2-y1,x2-x1), col); c.restoreState()

def arl(c, pts, col=C_GRY, lw=1):
    c.saveState(); c.setStrokeColor(col); c.setLineWidth(lw)
    for i in range(len(pts)-1):
        c.line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1])
    x1,y1 = pts[-2]; x2,y2 = pts[-1]
    atip(c, x2, y2, math.atan2(y2-y1,x2-x1), col); c.restoreState()

def lb(c, x, y, text, col=C_DEC, sz=7):
    c.saveState(); c.setFont('Helvetica-Bold', sz)
    tw = c.stringWidth(text, 'Helvetica-Bold', sz)
    c.setFillColor(white); c.rect(x-tw/2-3, y-4, tw+6, sz+6, fill=1, stroke=0)
    c.setFillColor(col); c.drawCentredString(x, y, text); c.restoreState()

def step_badge(c, x, y, n, label=''):
    """Círculo numerado profesional"""
    c.saveState()
    c.setFillColor(C_MAIN); c.circle(x, y, 0.55*cm, fill=1, stroke=0)
    c.setFont('Helvetica-Bold', 11); c.setFillColor(white)
    c.drawCentredString(x, y-3.5, str(n))
    if label:
        c.setFont('Helvetica-Bold', 7.5); c.setFillColor(C_MAIN)
        c.drawString(x+0.75*cm, y-3, label)
    c.restoreState()

def note_box(c, x, y, lines, w=6*cm, h=None, align='left'):
    """Caja de nota lateral discreta"""
    if not h: h = max(0.9*cm, len(lines)*0.28*cm + 0.35*cm)
    c.saveState()
    c.setStrokeColor(C_LGRY); c.setLineWidth(0.5); c.setFillColor(HexColor('#F5F5F5'))
    c.roundRect(x, y-h/2, w, h, 3, fill=1, stroke=1)
    lh = 7*1.3
    sy = y + (len(lines)-1)*lh/2/28.35*cm
    for i, ln in enumerate(lines):
        f = 'Helvetica-Bold' if i==0 else 'Helvetica'
        c.setFont(f, 6.5); c.setFillColor(C_NOTE)
        c.drawString(x+0.2*cm, y + (len(lines)-1)*lh/2/28.35*cm*0.6 - i*lh/28.35*cm - 0.15*cm, ln)
    c.restoreState()
    return h

# ======================== CAJAS PRINCIPALES ========================

BW = 7.5*cm    # ancho caja principal
BH_STD = 1.2*cm

def bx_start(c, x, y, ln, w=BW, h=1.3*cm):
    rr(c,x,y,w,h,h/2, C_STBG, C_START, 1.5)
    tx(c,x,y,ln,'Helvetica-Bold',9,white)
    return h

def bx_proc(c, x, y, ln, w=BW, h=None):
    if not h: h = max(BH_STD, len(ln)*0.32*cm+0.4*cm)
    rr(c,x,y,w,h,4,C_PBGN,C_PROC)
    tx(c,x,y,ln,sz=7.5,col=C_PROC)
    return h

def bx_dec(c, x, y, ln, w=4.5*cm, h=2*cm):
    dm(c,x,y,w,h,C_DBGN,C_DEC)
    tx(c,x,y,ln,sz=7,col=C_DEC,bf=True)
    return h

def bx_rej(c, x, y, ln, w=6*cm, h=None):
    if not h: h = max(BH_STD, len(ln)*0.32*cm+0.4*cm)
    rr(c,x,y,w,h,4,C_RBGN,C_REJ)
    tx(c,x,y,ln,sz=7.5,col=C_REJ,bf=True)
    return h

def bx_qual(c, x, y, ln, w=BW, h=None):
    if not h: h = max(BH_STD, len(ln)*0.32*cm+0.4*cm)
    rr(c,x,y,w,h,4,C_QBGN,C_QUA)
    tx(c,x,y,ln,sz=7.5,col=C_QUA,bf=True)
    return h

def bx_org(c, x, y, ln, w=6*cm, h=None):
    if not h: h = max(BH_STD, len(ln)*0.32*cm+0.4*cm)
    rr(c,x,y,w,h,4,C_OBGN,C_ORG)
    tx(c,x,y,ln,sz=7.5,col=C_ORG,bf=True)
    return h

def bx_sto(c, x, y, ln, w=BW, h=None):
    if not h: h = max(BH_STD, len(ln)*0.32*cm+0.4*cm)
    rr(c,x,y,w,h,4,C_SBGN,C_STO)
    tx(c,x,y,ln,sz=7.5,col=C_STO)
    return h

# ======================== MAIN ========================

def main():
    c = canvas.Canvas(OUTPUT, pagesize=(PW, PH))
    c.setTitle('PRO-RF-0023 Recepción de Materia Prima')

    # Fondo
    c.setFillColor(white)
    c.rect(0, 0, PW, PH, fill=1, stroke=0)

    # ===== ENCABEZADO =====
    header_y = PH - 2*cm
    # Barra superior
    c.setFillColor(C_MAIN)
    c.rect(0, PH-0.4*cm, PW, 0.4*cm, fill=1, stroke=0)
    c.rect(0, PH-0.5*cm, PW, 0.08*cm, fill=0, stroke=0)

    c.setFont('Helvetica-Bold', 20); c.setFillColor(C_MAIN)
    c.drawCentredString(PW/2, header_y, 'RECEPCIÓN DE MATERIA PRIMA')
    c.setFont('Helvetica', 10); c.setFillColor(C_NOTE)
    c.drawCentredString(PW/2, header_y - 0.55*cm, 'PRO-RF-0023  ·  Río Futuro Procesos  ·  Diagrama de Flujo')

    # Línea separadora elegante
    c.setStrokeColor(C_MAIN); c.setLineWidth(1.5)
    c.line(3*cm, header_y - 0.95*cm, PW-3*cm, header_y - 0.95*cm)
    c.setStrokeColor(C_LGRY); c.setLineWidth(0.5)
    c.line(3*cm, header_y - 1.05*cm, PW-3*cm, header_y - 1.05*cm)

    # ===== FLUJO PRINCIPAL: una sola columna centrada =====
    CX = PW / 2       # Centro X del flujo principal
    NX_L = 2*cm       # Notas a la izquierda
    NX_R = CX + BW/2 + 1*cm  # Notas a la derecha
    NW = 6.5*cm        # Ancho notas
    
    TOP = header_y - 2.2*cm
    G = 2.2*cm         # Gap vertical estándar

    y = TOP

    # ──────────────────────────────────────────────────────
    # INICIO
    # ──────────────────────────────────────────────────────
    bx_start(c, CX, y, ['LLEGADA DEL TRANSPORTE A PLANTA'])
    
    # ──────────────────────────────────────────────────────
    # PASO 1: UBICACIÓN DEL TRANSPORTE
    # ──────────────────────────────────────────────────────
    y -= G
    step_badge(c, CX - BW/2 - 1*cm, y, 1)
    bx_proc(c, CX, y, ['Supervisor asigna andén de descarga','Prioridad: camiones con MP orgánica'], BW, 1.1*cm)
    ar(c, CX, y+G-0.65*cm, CX, y+0.55*cm)

    # ──────────────────────────────────────────────────────
    # PASO 2: RECEPCIÓN DE DOCUMENTACIÓN
    # ──────────────────────────────────────────────────────
    y -= G
    step_badge(c, CX - BW/2 - 1*cm, y, 2)
    bx_proc(c, CX, y, ['Chofer entrega Guía de Despacho','al Analista de Calidad',
                        '→ Se entrega al Digitador/Supervisor'], BW, 1.3*cm)
    ar(c, CX, y+G-0.55*cm, CX, y+0.65*cm)

    # Nota derecha: datos obligatorios
    c.saveState()
    nx = NX_R
    nh = 2.8*cm
    c.setStrokeColor(C_LGRY); c.setLineWidth(0.5); c.setFillColor(HexColor('#F5F5F5'))
    c.roundRect(nx, y-nh/2, NW, nh, 3, fill=1, stroke=1)
    lines_n = ['DATOS OBLIGATORIOS GUÍA:', '1) Productor', '2) Nº Bandejas',
               '3) Fecha', '4) Tipo producto', '5) Variedad',
               '6) Calidad MP', '7) Datos chofer (nombre, rut, firma)',
               '8) Patente transporte']
    lh_n = 8.5
    sy_n = y + (len(lines_n)-1)*lh_n/2/28.35*cm
    for i, ln in enumerate(lines_n):
        f = 'Helvetica-Bold' if i==0 else 'Helvetica'
        c.setFont(f, 6.5); c.setFillColor(C_NOTE)
        c.drawString(nx+0.2*cm, sy_n - i*lh_n/28.35*cm - 0.1*cm, ln)
    c.restoreState()
    # Línea punteada de conexión
    c.saveState(); c.setDash(2,2); c.setStrokeColor(C_LGRY); c.setLineWidth(0.5)
    c.line(CX+BW/2, y, nx, y); c.restoreState()

    # ──────────────────────────────────────────────────────
    # Digitador genera orden en Odoo
    # ──────────────────────────────────────────────────────
    y -= G
    bx_proc(c, CX, y, ['Digitador ingresa datos en Odoo','y genera la orden de recepción'], BW, 1.1*cm)
    ar(c, CX, y+G-0.65*cm, CX, y+0.55*cm)

    # ──────────────────────────────────────────────────────
    # PASO 3: DESCARGA DE MATERIA PRIMA
    # ──────────────────────────────────────────────────────
    y -= G
    step_badge(c, CX - BW/2 - 1*cm, y, 3)
    bx_qual(c, CX, y, ['Analista verifica sello transporte vs guía','Inspección visual: limpieza, olores,','plagas, materiales extraños',
                        'Registro: R-RF-0077'], BW, 1.5*cm)
    ar(c, CX, y+G-0.55*cm, CX, y+0.75*cm)

    # ──────────────────────────────────────────────────────
    # Decisión: ¿Condiciones conformes?
    # ──────────────────────────────────────────────────────
    y -= G + 0.2*cm
    DW = 4.5*cm; DH = 1.8*cm
    bx_dec(c, CX, y, ['¿Condiciones','conformes?'], DW, DH)
    ar(c, CX, y+G+0.2*cm-0.75*cm, CX, y+DH/2)

    # Rechazo a la derecha
    rej_x = CX + 5.5*cm
    bx_rej(c, rej_x, y, ['Informar a Jefatura','de Calidad'], 4.5*cm, 1*cm)
    ar(c, CX+DW/2, y, rej_x-4.5*cm/2, y, C_REJ)
    lb(c, CX+DW/2+1*cm, y+0.28*cm, 'No', C_REJ)

    # ──────────────────────────────────────────────────────
    # Autorizar descarga
    # ──────────────────────────────────────────────────────
    y -= G
    bx_proc(c, CX, y, ['Autorizar descarga del camión'], BW, 0.9*cm)
    ar(c, CX, y+G-DH/2, CX, y+0.45*cm)
    lb(c, CX+0.5*cm, y+G-DH/2-0.1*cm, 'Sí', C_START)

    y -= G
    bx_proc(c, CX, y, ['Descarga de pallets con grúa horquilla','o transpaleta manual','MP paletizada + base bandejas vacías + esquineros'], BW, 1.3*cm)
    ar(c, CX, y+G-0.45*cm, CX, y+0.65*cm)

    # ──────────────────────────────────────────────────────
    # PASO 4: PESAJE DE MATERIA PRIMA
    # ──────────────────────────────────────────────────────
    y -= G + 0.1*cm
    step_badge(c, CX - BW/2 - 1*cm, y, 4)
    bx_proc(c, CX, y, ['Verificar calibración de romana','(PRO-RF-0108 Peso patrón)'], BW, 1.1*cm)
    ar(c, CX, y+G+0.1*cm-0.65*cm, CX, y+0.55*cm)

    y -= G
    bx_proc(c, CX, y, ['Pesaje de cada pallet en Odoo:','Peso Bruto − Pallet (~18 kg)','− Peso bandeja = Peso Neto'], BW, 1.3*cm)
    ar(c, CX, y+G-0.55*cm, CX, y+0.65*cm)

    # ──────────────────────────────────────────────────────
    # Decisión: ¿Orgánica o convencional?
    # ──────────────────────────────────────────────────────
    y -= G + 0.2*cm
    bx_dec(c, CX, y, ['¿Es Materia Prima','Orgánica?'], DW, DH)
    ar(c, CX, y+G+0.2*cm-0.65*cm, CX, y+DH/2)

    # Orgánica a la izquierda
    org_x = CX - 5.5*cm
    bx_org(c, org_x, y, ['MP ORGÁNICA','Check List R-RF-0001','Tarja verde · Zona separada'], 5*cm, 1.3*cm)
    ar(c, CX-DW/2, y, org_x+5*cm/2, y, C_ORG)
    lb(c, CX-DW/2-0.7*cm, y+0.28*cm, 'Sí', C_ORG)

    # Convencional a la derecha
    conv_x = CX + 5.5*cm
    bx_proc(c, conv_x, y, ['MP CONVENCIONAL','Proceso estándar'], 4.5*cm, 1*cm)
    ar(c, CX+DW/2, y, conv_x-4.5*cm/2, y, C_PROC)
    lb(c, CX+DW/2+0.7*cm, y+0.28*cm, 'No', C_DEC)

    # Convergencia limpia: ambas bajan al siguiente paso
    y_conv = y  # guardar nivel

    # ──────────────────────────────────────────────────────
    # PASO 5: MUESTREO Y ANÁLISIS DE CALIDAD
    # ──────────────────────────────────────────────────────
    y -= G + 0.3*cm
    step_badge(c, CX - BW/2 - 1*cm, y, 5)
    bx_qual(c, CX, y, ['Muestreo: muestra de 1 kg','de bandejas al azar (representativo)',
                        '2 muestras: laboratorio + contramuestra'], BW, 1.3*cm)
    # Convergencia desde orgánica
    arl(c, [(org_x, y_conv-0.65*cm), (org_x, y+0.65*cm), (CX-0.3*cm, y+0.65*cm)], C_ORG)
    # Convergencia desde convencional
    arl(c, [(conv_x, y_conv-0.5*cm), (conv_x, y+0.65*cm), (CX+0.3*cm, y+0.65*cm)], C_PROC)

    # Nota derecha: tabla de muestreo
    c.saveState()
    nx = NX_R; nh_t = 2.5*cm
    c.setStrokeColor(C_QUA); c.setLineWidth(0.7); c.setFillColor(HexColor('#F3E5F5'))
    c.roundRect(nx, y-nh_t/2, NW, nh_t, 3, fill=1, stroke=1)
    lines_t = ['REGLA DE MUESTREO:','1-2 pallets → 1 análisis',
               '3-5 pallets → 2 análisis','6-8 pallets → 3 análisis',
               '9-12 pallets → 4 análisis','13-15 pallets → 5 análisis',
               '>15 pallets → 6 análisis']
    sy_t = y + (len(lines_t)-1)*lh_n/2/28.35*cm
    for i, ln in enumerate(lines_t):
        f = 'Helvetica-Bold' if i==0 else 'Helvetica'
        c.setFont(f, 6.5); c.setFillColor(C_QUA)
        c.drawString(nx+0.2*cm, sy_t - i*lh_n/28.35*cm - 0.1*cm, ln)
    c.restoreState()
    c.saveState(); c.setDash(2,2); c.setStrokeColor(C_QUA); c.setLineWidth(0.5)
    c.line(CX+BW/2, y, nx, y); c.restoreState()

    # ──────────────────────────────────────────────────────
    # Análisis en laboratorio
    # ──────────────────────────────────────────────────────
    y -= G
    bx_qual(c, CX, y, ['Análisis de Calidad en Laboratorio','Medir temperatura · Pesar defectos',
                        'Calcular % calidad fruta'], BW, 1.3*cm)
    ar(c, CX, y+G-0.65*cm, CX, y+0.65*cm)

    # Nota izquierda: registros por fruta
    c.saveState()
    nx_l = NX_L; nh_r = 2*cm
    c.setStrokeColor(C_QUA); c.setLineWidth(0.7); c.setFillColor(HexColor('#F3E5F5'))
    c.roundRect(nx_l, y-nh_r/2, NW-0.5*cm, nh_r, 3, fill=1, stroke=1)
    lines_r = ['REGISTROS POR FRUTA:','R-RF-0004 Arándano','R-RF-0003 Frambuesa',
               'R-RF-0145 Mora','R-RF-0154 Frutilla']
    sy_r = y + (len(lines_r)-1)*lh_n/2/28.35*cm
    for i, ln in enumerate(lines_r):
        f = 'Helvetica-Bold' if i==0 else 'Helvetica'
        c.setFont(f, 6.5); c.setFillColor(C_QUA)
        c.drawString(nx_l+0.2*cm, sy_r - i*lh_n/28.35*cm - 0.1*cm, ln)
    c.restoreState()
    c.saveState(); c.setDash(2,2); c.setStrokeColor(C_QUA); c.setLineWidth(0.5)
    c.line(CX-BW/2, y, nx_l+NW-0.5*cm, y); c.restoreState()

    # ──────────────────────────────────────────────────────
    # Resultado de calidad
    # ──────────────────────────────────────────────────────
    y -= G + 0.2*cm
    bx_dec(c, CX, y, ['Resultado','de Calidad'], DW, DH)
    ar(c, CX, y+G+0.2*cm-0.65*cm, CX, y+DH/2)

    # IQF a la izquierda
    iqf_x = CX - 5*cm
    rr(c, iqf_x, y, 4.5*cm, 1.2*cm, 4, C_PBGN, C_PROC, 1.3)
    tx(c, iqf_x, y, ['CALIDAD IQF','(70% - 100% fruta apta)'], sz=7.5, col=C_PROC, bf=True)
    ar(c, CX-DW/2, y, iqf_x+4.5*cm/2, y, C_PROC)
    lb(c, CX-DW/2-0.8*cm, y+0.28*cm, 'IQF', C_PROC)

    c.saveState()
    c.setFont('Helvetica', 6.5); c.setFillColor(C_NOTE)
    c.drawCentredString(iqf_x, y-0.8*cm, 'Color homogéneo, fruta firme')
    c.drawCentredString(iqf_x, y-1.1*cm, 'y seca, sin daños físicos')
    c.restoreState()

    # Block a la derecha
    blk_x = CX + 5*cm
    rr(c, blk_x, y, 4.5*cm, 1.2*cm, 4, C_DBGN, C_DEC, 1.3)
    tx(c, blk_x, y, ['CALIDAD BLOCK','(0% - 69% fruta apta)'], sz=7.5, col=C_DEC, bf=True)
    ar(c, CX+DW/2, y, blk_x-4.5*cm/2, y, C_DEC)
    lb(c, CX+DW/2+0.8*cm, y+0.28*cm, 'Block', C_DEC)

    c.saveState()
    c.setFont('Helvetica', 6.5); c.setFillColor(C_NOTE)
    c.drawCentredString(blk_x, y-0.8*cm, 'Sobre madurez, exudación,')
    c.drawCentredString(blk_x, y-1.1*cm, 'gran cantidad fruta dañada')
    c.restoreState()

    y_clasif = y  # guardar nivel

    # ──────────────────────────────────────────────────────
    # PASO 6: REGISTRO E IDENTIFICACIÓN
    # ──────────────────────────────────────────────────────
    y -= G + 0.8*cm
    step_badge(c, CX - BW/2 - 1*cm, y, 6)
    bx_proc(c, CX, y, ['Analista comunica calidad al Digitador','Digitador ingresa en Odoo → Genera Nº Lote','(correlativo: guía + producto + productor + calidad)'], BW, 1.3*cm)
    # Convergencia: IQF baja, Block baja → centro
    arl(c, [(iqf_x, y_clasif-0.6*cm), (iqf_x, y+0.65*cm), (CX-0.3*cm, y+0.65*cm)], C_PROC)
    arl(c, [(blk_x, y_clasif-0.6*cm), (blk_x, y+0.65*cm), (CX+0.3*cm, y+0.65*cm)], C_DEC)

    # Nota derecha: datos del lote
    c.saveState()
    nx = NX_R; nh_l = 2*cm
    c.setStrokeColor(C_LGRY); c.setLineWidth(0.5); c.setFillColor(HexColor('#F5F5F5'))
    c.roundRect(nx, y-nh_l/2, NW, nh_l, 3, fill=1, stroke=1)
    lines_l = ['LOTE REGISTRA EN ODOO:','Fecha, hora, productor, tipo envase',
               'Variedad, calidad, Nº bandejas','Tipo pallet, guía de despacho']
    sy_l = y + (len(lines_l)-1)*lh_n/2/28.35*cm
    for i, ln in enumerate(lines_l):
        f = 'Helvetica-Bold' if i==0 else 'Helvetica'
        c.setFont(f, 6.5); c.setFillColor(C_NOTE)
        c.drawString(nx+0.2*cm, sy_l - i*lh_n/28.35*cm - 0.1*cm, ln)
    c.restoreState()
    c.saveState(); c.setDash(2,2); c.setStrokeColor(C_LGRY); c.setLineWidth(0.5)
    c.line(CX+BW/2, y, nx, y); c.restoreState()

    # ──────────────────────────────────────────────────────
    # Generar etiqueta
    # ──────────────────────────────────────────────────────
    y -= G
    bx_proc(c, CX, y, ['Generar etiqueta por pallet','con datos de recepción'], BW, 1.1*cm)
    ar(c, CX, y+G-0.65*cm, CX, y+0.55*cm)

    # Nota derecha: datos etiqueta
    c.saveState()
    nx = NX_R; nh_e = 3.2*cm
    c.setStrokeColor(C_LGRY); c.setLineWidth(0.5); c.setFillColor(HexColor('#F5F5F5'))
    c.roundRect(nx, y-nh_e/2, NW, nh_e, 3, fill=1, stroke=1)
    lines_e = ['DATOS ETIQUETA:','Nº Pallet · Nombre productor',
               'Código producto · Nombre producto','Fecha recepción · Nº Lote',
               'Peso pallet · Nº Bandejas',
               'Quién hizo el registro (Odoo)','Código de Barra']
    sy_e = y + (len(lines_e)-1)*lh_n/2/28.35*cm
    for i, ln in enumerate(lines_e):
        f = 'Helvetica-Bold' if i==0 else 'Helvetica'
        c.setFont(f, 6.5); c.setFillColor(C_NOTE)
        c.drawString(nx+0.2*cm, sy_e - i*lh_n/28.35*cm - 0.1*cm, ln)
    c.restoreState()
    c.saveState(); c.setDash(2,2); c.setStrokeColor(C_LGRY); c.setLineWidth(0.5)
    c.line(CX+BW/2, y, nx, y); c.restoreState()

    # ──────────────────────────────────────────────────────
    # PASO 7: TRASLADO Y ALMACENAMIENTO
    # ──────────────────────────────────────────────────────
    y -= G
    step_badge(c, CX - BW/2 - 1*cm, y, 7)
    bx_sto(c, CX, y, ['Traslado a Cámaras 0°C','(Cámara 8 y Cámara 9)'], BW, 1.1*cm)
    ar(c, CX, y+G-0.55*cm, CX, y+0.55*cm)

    y -= G
    bx_sto(c, CX, y, ['Almacenamiento en fila según lote','Acceso restringido'], BW, 1.1*cm)
    ar(c, CX, y+G-0.55*cm, CX, y+0.55*cm)

    # ──────────────────────────────────────────────────────
    # FIN
    # ──────────────────────────────────────────────────────
    y -= G
    bx_start(c, CX, y, ['RECEPCIÓN COMPLETADA','Registro finalizado en Odoo'])
    ar(c, CX, y+G-0.55*cm, CX, y+0.65*cm)

    # ──────────────────────────────────────────────────────
    # SECCIÓN RECHAZO (al costado izquierdo, nivel inferior)
    # ──────────────────────────────────────────────────────
    # Rechazo desde el resultado de calidad
    y_rej_start = y_clasif - DH/2
    rej_cx = 5.5*cm
    rej_y = y_clasif - G - 0.5*cm

    # Línea desde decisión hacia abajo-izquierda
    arl(c, [(CX, y_clasif - DH/2), (CX, y_clasif - DH/2 - 0.5*cm), 
            (rej_cx, y_clasif - DH/2 - 0.5*cm), (rej_cx, rej_y + 0.65*cm)], C_REJ)
    lb(c, CX - 2*cm, y_clasif - DH/2 - 0.3*cm, 'Rechazada', C_REJ)

    bx_rej(c, rej_cx, rej_y, ['RECHAZADA','Informar al productor','(Gerente Agrícola si es grande)'], 5.5*cm, 1.3*cm)

    rej_y -= G
    bx_rej(c, rej_cx, rej_y, ['Devolución con Guía de Despacho','+ Guía RF al huerto de origen','R-RF-0216 Producto No Conforme',
                               'Análisis calidad + fotos archivadas'], 5.5*cm, 1.5*cm)
    ar(c, rej_cx, rej_y+G-0.65*cm, rej_cx, rej_y+0.75*cm, C_REJ)

    # Nota: motivos rechazo
    c.saveState()
    nmx = rej_cx + 5.5*cm/2 + 0.5*cm; nmh = 2*cm
    c.setStrokeColor(C_REJ); c.setLineWidth(0.5); c.setFillColor(C_RBGN)
    c.roundRect(nmx, rej_y-nmh/2, NW-0.5*cm, nmh, 3, fill=1, stroke=1)
    lines_m = ['MOTIVOS DE RECHAZO:','• Hongos >30% de la muestra',
               '• Deficiencia/volcamiento de estiva','• Sin certif. lobesia botrana (arándano)',
               '• Orgánico sin certificado vigente']
    sy_m = rej_y + (len(lines_m)-1)*lh_n/2/28.35*cm
    for i, ln in enumerate(lines_m):
        f = 'Helvetica-Bold' if i==0 else 'Helvetica'
        c.setFont(f, 6.5); c.setFillColor(C_REJ)
        c.drawString(nmx+0.2*cm, sy_m - i*lh_n/28.35*cm - 0.1*cm, ln)
    c.restoreState()
    c.saveState(); c.setDash(2,2); c.setStrokeColor(C_REJ); c.setLineWidth(0.5)
    c.line(rej_cx+5.5*cm/2, rej_y, nmx, rej_y); c.restoreState()

    # ================================================================
    # LEYENDA
    # ================================================================
    leg_y = 2.2*cm
    c.setStrokeColor(C_LGRY); c.setLineWidth(0.5)
    c.line(3*cm, leg_y+0.8*cm, PW-3*cm, leg_y+0.8*cm)
    
    c.setFont('Helvetica-Bold', 9); c.setFillColor(C_MAIN)
    c.drawString(3*cm, leg_y+0.3*cm, 'LEYENDA')
    
    items = [
        (C_STBG, C_START, 'Inicio / Fin'),
        (C_PBGN, C_PROC, 'Proceso'),
        (C_DBGN, C_DEC, 'Decisión'),
        (C_RBGN, C_REJ, 'Rechazo'),
        (C_QBGN, C_QUA, 'Calidad / Muestreo'),
        (C_OBGN, C_ORG, 'MP Orgánica'),
        (C_SBGN, C_STO, 'Almacenamiento'),
    ]
    for i,(fc,sc,l) in enumerate(items):
        lx = 3*cm + i*5.2*cm
        rr(c, lx+0.3*cm, leg_y-0.2*cm, 0.6*cm, 0.35*cm, 3, fc, sc, 0.8)
        c.setFont('Helvetica', 7); c.setFillColor(C_TXT)
        c.drawString(lx+0.75*cm, leg_y-0.3*cm, l)

    # Documentos asociados
    c.setFont('Helvetica', 6); c.setFillColor(C_NOTE)
    c.drawString(3*cm, leg_y-0.85*cm,
        'Documentos: R-RF-0077 Control Transporte · R-RF-0001 Check List Orgánica · R-RF-0216 Prod. No Conforme · PRO-RF-0108 Calibración')

    # Pie de página
    c.setStrokeColor(C_MAIN); c.setLineWidth(0.8)
    c.line(0, 0.5*cm, PW, 0.5*cm)
    c.setFont('Helvetica', 6.5); c.setFillColor(C_NOTE)
    c.drawCentredString(PW/2, 0.15*cm, 'Río Futuro Procesos  ·  PRO-RF-0023  ·  Versión 2 (20-01-2026)')

    c.save()
    sz = os.path.getsize(OUTPUT)/1024
    print(f"✅ PDF generado: {OUTPUT}")
    print(f"   Tamaño: {sz:.0f} KB  ·  Formato: {PW/cm:.0f} × {PH/cm:.0f} cm")


if __name__ == '__main__':
    main()
