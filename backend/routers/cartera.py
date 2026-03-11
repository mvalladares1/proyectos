"""
Router para Cartera - CxP (Cuentas por Pagar) y CxC (Cuentas por Cobrar)
Antigüedad de facturas basada en fecha estimada de pago
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime, date
from collections import defaultdict
import logging

from shared.odoo_client import OdooClient
from backend.services.currency_service import CurrencyService

router = APIRouter(prefix="/api/v1/cartera", tags=["cartera"])
logger = logging.getLogger(__name__)


def clasificar_antiguedad_cxp(dias: int) -> str:
    """Clasifica días de antigüedad para CxP (proveedores)"""
    if dias > 60:
        return "vencidas_60_mas"
    elif dias > 30:
        return "vencidas_30_60"
    elif dias > 0:
        return "vencidas_0_30"
    elif dias >= -15:
        return "por_vencer_0_15"
    elif dias >= -30:
        return "por_vencer_15_30"
    else:
        return "por_vencer_30_mas"


def clasificar_antiguedad_cxc(dias: int) -> str:
    """Clasifica días de antigüedad para CxC (clientes)"""
    if dias > 32:
        return "vencidas_32_mas"
    elif dias > 15:
        return "vencidas_16_31"
    elif dias > 0:
        return "vencidas_0_15"
    elif dias >= -15:
        return "por_vencer_0_15"
    elif dias >= -31:
        return "por_vencer_16_31"
    else:
        return "por_vencer_32_mas"


@router.get("/antiguedad")
async def obtener_antiguedad_cartera(
    username: str,
    password: str,
    fecha_corte: Optional[str] = None
):
    """
    Obtiene antigüedad de cartera (CxP y CxC).
    
    Clasifica facturas por:
    - CxP: Categoría de contacto (Productor, Proveedor, Transportista)
    - CxC: Tipo de cliente (Nacional CLP, Internacional USD)
    
    Rangos de antigüedad basados en fecha estimada de pago vs fecha de corte.
    """
    try:
        odoo = OdooClient(username=username, password=password)
        
        # Fecha de corte (hoy por defecto)
        if fecha_corte:
            fecha_corte_dt = datetime.strptime(fecha_corte, "%Y-%m-%d").date()
        else:
            fecha_corte_dt = date.today()
        
        # ═══════════════════════════════════════════════════════════════════
        # CxP - CUENTAS POR PAGAR (Facturas de Proveedor)
        # ═══════════════════════════════════════════════════════════════════
        
        # Facturas de proveedor pendientes (in_invoice) y borradores
        facturas_proveedor = odoo.search_read(
            'account.move',
            [
                ['move_type', 'in', ['in_invoice', 'in_refund']],
                ['state', 'in', ['posted', 'draft']],
                ['payment_state', 'in', ['not_paid', 'partial']]
            ],
            [
                'id', 'name', 'partner_id', 'amount_total', 'amount_residual',
                'invoice_date', 'invoice_date_due', 'x_studio_fecha_estimada_de_pago',
                'currency_id', 'state', 'move_type'
            ],
            limit=5000
        )
        
        # Obtener categorías de contactos
        partner_ids = list(set(
            f['partner_id'][0] for f in facturas_proveedor 
            if f.get('partner_id') and isinstance(f['partner_id'], (list, tuple))
        ))
        
        categorias_por_partner = {}
        if partner_ids:
            partners = odoo.read('res.partner', partner_ids, ['id', 'category_id'])
            
            # Obtener nombres de categorías
            all_cat_ids = []
            for p in partners:
                cat_ids = p.get('category_id', [])
                if cat_ids:
                    all_cat_ids.extend(cat_ids)
            
            cat_nombres = {}
            if all_cat_ids:
                categorias = odoo.read('res.partner.category', list(set(all_cat_ids)), ['id', 'name'])
                cat_nombres = {c['id']: c['name'] for c in categorias}
            
            for p in partners:
                cat_ids = p.get('category_id', [])
                if cat_ids:
                    # Tomar primera categoría relevante
                    for cid in cat_ids:
                        nombre = cat_nombres.get(cid, '')
                        if nombre in ['Productor', 'Proveedor', 'Transportista']:
                            categorias_por_partner[p['id']] = nombre
                            break
                    if p['id'] not in categorias_por_partner:
                        categorias_por_partner[p['id']] = cat_nombres.get(cat_ids[0], 'Otros')
                else:
                    categorias_por_partner[p['id']] = 'Otros'
        
        # Estructura CxP por categoría
        cxp_por_categoria = defaultdict(lambda: {
            "vencidas_60_mas": 0,
            "vencidas_30_60": 0,
            "vencidas_0_30": 0,
            "por_vencer_0_15": 0,
            "por_vencer_15_30": 0,
            "por_vencer_30_mas": 0,
            "borrador": 0,
            "total": 0
        })
        
        remuneraciones = 0
        bancos = 0
        
        for f in facturas_proveedor:
            partner_data = f.get('partner_id')
            if not partner_data or not isinstance(partner_data, (list, tuple)):
                continue
            
            partner_id = partner_data[0]
            partner_name = partner_data[1] if len(partner_data) > 1 else ''
            
            # Monto (residual para posted, total para draft)
            if f.get('state') == 'draft':
                monto = float(f.get('amount_total') or 0)
            else:
                monto = float(f.get('amount_residual') or 0)
            
            if monto == 0:
                continue
            
            # Convertir moneda
            currency_data = f.get('currency_id')
            currency_name = currency_data[1] if isinstance(currency_data, (list, tuple)) and len(currency_data) > 1 else 'CLP'
            currency_upper = str(currency_name).upper()
            
            if 'USD' in currency_upper:
                monto = CurrencyService.convert_usd_to_clp(monto)
            elif 'UF' in currency_upper or 'CLF' in currency_upper:
                monto = CurrencyService.convert_uf_to_clp(monto)
            
            # N/C invierte signo
            if f.get('move_type') == 'in_refund':
                monto = -monto
            
            # Categoría del contacto
            categoria = categorias_por_partner.get(partner_id, 'Otros')
            
            # Detectar Remuneraciones y Bancos por nombre
            if 'remuneracion' in partner_name.lower() or 'sueldo' in partner_name.lower():
                remuneraciones += monto
                continue
            if 'banco' in partner_name.lower() and 'prestamo' in partner_name.lower():
                bancos += monto
                continue
            
            # Clasificar por antigüedad
            if f.get('state') == 'draft':
                cxp_por_categoria[categoria]["borrador"] += monto
            else:
                # Usar fecha estimada de pago > fecha vencimiento > fecha factura
                fecha_ref = (
                    f.get('x_studio_fecha_estimada_de_pago') or 
                    f.get('invoice_date_due') or 
                    f.get('invoice_date')
                )
                
                if fecha_ref:
                    try:
                        fecha_ref_dt = datetime.strptime(str(fecha_ref)[:10], "%Y-%m-%d").date()
                        dias = (fecha_corte_dt - fecha_ref_dt).days
                        bucket = clasificar_antiguedad_cxp(dias)
                        cxp_por_categoria[categoria][bucket] += monto
                    except:
                        cxp_por_categoria[categoria]["vencidas_0_30"] += monto
                else:
                    cxp_por_categoria[categoria]["vencidas_0_30"] += monto
            
            cxp_por_categoria[categoria]["total"] += monto
        
        # Formatear CxP
        cxp_resultado = []
        orden_categorias = ['Productor', 'Proveedor', 'Transportista', 'Otros']
        
        for cat in orden_categorias:
            if cat in cxp_por_categoria:
                data = cxp_por_categoria[cat]
                cxp_resultado.append({
                    "categoria": cat,
                    **data
                })
        
        # Total general CxP
        total_cxp = sum(d["total"] for d in cxp_resultado) + remuneraciones + bancos
        
        # ═══════════════════════════════════════════════════════════════════
        # CxC - CUENTAS POR COBRAR (Facturas de Cliente)
        # ═══════════════════════════════════════════════════════════════════
        
        # Facturas de cliente pendientes
        facturas_cliente = odoo.search_read(
            'account.move',
            [
                ['move_type', 'in', ['out_invoice', 'out_refund']],
                ['state', '=', 'posted'],
                ['payment_state', 'in', ['not_paid', 'partial']]
            ],
            [
                'id', 'name', 'partner_id', 'amount_total', 'amount_residual',
                'invoice_date', 'invoice_date_due', 'x_studio_fecha_estimada_de_pago',
                'currency_id', 'move_type'
            ],
            limit=5000
        )
        
        # Obtener info de clientes (para saber si es nacional/internacional)
        cliente_ids = list(set(
            f['partner_id'][0] for f in facturas_cliente 
            if f.get('partner_id') and isinstance(f['partner_id'], (list, tuple))
        ))
        
        clientes_info = {}
        if cliente_ids:
            clientes = odoo.read('res.partner', cliente_ids, ['id', 'name', 'country_id'])
            for c in clientes:
                country = c.get('country_id')
                es_chile = False
                if country and isinstance(country, (list, tuple)) and len(country) > 1:
                    es_chile = 'chile' in country[1].lower() or country[0] == 46  # ID Chile
                clientes_info[c['id']] = {
                    'name': c.get('name', ''),
                    'es_nacional': es_chile
                }
        
        # Estructura CxC por cliente
        cxc_nacionales = defaultdict(lambda: {
            "vencidas_0_15": 0,
            "vencidas_16_31": 0,
            "vencidas_32_mas": 0,
            "por_vencer_0_15": 0,
            "por_vencer_16_31": 0,
            "por_vencer_32_mas": 0,
            "total": 0
        })
        
        cxc_internacionales = defaultdict(lambda: {
            "vencidas_0_15": 0,
            "vencidas_16_31": 0,
            "vencidas_32_mas": 0,
            "por_vencer_0_15": 0,
            "por_vencer_16_31": 0,
            "por_vencer_32_mas": 0,
            "total": 0
        })
        
        for f in facturas_cliente:
            partner_data = f.get('partner_id')
            if not partner_data or not isinstance(partner_data, (list, tuple)):
                continue
            
            partner_id = partner_data[0]
            cliente_info = clientes_info.get(partner_id, {'name': partner_data[1], 'es_nacional': True})
            cliente_name = cliente_info['name']
            
            monto = float(f.get('amount_residual') or 0)
            if monto == 0:
                continue
            
            # Moneda original
            currency_data = f.get('currency_id')
            currency_name = currency_data[1] if isinstance(currency_data, (list, tuple)) and len(currency_data) > 1 else 'CLP'
            currency_upper = str(currency_name).upper()
            
            # N/C invierte signo
            if f.get('move_type') == 'out_refund':
                monto = -monto
            
            # Clasificar por antigüedad
            fecha_ref = (
                f.get('x_studio_fecha_estimada_de_pago') or 
                f.get('invoice_date_due') or 
                f.get('invoice_date')
            )
            
            bucket = "vencidas_0_15"
            if fecha_ref:
                try:
                    fecha_ref_dt = datetime.strptime(str(fecha_ref)[:10], "%Y-%m-%d").date()
                    dias = (fecha_corte_dt - fecha_ref_dt).days
                    bucket = clasificar_antiguedad_cxc(dias)
                except:
                    pass
            
            # Asignar a nacional o internacional
            if cliente_info['es_nacional']:
                # Convertir a CLP si está en otra moneda
                if 'USD' in currency_upper:
                    monto = CurrencyService.convert_usd_to_clp(monto)
                elif 'UF' in currency_upper or 'CLF' in currency_upper:
                    monto = CurrencyService.convert_uf_to_clp(monto)
                
                cxc_nacionales[cliente_name][bucket] += monto
                cxc_nacionales[cliente_name]["total"] += monto
            else:
                # Internacionales: mantener en USD
                if 'CLP' in currency_upper or currency_upper == '':
                    # Convertir CLP a USD
                    monto = CurrencyService.convert_clp_to_usd(monto)
                elif 'UF' in currency_upper or 'CLF' in currency_upper:
                    monto_clp = CurrencyService.convert_uf_to_clp(monto)
                    monto = CurrencyService.convert_clp_to_usd(monto_clp)
                # USD se mantiene
                
                cxc_internacionales[cliente_name][bucket] += monto
                cxc_internacionales[cliente_name]["total"] += monto
        
        # Formatear CxC
        cxc_nac_resultado = [
            {"cliente": k, "moneda": "CLP", **v}
            for k, v in sorted(cxc_nacionales.items(), key=lambda x: -x[1]["total"])
        ]
        
        cxc_int_resultado = [
            {"cliente": k, "moneda": "USD", **v}
            for k, v in sorted(cxc_internacionales.items(), key=lambda x: -x[1]["total"])
        ]
        
        # Totales CxC
        total_cxc_clp = sum(d["total"] for d in cxc_nac_resultado)
        total_cxc_usd = sum(d["total"] for d in cxc_int_resultado)
        
        return {
            "fecha_corte": fecha_corte_dt.isoformat(),
            "cxp": {
                "por_categoria": cxp_resultado,
                "remuneraciones": remuneraciones,
                "bancos": bancos,
                "total_general": total_cxp
            },
            "cxc": {
                "nacionales": cxc_nac_resultado,
                "internacionales": cxc_int_resultado,
                "total_clp": total_cxc_clp,
                "total_usd": total_cxc_usd
            }
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error obteniendo antigüedad cartera: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
