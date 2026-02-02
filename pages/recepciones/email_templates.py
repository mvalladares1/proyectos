"""
Templates de correo estandarizados para Río Futuro
Incluye templates para proformas de fletes y otros documentos
"""

from datetime import datetime
from typing import Dict


def formato_numero_chileno(numero: float, decimales: int = 0) -> str:
    """Formatea número con separador de miles chileno (punto) y decimal (coma)"""
    if decimales == 0:
        formato = f"{numero:,.0f}"
    else:
        formato = f"{numero:,.{decimales}f}"
    # Reemplazar separadores: coma por punto (miles) y punto por coma (decimal)
    return formato.replace(',', 'X').replace('.', ',').replace('X', '.')


def get_proforma_email_template(
    transportista: str,
    fecha_desde: str,
    fecha_hasta: str,
    cant_ocs: int,
    total_kms: float,
    total_kilos: float,
    total_costo: float,
    email_remitente: str = "finanzas@riofuturo.cl",
    telefono_contacto: str = "+56 2 2345 6789"
) -> Dict[str, str]:
    """
    Genera el template de correo para envío de proforma de fletes
    
    Returns:
        Dict con 'subject' y 'body_html'
    """
    
    subject = f"Proforma Consolidada de Fletes - {fecha_desde} al {fecha_hasta}"
    
    body_html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Proforma de Fletes</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f5f5f5;
            }}
            .email-container {{
                max-width: 650px;
                margin: 0 auto;
                background-color: #ffffff;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #1f4788 0%, #2c5aa0 100%);
                color: white;
                padding: 30px 20px;
                text-align: center;
            }}
            .header h1 {{
                font-size: 24px;
                margin: 0;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
            .header .subtitle {{
                font-size: 14px;
                margin-top: 8px;
                opacity: 0.95;
            }}
            .content {{
                padding: 30px 25px;
            }}
            .greeting {{
                font-size: 16px;
                margin-bottom: 20px;
                color: #2c5aa0;
                font-weight: 500;
            }}
            .message {{
                font-size: 15px;
                margin-bottom: 15px;
                color: #444;
            }}
            .summary-box {{
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                border-left: 4px solid #4a90e2;
                padding: 20px;
                margin: 25px 0;
                border-radius: 5px;
            }}
            .summary-box h2 {{
                color: #1f4788;
                font-size: 18px;
                margin-bottom: 15px;
                font-weight: 600;
            }}
            .summary-item {{
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #dee2e6;
            }}
            .summary-item:last-child {{
                border-bottom: none;
            }}
            .summary-label {{
                color: #666;
                font-weight: 500;
            }}
            .summary-value {{
                color: #1f4788;
                font-weight: 600;
                text-align: right;
            }}
            .total-box {{
                background-color: #1f4788;
                color: white;
                padding: 15px;
                border-radius: 5px;
                margin-top: 10px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .total-label {{
                font-size: 16px;
                font-weight: 600;
            }}
            .total-value {{
                font-size: 22px;
                font-weight: 700;
            }}
            .attachment-notice {{
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                color: #856404;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
                font-size: 14px;
            }}
            .attachment-notice strong {{
                display: block;
                margin-bottom: 5px;
            }}
            .contact-info {{
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 5px;
                margin: 20px 0;
                font-size: 14px;
            }}
            .contact-info h3 {{
                color: #1f4788;
                font-size: 16px;
                margin-bottom: 10px;
            }}
            .contact-item {{
                margin: 8px 0;
                color: #555;
            }}
            .contact-item strong {{
                color: #1f4788;
            }}
            .signature {{
                margin: 25px 0;
                color: #444;
            }}
            .signature strong {{
                color: #1f4788;
                font-size: 16px;
            }}
            .footer {{
                background-color: #2c3e50;
                color: #ecf0f1;
                padding: 25px 20px;
                text-align: center;
                font-size: 12px;
                line-height: 1.8;
            }}
            .footer .company-name {{
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 10px;
                color: #fff;
            }}
            .footer .timestamp {{
                margin-top: 15px;
                opacity: 0.8;
                font-size: 11px;
            }}
            .footer .legal {{
                margin-top: 10px;
                opacity: 0.7;
                font-size: 11px;
            }}
            @media only screen and (max-width: 600px) {{
                .content {{
                    padding: 20px 15px;
                }}
                .summary-item {{
                    flex-direction: column;
                }}
                .summary-value {{
                    text-align: left;
                    margin-top: 5px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <!-- Header -->
            <div class="header">
                <h1>🚛 Proforma Consolidada de Fletes</h1>
                <div class="subtitle">Período: {fecha_desde} al {fecha_hasta}</div>
            </div>
            
            <!-- Content -->
            <div class="content">
                <div class="greeting">
                    Estimado/a {transportista},
                </div>
                
                <p class="message">
                    Por medio del presente, adjuntamos la <strong>proforma consolidada</strong> de los servicios de 
                    flete prestados durante el período comprendido entre el <strong>{fecha_desde}</strong> y el 
                    <strong>{fecha_hasta}</strong>.
                </p>
                
                <!-- Summary Box -->
                <div class="summary-box">
                    <h2>📊 Resumen del Período</h2>
                    
                    <div class="summary-item">
                        <span class="summary-label">📋 Órdenes de Compra Procesadas:</span>
                        <span class="summary-value">{cant_ocs} OC{'' if cant_ocs == 1 else 's'}</span>
                    </div>
                    
                    <div class="summary-item">
                        <span class="summary-label">🛣️ Kilómetros Totales Recorridos:</span>
                        <span class="summary-value">{formato_numero_chileno(total_kms, 0)} km</span>
                    </div>
                    
                    <div class="summary-item">
                        <span class="summary-label">⚖️ Carga Total Transportada:</span>
                        <span class="summary-value">{formato_numero_chileno(total_kilos, 1)} kg</span>
                    </div>
                    
                    <div class="summary-item">
                        <span class="summary-label">💵 Costo Promedio por Kilómetro:</span>
                        <span class="summary-value">${formato_numero_chileno(total_costo / total_kms, 0)}/km</span>
                    </div>
                    
                    <!-- Total destacado -->
                    <div class="total-box">
                        <span class="total-label">MONTO TOTAL:</span>
                        <span class="total-value">${formato_numero_chileno(total_costo, 0)}</span>
                    </div>
                </div>
                
                <!-- Attachment Notice -->
                <div class="attachment-notice">
                    <strong>📎 Documento Adjunto</strong>
                    En el archivo PDF adjunto encontrará el detalle completo de todas las órdenes de compra, 
                    rutas, kilómetros, costos y tipo de vehículo utilizado en cada servicio.
                </div>
                
                <p class="message">
                    El documento adjunto contiene información detallada de cada operación, incluyendo:
                </p>
                <ul style="margin-left: 25px; margin-bottom: 20px; color: #555;">
                    <li>Número de Orden de Compra (OC)</li>
                    <li>Fecha de servicio</li>
                    <li>Ruta realizada</li>
                    <li>Kilómetros y carga transportada</li>
                    <li>Tipo de vehículo utilizado</li>
                    <li>Costo por kilómetro y total por servicio</li>
                </ul>
                
                <!-- Contact Info -->
                <div class="contact-info">
                    <h3>📞 Información de Contacto</h3>
                    <div class="contact-item">
                        <strong>Email:</strong> {email_remitente}
                    </div>
                    <div class="contact-item">
                        <strong>Teléfono:</strong> {telefono_contacto}
                    </div>
                    <div class="contact-item">
                        Para cualquier consulta o aclaración respecto a esta proforma, 
                        no dude en contactarnos a través de los medios indicados.
                    </div>
                </div>
                
                <p class="message">
                    Agradecemos la confianza depositada en nuestros servicios y quedamos atentos 
                    a cualquier consulta que pueda tener.
                </p>
                
                <!-- Signature -->
                <div class="signature">
                    <p>Saludos cordiales,</p>
                    <p><strong>Equipo de Gestión</strong></p>
                    <p><strong>Río Futuro</strong></p>
                </div>
            </div>
            
            <!-- Footer -->
            <div class="footer">
                <div class="company-name">RÍO FUTURO</div>
                <div>Sistema de Gestión Automatizado</div>
                <div class="timestamp">
                    📅 Documento generado automáticamente el {datetime.now().strftime('%d/%m/%Y a las %H:%M')} hrs
                </div>
                <div class="legal">
                    Este es un correo automático. Por favor, no responda directamente a este mensaje.
                    <br>Para consultas, utilice los datos de contacto proporcionados en el cuerpo del correo.
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return {
        'subject': subject,
        'body_html': body_html
    }


def get_proforma_email_template_simple(
    transportista: str,
    fecha_desde: str,
    fecha_hasta: str,
    cant_ocs: int,
    total_kms: float,
    total_kilos: float,
    total_costo: float
) -> Dict[str, str]:
    """
    Template simple (versión actual) para compatibilidad
    """
    subject = f'Proforma Consolidada de Fletes - {fecha_desde} al {fecha_hasta}'
    
    body_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ background-color: #1f4788; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .summary {{ background-color: #f0f0f0; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            .footer {{ text-align: center; color: #666; padding: 20px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Proforma Consolidada de Fletes</h2>
        </div>
        <div class="content">
            <p>Estimado/a,</p>
            <p>Adjuntamos la proforma consolidada de servicios de flete correspondiente al período <strong>{fecha_desde}</strong> al <strong>{fecha_hasta}</strong>.</p>
            
            <div class="summary">
                <h3>Resumen del Período</h3>
                <ul>
                    <li><strong>Cantidad de Órdenes de Compra:</strong> {cant_ocs}</li>
                    <li><strong>Total Kilómetros:</strong> {formato_numero_chileno(total_kms, 0)} km</li>
                    <li><strong>Total Kilos:</strong> {formato_numero_chileno(total_kilos, 1)} kg</li>
                    <li><strong>Monto Total:</strong> ${formato_numero_chileno(total_costo, 0)}</li>
                </ul>
            </div>
            
            <p>En el documento adjunto encontrará el detalle completo de todas las órdenes de compra incluidas en este período.</p>
            
            <p>Cualquier consulta, no dude en contactarnos.</p>
            
            <p>Saludos cordiales,<br>
            <strong>Río Futuro</strong></p>
        </div>
        <div class="footer">
            Este es un correo automático generado por el sistema de gestión de Río Futuro.<br>
            Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}
        </div>
    </body>
    </html>
    """
    
    return {
        'subject': subject,
        'body_html': body_html
    }
