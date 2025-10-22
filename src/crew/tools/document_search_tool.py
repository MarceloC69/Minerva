# ============================================================
# src/crew/tools/document_search_tool.py
# ============================================================
"""Tool de CrewAI para buscar en documentos indexados."""

from crewai.tools import BaseTool
from typing import Type, Any
from pydantic import BaseModel, Field


class DocumentSearchInput(BaseModel):
    """Input para búsqueda en documentos."""
    query: str = Field(..., description="Query para buscar en documentos")
    limit: int = Field(default=3, description="Número máximo de chunks")


class DocumentSearchTool(BaseTool):
    """
    Tool para buscar en documentos indexados (RAG).
    
    Uso: Cuando necesites información de documentos técnicos,
    manuales, o archivos que el usuario haya subido.
    """
    
    name: str = "search_documents"
    description: str = """Busca en documentos indexados (PDF, DOCX, etc).
    Usa esta herramienta para:
    - Información técnica de documentos
    - Manuales o guías subidas
    - Código o especificaciones
    
    Input: query (str) - pregunta sobre los documentos
    Output: Información relevante de los documentos con fuentes
    """
    args_schema: Type[BaseModel] = DocumentSearchInput
    
    def __init__(self, indexer: Any, **kwargs):
        super().__init__(**kwargs)
        # Usar atributo privado
        object.__setattr__(self, '_indexer', indexer)
    
    def _run(self, query: str, limit: int = 3) -> str:
        """Ejecuta la búsqueda en documentos."""
        try:
            if not self._indexer.has_documents():
                return "No hay documentos indexados disponibles."
            
            results = self._indexer.search_documents(
                query=query,
                collection_name='knowledge_base',
                limit=limit,
                score_threshold=0.5
            )
            
            if not results:
                return "No encontré información relevante en los documentos."
            
            response = "📄 Información de documentos:\n\n"
            for i, result in enumerate(results, 1):
                payload = result.get('payload', {})
                text = result.get('text', payload.get('text', ''))
                filename = payload.get('filename', 'Documento desconocido')
                score = result.get('score', 0)
                
                response += f"{i}. [{filename}] (relevancia: {score:.2f})\n"
                response += f"   {text[:200]}...\n\n"
            
            return response
            
        except Exception as e:
            return f"Error buscando en documentos: {str(e)}"