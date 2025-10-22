# src/crew/tools/source_retrieval_tool.py - v1.0.1
"""
Tool para recuperar fuentes de respuestas anteriores.
"""

from typing import Any, Optional
from crewai_tools import BaseTool
import json


class SourceRetrievalTool(BaseTool):
    """
    Tool para recuperar fuentes del último mensaje con sources.
    """
    
    name: str = "source_retrieval"
    description: str = (
        "Recupera las fuentes (URLs) del último mensaje que las usó. "
        "Útil cuando el usuario pregunta '¿de dónde sacaste eso?'. "
        "No requiere input."
    )
    
    # IMPORTANTE: Declarar db_manager como atributo
    db_manager: Any = None
    
    def __init__(self, db_manager, **kwargs):
        """
        Inicializa el tool.
        
        Args:
            db_manager: DatabaseManager
        """
        super().__init__(**kwargs)
        self.db_manager = db_manager
    
    def _run(self, conversation_id: Optional[int] = None) -> str:
        """
        Recupera las fuentes.
        
        Args:
            conversation_id: ID de conversación (opcional)
            
        Returns:
            Fuentes formateadas o mensaje de no encontradas
        """
        try:
            # Obtener última conversación si no se especifica
            if conversation_id is None:
                conversations = self.db_manager.get_active_conversations(limit=1)
                if not conversations:
                    return "No hay conversaciones activas"
                conversation_id = conversations[0].id
            
            # Obtener mensajes recientes
            messages = self.db_manager.get_conversation_messages(
                conversation_id=conversation_id,
                limit=20
            )
            
            # Buscar último mensaje con sources
            for message in reversed(messages):
                if message.role == 'assistant' and message.extra_metadata:
                    metadata = message.extra_metadata
                    
                    if isinstance(metadata, dict) and 'sources' in metadata:
                        sources = metadata['sources']
                        
                        if sources:
                            # Formatear fuentes
                            result = "Fuentes encontradas:\n\n"
                            for i, source in enumerate(sources, 1):
                                result += f"{i}. {source.get('title', 'Sin título')}\n"
                                result += f"   {source.get('url', 'Sin URL')}\n\n"
                            return result
            
            return "No se encontraron fuentes en mensajes recientes"
            
        except Exception as e:
            return f"Error recuperando fuentes: {e}"