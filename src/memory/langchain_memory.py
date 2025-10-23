# src/memory/langchain_memory.py
"""
Wrapper de LangChain SQLChatMessageHistory para Minerva.
Proporciona memoria de conversación persistente.
"""

import logging
from typing import List, Dict, Any
from pathlib import Path

from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger('minerva.memory.langchain')


class LangChainMemoryWrapper:
    """
    Wrapper para LangChain SQLChatMessageHistory.
    
    Proporciona una interfaz simple para:
    - Agregar mensajes de usuario y AI
    - Recuperar historial formateado
    - Limpiar memoria
    """
    
    def __init__(self, db_path: str, conversation_id: int):
        """
        Inicializa el wrapper de memoria.
        
        Args:
            db_path: Ruta a la base de datos SQLite
            conversation_id: ID único de la conversación
        """
        self.db_path = db_path
        self.conversation_id = conversation_id
        
        # Crear SQLChatMessageHistory
        # Usamos connection_string en formato SQLite
        connection_string = f"sqlite:///{db_path}"
        
        # Session ID único por conversación
        session_id = f"conv_{conversation_id}"
        
        try:
            self.memory = SQLChatMessageHistory(
                connection_string=connection_string,
                session_id=session_id
            )
            logger.info(f"✅ Memoria inicializada para conversación {conversation_id}")
        except Exception as e:
            logger.error(f"❌ Error inicializando memoria: {e}")
            raise
    
    def add_user_message(self, message: str) -> None:
        """
        Agrega un mensaje del usuario.
        
        Args:
            message: Contenido del mensaje
        """
        try:
            self.memory.add_user_message(message)
            logger.debug(f"Usuario: {message[:50]}...")
        except Exception as e:
            logger.error(f"Error agregando mensaje de usuario: {e}")
            raise
    
    def add_ai_message(self, message: str) -> None:
        """
        Agrega un mensaje de la AI.
        
        Args:
            message: Contenido del mensaje
        """
        try:
            self.memory.add_ai_message(message)
            logger.debug(f"AI: {message[:50]}...")
        except Exception as e:
            logger.error(f"Error agregando mensaje de AI: {e}")
            raise
    
    def get_messages(self, limit: int = None) -> List[Dict[str, str]]:
        """
        Obtiene todos los mensajes.
        
        Args:
            limit: Número máximo de mensajes (más recientes)
        
        Returns:
            Lista de dicts con role y content
        """
        try:
            messages = self.memory.messages
            
            if limit:
                messages = messages[-limit:]
            
            result = []
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    result.append({'role': 'user', 'content': msg.content})
                elif isinstance(msg, AIMessage):
                    result.append({'role': 'assistant', 'content': msg.content})
            
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo mensajes: {e}")
            return []
    
    def get_formatted_history(self, limit: int = 10) -> str:
        """
        Obtiene historial formateado para incluir en prompts.
        
        Args:
            limit: Número máximo de intercambios (pares user/ai)
        
        Returns:
            String con historial formateado
        """
        try:
            messages = self.get_messages(limit=limit * 2)  # *2 porque son pares
            
            if not messages:
                return ""
            
            formatted = "\n--- CONVERSACIÓN RECIENTE ---\n"
            
            for msg in messages:
                role = "Usuario" if msg['role'] == 'user' else "Minerva"
                formatted += f"{role}: {msg['content']}\n"
            
            formatted += "---\n"
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formateando historial: {e}")
            return ""
    
    def get_message_count(self) -> int:
        """
        Obtiene el número total de mensajes.
        
        Returns:
            Cantidad de mensajes
        """
        try:
            return len(self.memory.messages)
        except Exception as e:
            logger.error(f"Error contando mensajes: {e}")
            return 0
    
    def clear(self) -> None:
        """
        Limpia toda la memoria de esta conversación.
        """
        try:
            self.memory.clear()
            logger.info(f"🗑️ Memoria limpiada para conversación {self.conversation_id}")
        except Exception as e:
            logger.error(f"Error limpiando memoria: {e}")
            raise