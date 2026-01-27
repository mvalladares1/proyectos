"""Actualizar menú Logs para que aparezca en la raíz"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

print("\n=== ACTUALIZANDO MENÚ LOGS ===\n")

# Actualizar el menú 993 para que sea raíz y se llame "Trasferencias Dashboard"
odoo.execute("ir.ui.menu", "write", [993], {
    "name": "Trasferencias Dashboard",
    "parent_id": False,
    "sequence": 100
})

print("✓ Menú actualizado:")
print("  - Nombre: Trasferencias Dashboard")
print("  - Ubicación: Menú raíz (sin padre)")
print("  - ID: 993")
print("\n⚠️  IMPORTANTE: Refresca el navegador con Ctrl+F5")
print("   Busca el ícono 'Trasferencias Dashboard' en la pantalla principal")
