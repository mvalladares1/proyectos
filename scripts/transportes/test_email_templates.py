"""
Script para probar y comparar los templates de email de proformas
Genera versiones del template actual y mejorado para comparación
"""

import sys
sys.path.insert(0, r'c:\new\RIO FUTURO\DASHBOARD\proyectos\pages\recepciones')

from email_templates import get_proforma_email_template, get_proforma_email_template_simple
from datetime import datetime

# Datos de prueba
transportista = "TRANSPORTES RODRIGUEZ LIMITADA"
fecha_desde = "2026-01-01"
fecha_hasta = "2026-01-31"
cant_ocs = 3
total_kms = 1380.0
total_kilos = 39500.0
total_costo = 690000.0

print("=" * 80)
print("COMPARACIÓN DE TEMPLATES DE EMAIL - PROFORMA DE FLETES")
print("=" * 80)

# Template Simple (Actual)
print("\n1. Generando template ACTUAL (simple)...")
template_simple = get_proforma_email_template_simple(
    transportista, fecha_desde, fecha_hasta,
    cant_ocs, total_kms, total_kilos, total_costo
)

filename_simple = f'proforma_email_ACTUAL_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
with open(filename_simple, 'w', encoding='utf-8') as f:
    f.write(template_simple['body_html'])

print(f"   ✅ Generado: {filename_simple}")
print(f"   📧 Asunto: {template_simple['subject']}")
print(f"   📊 Tamaño: {len(template_simple['body_html']):,} caracteres")

# Template Mejorado
print("\n2. Generando template MEJORADO (nuevo)...")
template_mejorado = get_proforma_email_template(
    transportista, fecha_desde, fecha_hasta,
    cant_ocs, total_kms, total_kilos, total_costo,
    email_remitente="finanzas@riofuturo.cl",
    telefono_contacto="+56 2 2345 6789"
)

filename_mejorado = f'proforma_email_MEJORADO_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
with open(filename_mejorado, 'w', encoding='utf-8') as f:
    f.write(template_mejorado['body_html'])

print(f"   ✅ Generado: {filename_mejorado}")
print(f"   📧 Asunto: {template_mejorado['subject']}")
print(f"   📊 Tamaño: {len(template_mejorado['body_html']):,} caracteres")

# Comparación
print("\n" + "=" * 80)
print("COMPARACIÓN DE CARACTERÍSTICAS")
print("=" * 80)

print("\n📋 TEMPLATE ACTUAL:")
print("   • Diseño simple con colores básicos")
print("   • Header azul plano")
print("   • Resumen en lista <ul>")
print("   • Footer básico con timestamp")
print("   • Sin información de contacto detallada")
print("   • Sin diseño responsive")

print("\n✨ TEMPLATE MEJORADO:")
print("   • Diseño profesional con gradientes")
print("   • Header con gradiente azul corporativo")
print("   • Resumen en tabla visual con items destacados")
print("   • Total destacado en caja especial")
print("   • Aviso de adjunto destacado en amarillo")
print("   • Información de contacto completa (email + teléfono)")
print("   • Lista detallada de contenido del PDF")
print("   • Footer corporativo completo")
print("   • Diseño responsive para móviles")
print("   • Mejor jerarquía visual")
print("   • Iconos emoji para mejor UX")

print("\n" + "=" * 80)
print("DATOS DEL CORREO DE PRUEBA")
print("=" * 80)
print(f"Para: {transportista}")
print(f"Período: {fecha_desde} al {fecha_hasta}")
print(f"OCs: {cant_ocs}")
print(f"Kilómetros: {total_kms:,.0f} km")
print(f"Carga: {total_kilos:,.1f} kg")
print(f"Total: ${total_costo:,.0f}")
print(f"Costo/km: ${total_costo/total_kms:,.0f}/km")

print("\n✅ Archivos generados exitosamente!")
print("\n💡 RECOMENDACIÓN:")
print("   Abre ambos archivos HTML en tu navegador para comparar visualmente")
print("   y decide cuál implementar en el sistema de producción.")

# Generar archivo de comparación lado a lado
html_comparacion = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Comparación de Templates</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            color: #1f4788;
        }}
        .comparison {{
            display: flex;
            gap: 20px;
            margin-top: 30px;
        }}
        .column {{
            flex: 1;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .column h2 {{
            text-align: center;
            padding: 15px;
            border-radius: 5px;
            color: white;
        }}
        .actual h2 {{
            background-color: #6c757d;
        }}
        .mejorado h2 {{
            background-color: #28a745;
        }}
        iframe {{
            width: 100%;
            height: 800px;
            border: 1px solid #ddd;
            border-radius: 5px;
            background: white;
        }}
        .stats {{
            background: #f8f9fa;
            padding: 15px;
            margin-top: 15px;
            border-radius: 5px;
        }}
        .stats h3 {{
            margin-top: 0;
            color: #1f4788;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Comparación de Templates de Email - Proforma de Fletes</h1>
        
        <div class="comparison">
            <div class="column actual">
                <h2>📄 Template ACTUAL</h2>
                <iframe src="{filename_simple}"></iframe>
                <div class="stats">
                    <h3>Características</h3>
                    <ul>
                        <li>Diseño simple</li>
                        <li>Header básico</li>
                        <li>Sin diseño responsive</li>
                        <li>Información mínima</li>
                    </ul>
                </div>
            </div>
            
            <div class="column mejorado">
                <h2>✨ Template MEJORADO</h2>
                <iframe src="{filename_mejorado}"></iframe>
                <div class="stats">
                    <h3>Mejoras Implementadas</h3>
                    <ul>
                        <li>✅ Diseño profesional con gradientes</li>
                        <li>✅ Total destacado visualmente</li>
                        <li>✅ Información de contacto completa</li>
                        <li>✅ Diseño responsive para móviles</li>
                        <li>✅ Aviso de adjunto destacado</li>
                        <li>✅ Lista detallada de contenido</li>
                        <li>✅ Footer corporativo completo</li>
                        <li>✅ Mejor jerarquía visual</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

filename_comparacion = f'COMPARACION_templates_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
with open(filename_comparacion, 'w', encoding='utf-8') as f:
    f.write(html_comparacion)

print(f"\n📊 Archivo de comparación generado: {filename_comparacion}")
print("   Abre este archivo para ver ambos templates lado a lado")
