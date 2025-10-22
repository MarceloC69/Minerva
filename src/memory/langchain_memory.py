# src/memory/langchain_memory.py
"""
Wrapper de LangChain SQLChatMessageHistory para memoria persistente.
Usa la base de datos SQLite existente de Minerva.
"""

from typing import List, Optional
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import logging

logger = logging.getLogger(__name__)


class LangChainMemoryWrapper:
    """
    Wrapper para SQLChatMessageHistory de LangChain.
    
    Características:
    - Usa SQLite existente de Minerva
    - Persistencia automática de conversaciones
    - Compatible con sistema actual
    """
    
    def __init__(self, db_path: str, conversation_id: str):
        """
        Inicializa el wrapper de memoria.
        
        Args:
            db_path: Ruta a la base de datos SQLite
            conversation_id: ID único de la conversación
        """
        self.db_path = db_path
        self.conversation_id = str(conversation_id)
        
        # Crear SQLChatMessageHistory
        self.history = SQLChatMessageHistory(
            session_id=self.conversation_id,
            connection=f"sqlite:///{db_path}"
        )
        
        logger.info(f"✅ LangChain memory inicializada para conversación {conversation_id}")
    
    def add_user_message(self, message: str):
        """Agrega mensaje del usuario."""
        self.history.add_user_message(message)
        logger.debug(f"Usuario: {message[:50]}...")
    
    def add_ai_message(self, message: str):
        """Agrega mensaje de la IA."""
        self.history.add_ai_message(message)
        logger.debug(f"Minerva: {message[:50]}...")
    
    def get_messages(self, limit: Optional[int] = None) -> List[BaseMessage]:
        """
        Recupera mensajes del historial.
        
        Args:
            limit: Número máximo de mensajes (None = todos)
            
        Returns:
            Lista de mensajes (HumanMessage, AIMessage)
        """
        messages = self.history.messages
        
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def get_formatted_history(self, limit: Optional[int] = 10) -> str:
        """
        Obtiene historial formateado como texto.
        
        Args:
            limit: Número de mensajes recientes (default: 10)
            
        Returns:
            String con historial formateado
        """
        messages = self.get_messages(limit=limit)
        
        if not messages:
            return ""
        
        formatted = "--- HISTORIAL RECIENTE ---\n"
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted += f"Usuario: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                formatted += f"Minerva: {msg.content}\n"
        formatted += "---\n"
        
        return formatted
    
    def clear(self):
        """Limpia el historial de esta conversación."""
        self.history.clear()
        logger.info(f"🗑️ Historial limpiado para conversación {self.conversation_id}")
    
    def get_message_count(self) -> int:
        """Retorna el número de mensajes en el historial."""
        return len(self.history.messages)