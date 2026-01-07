"""
Script de Trazabilidad Completa en Odoo
Rastreo desde Pallet de Venta hasta Productor Original

Uso:
    python trazabilidad_completa.py --pallet "PALLET-RF-2024-0156"
    python trazabilidad_completa.py --lote "LOTE-PT-2024-0892"
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime

# Agregar el path del backend para imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.odoo_client import OdooClient


class TrazabilidadCompleta:
    """Clase para rastrear trazabilidad completa desde PT hasta MP."""
    
    def __init__(self, username: str, password: str):
        self.odoo = OdooClient(username=username, password=password)
        self.lotes_procesados = set()
        self.cadena = []
    
    # ========================================
    # FUNCIONES PRINCIPALES
    # ========================================
    
    def rastrear_desde_pallet(self, pallet_name: str) -> Dict:
        """
        Rastrea trazabilidad desde un pallet físico.
        
        Args:
            pallet_name: Nombre del pallet (ej: "PALLET-RF-2024-0156")
        
        Returns:
            Dict con toda la cadena de trazabilidad
        """
        print(f"\n🔍 Buscando pallet: {pallet_name}")
        
        # 1. Buscar el pallet en stock.quant.package
        pallet = self.odoo.search_read(
            'stock.quant.package',
            [['name', '=', pallet_name]],
            ['id', 'name', 'location_id'],
            limit=1
        )
        
        if not pallet:
            return {'error': f'Pallet {pallet_name} no encontrado'}
        
        pallet_id = pallet[0]['id']
        print(f"✅ Pallet encontrado: ID {pallet_id}")
        
        # 2. Buscar los lotes dentro del pallet
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['result_package_id', '=', pallet_id]],
            ['id', 'lot_id', 'product_id', 'qty_done', 'picking_id', 'date'],
            order='date desc',
            limit=10
        )
        
        if not move_lines:
            return {'error': f'No se encontraron movimientos para pallet {pallet_name}'}
        
        # Tomar el lote más reciente (puede haber varios)
        lote_pt = move_lines[0].get('lot_id')
        if not lote_pt:
            return {'error': 'El pallet no tiene lote asignado'}
        
        lote_pt_id = lote_pt[0]
        lote_pt_name = lote_pt[1]
        
        print(f"📦 Lote PT encontrado: {lote_pt_name} (ID: {lote_pt_id})")
        
        # 3. Rastrear desde el lote PT
        return self.rastrear_desde_lote(lote_pt_id, pallet_name=pallet_name)
    
    def rastrear_desde_lote(self, lote_id: int, lote_name: str = None, 
                            pallet_name: str = None) -> Dict:
        """
        Rastrea trazabilidad desde un lote PT.
        
        Args:
            lote_id: ID del lote de producto terminado
            lote_name: Nombre del lote (opcional)
            pallet_name: Nombre del pallet (opcional)
        
        Returns:
            Dict con toda la cadena de trazabilidad
        """
        # Obtener info del lote si no se proveyó
        if not lote_name:
            lote = self.odoo.search_read(
                'stock.lot',
                [['id', '=', lote_id]],
                ['id', 'name', 'product_id', 'create_date'],
                limit=1
            )
            if not lote:
                return {'error': f'Lote {lote_id} no encontrado'}
            lote_name = lote[0]['name']
        
        print(f"\n🔍 Iniciando trazabilidad para lote: {lote_name}")
        
        # Resetear estado
        self.lotes_procesados = set()
        self.cadena = []
        
        # Rastrear recursivamente
        self._rastrear_lote_recursivo(lote_id, nivel=0)
        
        # Construir resultado
        return {
            'pallet': pallet_name,
            'lote_pt': lote_name,
            'fecha_consulta': datetime.now().isoformat(),
            'cadena_produccion': self.cadena,
            'total_niveles': len(self.cadena),
            'productor': self._extraer_productor(),
            'resumen': self._generar_resumen()
        }
    
    # ========================================
    # FUNCIONES RECURSIVAS
    # ========================================
    
    def _rastrear_lote_recursivo(self, lot_id: int, nivel: int = 0):
        """Rastrea recursivamente un lote hasta encontrar el origen."""
        
        # Evitar loops infinitos
        if lot_id in self.lotes_procesados:
            print(f"  ⚠️  Lote {lot_id} ya procesado (evitando loop)")
            return
        
        self.lotes_procesados.add(lot_id)
        indent = "  " * nivel
        
        # 1. Obtener info del lote
        lote_info = self._get_lote_info(lot_id)
        if not lote_info:
            print(f"{indent}❌ No se pudo obtener info del lote {lot_id}")
            return
        
        print(f"{indent}📍 Nivel {nivel}: {lote_info['name']}")
        
        # 2. Buscar la MO que produjo este lote
        mo_info = self._get_mo_from_lot(lot_id)
        
        if not mo_info:
            # Es un lote de MP (no fue producido, fue comprado)
            print(f"{indent}🌾 MATERIA PRIMA encontrada")
            productor_info = self._get_productor_from_lot(lot_id)
            
            self.cadena.append({
                'nivel': nivel,
                'tipo': 'MATERIA_PRIMA',
                'lot_id': lot_id,
                'lot_name': lote_info['name'],
                'product_name': lote_info['product_name'],
                'fecha': lote_info['create_date'],
                'productor': productor_info
            })
            return
        
        # 3. Es un producto intermedio o final
        print(f"{indent}🏭 MO: {mo_info['name']} - {mo_info.get('sala', 'N/A')}")
        
        self.cadena.append({
            'nivel': nivel,
            'tipo': 'PROCESO',
            'lot_id': lot_id,
            'lot_name': lote_info['name'],
            'product_name': lote_info['product_name'],
            'fecha': lote_info['create_date'],
            'mo_id': mo_info['id'],
            'mo_name': mo_info['name'],
            'sala': mo_info.get('sala', 'N/A'),
            'fecha_mo': mo_info.get('fecha', '')
        })
        
        # 4. Obtener consumos de la MO
        consumos = self._get_consumos_mo(mo_info['id'])
        
        if not consumos:
            print(f"{indent}  ⚠️  No se encontraron consumos")
            return
        
        print(f"{indent}  → {len(consumos)} lote(s) consumido(s)")
        
        # 5. Rastrear cada lote consumido (recursión)
        for consumo in consumos:
            lot_consumido_id = consumo['lot_id']
            qty = consumo['qty_done']
            print(f"{indent}    • {consumo['lot_name']}: {qty} kg")
            
            # Agregar info de consumo al registro actual
            if 'consumos' not in self.cadena[-1]:
                self.cadena[-1]['consumos'] = []
            
            self.cadena[-1]['consumos'].append({
                'lot_id': lot_consumido_id,
                'lot_name': consumo['lot_name'],
                'product_name': consumo['product_name'],
                'qty_done': qty
            })
            
            # Recursión
            self._rastrear_lote_recursivo(lot_consumido_id, nivel + 1)
    
    # ========================================
    # FUNCIONES DE CONSULTA ODOO
    # ========================================
    
    def _get_lote_info(self, lot_id: int) -> Optional[Dict]:
        """Obtiene información de un lote."""
        lotes = self.odoo.search_read(
            'stock.lot',
            [['id', '=', lot_id]],
            ['id', 'name', 'product_id', 'create_date'],
            limit=1
        )
        
        if not lotes:
            return None
        
        lote = lotes[0]
        product_info = lote.get('product_id')
        
        return {
            'id': lote['id'],
            'name': lote['name'],
            'product_name': product_info[1] if product_info else 'N/A',
            'create_date': str(lote.get('create_date', ''))[:19]
        }
    
    def _get_mo_from_lot(self, lot_id: int) -> Optional[Dict]:
        """
        Obtiene la MO que produjo un lote.
        Retorna None si el lote no fue producido (es MP).
        """
        # Buscar primer movimiento del lote (creación)
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['lot_id', '=', lot_id]],
            ['id', 'move_id', 'date', 'location_id'],
            order='date asc',
            limit=1
        )
        
        if not move_lines:
            return None
        
        move_id = move_lines[0]['move_id'][0]
        
        # Obtener el stock.move
        moves = self.odoo.search_read(
            'stock.move',
            [['id', '=', move_id]],
            ['id', 'production_id', 'raw_material_production_id']
        )
        
        if not moves:
            return None
        
        move = moves[0]
        
        # El lote fue producido por esta MO
        mo_ref = move.get('production_id')
        
        if not mo_ref:
            # No fue producido, es MP
            return None
        
        mo_id = mo_ref[0]
        
        # Obtener detalles de la MO
        mos = self.odoo.search_read(
            'mrp.production',
            [['id', '=', mo_id]],
            ['id', 'name', 'move_raw_ids', 'date_planned_start', 
             'x_studio_sala_de_proceso'],
            limit=1
        )
        
        if not mos:
            return None
        
        mo = mos[0]
        
        return {
            'id': mo['id'],
            'name': mo['name'],
            'move_raw_ids': mo.get('move_raw_ids', []),
            'sala': mo.get('x_studio_sala_de_proceso', ''),
            'fecha': str(mo.get('date_planned_start', ''))[:19]
        }
    
    def _get_consumos_mo(self, mo_id: int) -> List[Dict]:
        """Obtiene todos los lotes consumidos por una MO."""
        
        # Obtener move_raw_ids de la MO
        mos = self.odoo.search_read(
            'mrp.production',
            [['id', '=', mo_id]],
            ['move_raw_ids'],
            limit=1
        )
        
        if not mos or not mos[0].get('move_raw_ids'):
            return []
        
        move_raw_ids = mos[0]['move_raw_ids']
        
        # Obtener stock.move.line de los consumos
        consumos = self.odoo.search_read(
            'stock.move.line',
            [
                ['move_id', 'in', move_raw_ids],
                ['lot_id', '!=', False]  # Solo los que tienen lote
            ],
            ['id', 'product_id', 'lot_id', 'qty_done']
        )
        
        # Formatear resultado
        result = []
        for c in consumos:
            lot_info = c.get('lot_id')
            product_info = c.get('product_id')
            
            if lot_info:
                result.append({
                    'lot_id': lot_info[0],
                    'lot_name': lot_info[1],
                    'product_name': product_info[1] if product_info else 'N/A',
                    'qty_done': c.get('qty_done', 0)
                })
        
        return result
    
    def _get_productor_from_lot(self, lot_id: int) -> Optional[Dict]:
        """Obtiene el productor original de un lote MP."""
        
        # Buscar movimientos del lote desde ubicación de proveedor
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['lot_id', '=', lot_id]],
            ['id', 'picking_id', 'location_id', 'date'],
            order='date asc',
            limit=20
        )
        
        if not move_lines:
            return None
        
        # Buscar el que viene de Vendor/Proveedor
        for ml in move_lines:
            loc_info = ml.get('location_id')
            if loc_info:
                loc_name = loc_info[1] if isinstance(loc_info, list) else str(loc_info)
                
                # Verificar si es de proveedor
                if 'vendor' in loc_name.lower() or 'proveedor' in loc_name.lower():
                    picking_info = ml.get('picking_id')
                    
                    if picking_info:
                        picking_id = picking_info[0]
                        
                        # Obtener el picking
                        pickings = self.odoo.search_read(
                            'stock.picking',
                            [['id', '=', picking_id]],
                            ['id', 'name', 'partner_id', 'scheduled_date', 'origin']
                        )
                        
                        if pickings and pickings[0].get('partner_id'):
                            partner_ref = pickings[0]['partner_id']
                            partner_id = partner_ref[0]
                            
                            # Obtener info del productor
                            partners = self.odoo.search_read(
                                'res.partner',
                                [['id', '=', partner_id]],
                                ['id', 'name', 'vat', 'phone', 'email', 'street', 'city']
                            )
                            
                            if partners:
                                return {
                                    'id': partners[0]['id'],
                                    'nombre': partners[0]['name'],
                                    'rut': partners[0].get('vat', ''),
                                    'telefono': partners[0].get('phone', ''),
                                    'email': partners[0].get('email', ''),
                                    'direccion': f"{partners[0].get('street', '')} {partners[0].get('city', '')}".strip(),
                                    'fecha_recepcion': str(pickings[0].get('scheduled_date', ''))[:19],
                                    'picking': pickings[0]['name']
                                }
        
        return {'nombre': 'Producción Interna', 'id': None}
    
    # ========================================
    # FUNCIONES DE RESUMEN
    # ========================================
    
    def _extraer_productor(self) -> Optional[Dict]:
        """Extrae la información del productor de la cadena."""
        for registro in self.cadena:
            if registro['tipo'] == 'MATERIA_PRIMA':
                return registro.get('productor')
        return None
    
    def _generar_resumen(self) -> Dict:
        """Genera un resumen de la trazabilidad."""
        procesos = [r for r in self.cadena if r['tipo'] == 'PROCESO']
        mp = [r for r in self.cadena if r['tipo'] == 'MATERIA_PRIMA']
        
        # Calcular rendimiento total
        total_kg_mp = sum(c.get('qty_done', 0) 
                         for r in procesos 
                         for c in r.get('consumos', [])
                         if r['nivel'] == max(r2['nivel'] for r2 in procesos))
        
        return {
            'total_procesos': len(procesos),
            'total_lotes_mp': len(mp),
            'etapas': [r['mo_name'] for r in procesos],
            'salas': list(set(r.get('sala', 'N/A') for r in procesos)),
            'kg_mp_total': round(total_kg_mp, 2) if total_kg_mp > 0 else 0
        }


# ========================================
# MAIN
# ========================================

def main():
    """Función principal para ejecutar desde CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Trazabilidad completa en Odoo')
    parser.add_argument('--pallet', help='Nombre del pallet a rastrear')
    parser.add_argument('--lote', help='Nombre del lote PT a rastrear')
    parser.add_argument('--username', help='Usuario Odoo (o usar ODOO_USERNAME env)')
    parser.add_argument('--password', help='Password Odoo (o usar ODOO_PASSWORD env)')
    parser.add_argument('--output', help='Archivo JSON de salida (opcional)')
    
    args = parser.parse_args()
    
    # Obtener credenciales
    username = args.username or os.getenv('ODOO_USERNAME')
    password = args.password or os.getenv('ODOO_PASSWORD')
    
    if not username or not password:
        print("❌ Error: Se requieren credenciales de Odoo")
        print("   Usar --username y --password o variables de entorno")
        return
    
    if not args.pallet and not args.lote:
        print("❌ Error: Se requiere --pallet o --lote")
        return
    
    # Crear instancia de trazabilidad
    tracer = TrazabilidadCompleta(username, password)
    
    # Rastrear
    if args.pallet:
        resultado = tracer.rastrear_desde_pallet(args.pallet)
    else:
        # Buscar el lote por nombre
        lotes = tracer.odoo.search_read(
            'stock.lot',
            [['name', '=', args.lote]],
            ['id'],
            limit=1
        )
        if not lotes:
            print(f"❌ Lote {args.lote} no encontrado")
            return
        
        resultado = tracer.rastrear_desde_lote(lotes[0]['id'], args.lote)
    
    # Mostrar resultado
    print("\n" + "="*80)
    print("📊 RESULTADO DE TRAZABILIDAD")
    print("="*80)
    
    if resultado.get('error'):
        print(f"❌ {resultado['error']}")
        return
    
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    
    # Guardar a archivo si se especificó
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Resultado guardado en: {args.output}")


if __name__ == '__main__':
    main()
