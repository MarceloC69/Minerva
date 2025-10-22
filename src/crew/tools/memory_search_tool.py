# ============================================================
# src/crew/tools/memory_search_tool.py
# ============================================================
"""Tool de CrewAI para buscar en la memoria de mem0."""

from crewai.tools import BaseTool
from typing import Type, Optional, Any
from pydantic import BaseModel, Field


class MemorySearchInput(BaseModel):
    """Input para búsqueda en memoria."""
    query: str = Field(..., description="Query para buscar en la memoria del usuario")
    limit: int = Field(default=3, description="Número máximo de resultados")


class MemorySearchTool(BaseTool):
    """
    Tool para buscar información en la memoria persistente (mem0).
    
    Uso: Cuando necesites recordar información sobre el usuario,
    conversaciones pasadas, o contexto histórico.
    """
    
    name: str = "search_memory"
    description: str = """Busca en la memoria persistente del usuario.
    Usa esta herramienta cuando necesites:
    - Recordar información del usuario (nombre, preferencias, etc.)
    - Contexto de conversaciones pasadas
    - Hechos mencionados anteriormente
    
    Input: query (str) - pregunta o tema a buscar
    Output: Información relevante de la memoria
    """
    args_schema: Type[BaseModel] = MemorySearchInput
    
    def __init__(self, mem0_wrapper: Any, **kwargs):
        super().__init__(**kwargs)
        # Usar atributo privado para evitar conflicto con Pydantic
        object.__setattr__(self, '_mem0', mem0_wrapper)
    
    def _run(self, query: str, limit: int = 3) -> str:
        """Ejecuta la búsqueda en memoria."""
        try:
            memories = self._mem0.search(query=query, limit=limit)
            
            if not memories:
                return "No encontré información relevante en la memoria."
            
            result = "📚 Información de la memoria:\n\n"
            for i, mem in enumerate(memories, 1):
                memory_text = mem.get('memory', mem.get('text', str(mem)))
                result += f"{i}. {memory_text}\n"
            
            return result
            
        except Exception as e:
            return f"Error buscando en memoria: {str(e)}"