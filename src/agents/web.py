# src/agents/web.py - v1.0.0
"""
Agente de búsqueda web para Minerva.
Busca información actualizada en internet y la presenta de forma clara.
"""

from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import ollama

from src.tools.web_search import WebSearchTool


class WebAgent:
    """
    Agente especializado en búsqueda web.
    
    Responsabilidades:
    - Buscar información actualizada en internet
    - Sintetizar resultados de múltiples fuentes
    - Citar fuentes cuando es relevante
    - Guardar links en metadata para referencia
    """
    
    def __init__(
        self,
        model_name: str = "phi3:latest",  # Cambiado de phi3:mini
        temperature: float = 0.3,
        db_manager=None,
        max_results: int = 5
    ):
        """
        Inicializa el agente web.
        
        Args:
            model_name: Modelo de Ollama a usar
            temperature: Temperatura para generación (más bajo = más preciso)
            db_manager: Manager de base de datos para guardar sources
            max_results: Número máximo de resultados a buscar
        """
        self.model_name = model_name
        self.temperature = temperature
        self.search_tool = WebSearchTool(max_results=max_results)
        self.db_manager = db_manager
        self.logger = logging.getLogger("minerva.web_agent")
    
    def _get_system_prompt(self) -> str:
        """
        Obtiene el system prompt del agente web.
        Intenta cargarlo desde la DB, si no usa uno por defecto.
        """
        if self.db_manager:
            try:
                from src.database.prompt_manager import PromptManager
                pm = PromptManager(self.db_manager)
                prompt = pm.get_active_prompt('web', 'system_prompt')
                if prompt:
                    return prompt
            except Exception as e:
                self.logger.warning(f"No se pudo cargar prompt desde DB: {e}")
        
        # Prompt por defecto
        return """Eres Minerva en modo de búsqueda web. Tu trabajo es sintetizar información de internet de forma clara y precisa.

DIRECTRICES:
- Resume la información de los resultados de búsqueda
- Sé conciso y directo
- Menciona cuando hay información contradictoria
- NO inventes información que no esté en los resultados
- Si los resultados no son suficientes, dilo claramente

FORMATO:
- Responde directamente la pregunta
- Usa la información más reciente y relevante
- Estructura bien la información con bullets si es necesario

NO hagas sugerencias adicionales a menos que se te pidan."""
    
    def search_and_answer(
        self,
        query: str,
        search_type: str = "general",
        conversation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Busca en web y genera una respuesta sintetizada.
        
        Args:
            query: Pregunta del usuario
            search_type: Tipo de búsqueda ('general' o 'news')
            conversation_id: ID de conversación para guardar en DB
            
        Returns:
            Diccionario con respuesta y metadata
        """
        try:
            self.logger.info(f"🌐 WebAgent procesando: '{query}'")
            
            # 1. Realizar búsqueda
            if search_type == "news":
                results = self.search_tool.search_news(query)
            else:
                results = self.search_tool.search(query)
            
            if not results:
                return {
                    'answer': "No pude encontrar información actualizada en internet sobre esa consulta. Esto puede ocurrir si:\n- DuckDuckGo no tiene resultados para esa búsqueda\n- La consulta necesita ser más específica\n- Hay problemas temporales de conexión\n\nIntenta reformular tu pregunta de otra manera.",
                    'sources': [],
                    'success': False
                }
            
            # 2. Construir contexto para el LLM
            context = self._build_context_from_results(results)
            
            # 3. Generar respuesta usando el LLM
            system_prompt = self._get_system_prompt()
            
            user_prompt = f"""Basándote en los siguientes resultados de búsqueda, responde la pregunta del usuario de forma clara y concisa.

RESULTADOS DE BÚSQUEDA:
{context}

PREGUNTA DEL USUARIO:
{query}

INSTRUCCIONES:
- Sintetiza la información más relevante
- Sé directo y preciso
- No repitas información
- No hagas sugerencias adicionales

RESPUESTA:"""
            
            # Usar ollama directamente
            response_obj = ollama.chat(
                model=self.model_name,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                options={
                    'temperature': self.temperature
                }
            )
            
            response = response_obj['message']['content']
            
            # 4. Extraer sources para metadata (NO mostrar en respuesta)
            sources = [
                {
                    'title': r['title'],
                    'url': r['link'],
                    'snippet': r['snippet'][:100]
                }
                for r in results[:3]
            ]
            
            # 5. Guardar en DB si hay conversation_id
            if conversation_id and self.db_manager:
                try:
                    self.db_manager.add_message(
                        conversation_id=conversation_id,
                        role='assistant',
                        content=response,
                        agent_type='web',
                        model=self.model_name,
                        temperature=self.temperature,
                        had_context=True,
                        context_source='web_search',
                        metadata={
                            'query': query,
                            'search_type': search_type,
                            'sources': sources,
                            'num_results': len(results)
                        }
                    )
                except Exception as e:
                    self.logger.error(f"Error guardando en DB: {e}")
            
            self.logger.info("✅ WebAgent completado")
            
            return {
                'answer': response,
                'sources': sources,
                'search_type': search_type,
                'num_results': len(results),
                'success': True
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error en WebAgent: {e}")
            return {
                'answer': f"Ocurrió un error al buscar en internet: {str(e)}",
                'sources': [],
                'success': False
            }
    
    def _build_context_from_results(self, results: List[Dict[str, str]]) -> str:
        """
        Construye un contexto formateado a partir de resultados de búsqueda.
        
        Args:
            results: Lista de resultados de búsqueda
            
        Returns:
            String con contexto formateado
        """
        context_parts = []
        
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[Resultado {i}]\n"
                f"Título: {result['title']}\n"
                f"Contenido: {result['snippet']}\n"
                f"Fuente: {result['link']}\n"
            )
        
        return "\n".join(context_parts)
    
    def quick_fact(self, query: str) -> Optional[str]:
        """
        Intenta obtener una respuesta rápida sin procesamiento completo.
        
        Args:
            query: Pregunta simple
            
        Returns:
            Respuesta directa si está disponible
        """
        try:
            answer = self.search_tool.quick_answer(query)
            return answer
        except Exception as e:
            self.logger.error(f"Error en quick_fact: {e}")
            return None


# Para testing directo
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    # Agregar root al path
    ROOT_DIR = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(ROOT_DIR))
    
    # Crear agente
    agent = WebAgent(
        model_name="phi3:latest",  # Cambiado de phi3:mini
        temperature=0.3,
        max_results=3
    )
    
    # Test
    print("=== TEST: WebAgent ===\n")
    
    query = "¿Cuál es la capital de Francia?"
    print(f"Pregunta: {query}\n")
    
    result = agent.search_and_answer(query)
    
    print(f"Respuesta:\n{result['answer']}\n")
    print(f"Fuentes ({len(result['sources'])}):")
    for source in result['sources']:
        print(f"  - {source['title']}")
        print(f"    {source['url']}\n")