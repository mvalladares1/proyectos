"""
Servicio para integración con Ollama (modelo de IA local)
"""
import httpx
import json
from typing import Dict, List, Optional, Any
from datetime import datetime


class AIService:
    """Servicio para generar resúmenes de trazabilidad usando Ollama"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3.2"  # Modelo pequeño y rápido
        
    async def generate_traceability_summary(
        self,
        search_context: Dict[str, Any],
        traceability_data: Dict[str, Any]
    ) -> str:
        """
        Genera un resumen de trazabilidad usando IA
        
        Args:
            search_context: Contexto de búsqueda (tipo, parámetros, fechas, etc.)
            traceability_data: Datos completos de trazabilidad
            
        Returns:
            Resumen generado por la IA
        """
        # Construir el prompt según el contexto
        prompt = self._build_prompt(search_context, traceability_data)
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,  # Más determinístico
                            "top_p": 0.9,
                            "num_predict": 500,  # Máximo de tokens
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "No se pudo generar el resumen.")
                else:
                    return f"Error al conectar con Ollama: {response.status_code}"
                    
        except httpx.ConnectError:
            return "⚠️ No se pudo conectar con Ollama. Asegúrate de que el servicio esté corriendo (ollama serve)."
        except Exception as e:
            return f"Error inesperado: {str(e)}"
    
    def _build_prompt(self, context: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Construye el prompt según el tipo de búsqueda"""
        
        search_type = context.get("search_type", "unknown")
        
        # Extraer estadísticas clave
        stats = self._extract_stats(data)
        
        # Prompt base
        base_prompt = """Eres un asistente experto en trazabilidad agroalimentaria. Tu trabajo es analizar datos de trazabilidad y generar resúmenes claros, concisos y accionables en español.

IMPORTANTE: 
- Sé específico con números y nombres
- Menciona fechas importantes
- Identifica el flujo completo (origen → destino)
- Resalta cualquier anomalía o patrón relevante
- Usa lenguaje profesional pero claro
- Máximo 300 palabras

"""
        
        # Agregar contexto específico según el tipo de búsqueda
        if search_type == "sale":
            context_prompt = self._build_sale_context(context, stats)
        elif search_type == "date_range":
            context_prompt = self._build_date_range_context(context, stats)
        elif search_type == "pallet":
            context_prompt = self._build_pallet_context(context, stats)
        elif search_type == "guide":
            context_prompt = self._build_guide_context(context, stats)
        else:
            context_prompt = self._build_generic_context(context, stats)
        
        return base_prompt + context_prompt
    
    def _extract_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae estadísticas relevantes de los datos de trazabilidad"""
        
        pallets = data.get("pallets", {})
        processes = data.get("processes", {})
        suppliers = data.get("suppliers", {})
        customers = data.get("customers", {})
        links = data.get("links", [])
        
        # Contar recepciones y procesos
        receptions = {ref: p for ref, p in processes.items() if p.get("is_reception")}
        production_processes = {ref: p for ref, p in processes.items() if not p.get("is_reception")}
        
        # Calcular pesos totales
        total_weight_in = sum(p.get("qty_done", 0) for p in pallets.values() if p.get("move_type") in ["in", "internal"])
        total_weight_out = sum(p.get("qty_done", 0) for p in pallets.values() if p.get("move_type") == "out")
        
        # Extraer nombres de proveedores y clientes
        supplier_names = [s.get("name", "Desconocido") for s in suppliers.values()]
        customer_names = [c.get("name", "Desconocido") for c in customers.values()]
        
        # Extraer fechas
        dates = []
        for p in pallets.values():
            if p.get("pack_date"):
                dates.append(p["pack_date"])
            elif p.get("date"):
                dates.append(p["date"])
        
        return {
            "total_pallets": len(pallets),
            "total_receptions": len(receptions),
            "total_processes": len(production_processes),
            "total_suppliers": len(suppliers),
            "total_customers": len(customers),
            "total_links": len(links),
            "total_weight_in": total_weight_in,
            "total_weight_out": total_weight_out,
            "supplier_names": supplier_names[:5],  # Top 5
            "customer_names": customer_names[:5],  # Top 5
            "date_range": {
                "min": min(dates) if dates else None,
                "max": max(dates) if dates else None
            }
        }
    
    def _build_sale_context(self, context: Dict, stats: Dict) -> str:
        """Prompt para búsqueda por venta"""
        sale_id = context.get("sale_id", "N/A")
        customer = context.get("customer_name", "Cliente desconocido")
        
        return f"""
CONTEXTO: Trazabilidad de venta
- ID de Venta: {sale_id}
- Cliente: {customer}

DATOS:
- Total de pallets enviados: {stats['total_pallets']}
- Peso total: {stats['total_weight_out']:.2f} kg
- Procesos involucrados: {stats['total_processes']}
- Proveedores origen: {', '.join(stats['supplier_names']) if stats['supplier_names'] else 'N/A'}
- Rango de fechas: {stats['date_range']['min']} a {stats['date_range']['max']}

TAREA: Genera un resumen ejecutivo de la trazabilidad de esta venta. Describe:
1. El origen de los productos (proveedores y fechas de recepción)
2. Los procesos de transformación aplicados
3. El destino final (cliente y fecha de despacho)
4. Cualquier observación relevante sobre tiempos o volúmenes
"""
    
    def _build_date_range_context(self, context: Dict, stats: Dict) -> str:
        """Prompt para búsqueda por rango de fechas"""
        start_date = context.get("start_date", "N/A")
        end_date = context.get("end_date", "N/A")
        
        return f"""
CONTEXTO: Trazabilidad por rango de fechas
- Período: {start_date} a {end_date}

DATOS:
- Total de pallets: {stats['total_pallets']}
- Recepciones: {stats['total_receptions']}
- Procesos de producción: {stats['total_processes']}
- Proveedores activos: {stats['total_suppliers']} ({', '.join(stats['supplier_names'][:3])})
- Clientes atendidos: {stats['total_customers']} ({', '.join(stats['customer_names'][:3])})
- Peso total procesado: {stats['total_weight_in']:.2f} kg
- Peso total despachado: {stats['total_weight_out']:.2f} kg

TAREA: Genera un resumen del flujo de trazabilidad en este período. Describe:
1. Volumen de recepciones y principales proveedores
2. Actividad de producción y transformación
3. Despachos y principales clientes
4. Eficiencia del flujo (mermas, tiempos, etc.)
"""
    
    def _build_pallet_context(self, context: Dict, stats: Dict) -> str:
        """Prompt para búsqueda por pallet específico"""
        pallet_id = context.get("pallet_id", "N/A")
        pallet_name = context.get("pallet_name", "N/A")
        
        return f"""
CONTEXTO: Trazabilidad de pallet específico
- ID Pallet: {pallet_id}
- Nombre: {pallet_name}

DATOS:
- Proveedores origen: {', '.join(stats['supplier_names']) if stats['supplier_names'] else 'Producción interna'}
- Procesos aplicados: {stats['total_processes']}
- Cliente destino: {', '.join(stats['customer_names']) if stats['customer_names'] else 'Stock interno'}
- Rango temporal: {stats['date_range']['min']} a {stats['date_range']['max']}
- Enlaces en la cadena: {stats['total_links']}

TAREA: Genera un resumen detallado de la trazabilidad de este pallet. Describe:
1. Origen completo (proveedor, recepción, fecha)
2. Transformaciones y procesos aplicados
3. Destino final (cliente y fecha)
4. Tiempo total del flujo y observaciones relevantes
"""
    
    def _build_guide_context(self, context: Dict, stats: Dict) -> str:
        """Prompt para búsqueda por guía de despacho"""
        guide_number = context.get("guide_number", "N/A")
        
        return f"""
CONTEXTO: Trazabilidad por guía de despacho
- Guía de Despacho: {guide_number}

DATOS:
- Pallets en la guía: {stats['total_pallets']}
- Peso total: {stats['total_weight_out']:.2f} kg
- Proveedores origen: {', '.join(stats['supplier_names']) if stats['supplier_names'] else 'N/A'}
- Procesos involucrados: {stats['total_processes']}
- Cliente destino: {', '.join(stats['customer_names']) if stats['customer_names'] else 'N/A'}
- Fecha: {stats['date_range']['max']}

TAREA: Genera un resumen de la trazabilidad de esta guía de despacho. Describe:
1. Composición del despacho (pallets y productos)
2. Origen de los materiales (proveedores y fechas)
3. Procesos aplicados antes del despacho
4. Observaciones sobre calidad o conformidad
"""
    
    def _build_generic_context(self, context: Dict, stats: Dict) -> str:
        """Prompt genérico"""
        return f"""
CONTEXTO: Análisis de trazabilidad general

DATOS:
- Total de pallets: {stats['total_pallets']}
- Recepciones: {stats['total_receptions']}
- Procesos: {stats['total_processes']}
- Proveedores: {stats['total_suppliers']}
- Clientes: {stats['total_customers']}
- Peso entrada: {stats['total_weight_in']:.2f} kg
- Peso salida: {stats['total_weight_out']:.2f} kg

TAREA: Genera un resumen general del flujo de trazabilidad. Describe el flujo completo desde proveedores hasta clientes, destacando volúmenes, procesos clave y observaciones relevantes.
"""


# Instancia global del servicio
ai_service = AIService()
