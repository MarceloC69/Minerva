# ============================================================
# src/crew/tools/source_retrieval_tool.py
# ============================================================
"""Tool de CrewAI para recuperar fuentes web de mensajes previos."""

from crewai.tools import BaseTool
from typing import Type, Any
from pydantic import BaseModel, Field


class SourceRetrievalInput(BaseModel):
    """Input para recuperación de fuentes."""
    conversation_id: int = Field(..., description="ID de la conversación actual")


class SourceRetrievalTool(BaseTool):
    """
    Tool para recuperar fuentes web del último mensaje.
    
    Uso: Cuando el usuario pregunte "¿de dónde sacaste eso?" o
    solicite las fuentes de información.
    """
    
    name: str = "retrieve_sources"
    description: str = """Recupera las fuentes web del último mensaje.
    Usa esta herramienta cuando el usuario pregunte por:
    - Fuentes de información
    - Links o URLs usados
    - De dónde salió la información
    
    Input: conversation_id (int)
    Output: Lista de fuentes con títulos y URLs
    """
    args_schema: Type[BaseModel] = SourceRetrievalInput
    
    def __init__(self, db_manager: Any, **kwargs):
        super().__init__(**kwargs)
        # Usar atributo privado
        object.__setattr__(self, '_db_manager', db_manager)
    
    def _run(self, conversation_id: int) -> str:
        """Recupera las fuentes del último mensaje."""
        try:
            messages = self._db_manager.get_messages(
                conversation_id=conversation_id,
                limit=10
            )
            
            for msg in reversed(messages):
                if msg['role'] == 'assistant' and msg.get('metadata'):
                    metadata = msg['metadata']
                    if 'sources' in metadata:
                        sources = metadata['sources']
                        
                        if not sources:
                            return "No hay fuentes web en la última respuesta."
                        
                        result = "🔗 Fuentes utilizadas:\n\n"
                        for i, source in enumerate(sources, 1):
                            title = source.get('title', 'Sin título')
                            url = source.get('url', 'Sin URL')
                            result += f"{i}. **{title}**\n   {url}\n\n"
                        
                        return result
            
            return "No encontré fuentes en mensajes recientes."
            
        except Exception as e:
            return f"Error recuperando fuentes: {str(e)}"