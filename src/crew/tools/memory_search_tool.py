# src/crew/tools/memory_search_tool.py - v1.0.1
"""
Tool para buscar en la memoria persistente (base de datos).
"""

from typing import Any
from crewai_tools import BaseTool


class MemorySearchTool(BaseTool):
    """
    Tool para buscar mensajes en la base de datos.
    """
    
    name: str = "memory_search"
    description: str = (
        "Busca en conversaciones pasadas. "
        "Útil para encontrar información mencionada anteriormente. "
        "Input: texto a buscar"
    )
    
    # IMPORTANTE: Declarar db_manager como atributo con tipo Any
    db_manager: Any = None
    
    def __init__(self, db_manager, **kwargs):
        """
        Inicializa el tool.
        
        Args:
            db_manager: DatabaseManager
        """
        super().__init__(**kwargs)
        self.db_manager = db_manager
    
    def _run(self, query: str) -> str:
        """
        Ejecuta la búsqueda.
        
        Args:
            query: Texto a buscar
            
        Returns:
            Resultados formateados
        """
        try:
            messages = self.db_manager.search_messages(query=query, limit=5)
            
            if not messages:
                return f"No se encontraron mensajes con '{query}'"
            
            results = []
            for msg in messages:
                results.append(
                    f"[{msg.timestamp.strftime('%Y-%m-%d %H:%M')}] "
                    f"{msg.role}: {msg.content[:150]}..."
                )
            
            return "\n\n".join(results)
            
        except Exception as e:
            return f"Error buscando en memoria: {e}"