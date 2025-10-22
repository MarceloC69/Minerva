# src/crew/agents/memory_agent.py - v1.0.0
"""
Agente de memoria para Minerva.
Busca información en la base de datos: conversaciones, fuentes, metadata.
"""

from typing import Dict, Any, Optional, List
import logging
import json


class MemoryAgent:
    """
    Agente especializado en buscar información en la memoria persistente.
    
    Responsabilidades:
    - Buscar en conversaciones pasadas
    - Recuperar fuentes de respuestas anteriores
    - Encontrar metadata de mensajes
    - Construir contexto histórico
    """
    
    def __init__(self, db_manager, logger: Optional[logging.Logger] = None):
        """
        Inicializa el agente de memoria.
        
        Args:
            db_manager: DatabaseManager para acceder a SQLite
            logger: Logger opcional
        """
        self.db_manager = db_manager
        self.logger = logger or logging.getLogger("minerva.memory_agent")
    
    def get_last_sources(
        self,
        conversation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Recupera las fuentes del último mensaje en una conversación.
        
        Args:
            conversation_id: ID de conversación (None = última conversación activa)
            
        Returns:
            Dict con found=True/False y sources=[]
        """
        try:
            # Si no hay conversation_id, buscar la última conversación activa
            if conversation_id is None:
                conversations = self.db_manager.get_active_conversations(limit=1)
                if not conversations:
                    return {'found': False, 'sources': []}
                conversation_id = conversations[0].id
            
            # Obtener mensajes de la conversación
            messages = self.db_manager.get_conversation_messages(
                conversation_id=conversation_id,
                limit=20  # Últimos 20 mensajes
            )
            
            if not messages:
                return {'found': False, 'sources': []}
            
            # Buscar el último mensaje del asistente con sources
            for message in reversed(messages):
                if message.role == 'assistant' and message.extra_metadata:
                    metadata = message.extra_metadata
                    
                    # Verificar si tiene sources
                    if isinstance(metadata, dict) and 'sources' in metadata:
                        sources = metadata['sources']
                        
                        if sources:
                            self.logger.info(f"✅ Encontradas {len(sources)} fuentes")
                            return {
                                'found': True,
                                'sources': sources,
                                'message_id': message.id,
                                'agent_type': message.agent_type
                            }
            
            # No se encontraron fuentes
            self.logger.info("ℹ️ No se encontraron fuentes en mensajes recientes")
            return {'found': False, 'sources': []}
            
        except Exception as e:
            self.logger.error(f"❌ Error recuperando fuentes: {e}")
            return {'found': False, 'sources': [], 'error': str(e)}
    
    def search_conversations(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca en conversaciones pasadas.
        
        Args:
            query: Texto a buscar
            limit: Número máximo de resultados
            
        Returns:
            Lista de mensajes que coinciden
        """
        try:
            messages = self.db_manager.search_messages(
                query=query,
                limit=limit
            )
            
            results = []
            for msg in messages:
                results.append({
                    'message_id': msg.id,
                    'conversation_id': msg.conversation_id,
                    'role': msg.role,
                    'content': msg.content[:200],  # Preview
                    'timestamp': msg.timestamp.isoformat(),
                    'agent_type': msg.agent_type
                })
            
            self.logger.info(f"🔍 Encontrados {len(results)} mensajes para '{query}'")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Error buscando conversaciones: {e}")
            return []
    
    def get_conversation_context(
        self,
        conversation_id: int,
        last_n: int = 10
    ) -> str:
        """
        Obtiene contexto de una conversación.
        
        Args:
            conversation_id: ID de conversación
            last_n: Número de mensajes a recuperar
            
        Returns:
            String con contexto formateado
        """
        try:
            messages = self.db_manager.get_conversation_messages(
                conversation_id=conversation_id,
                limit=last_n
            )
            
            if not messages:
                return ""
            
            context_lines = []
            for msg in messages:
                role = "Usuario" if msg.role == "user" else "Minerva"
                context_lines.append(f"{role}: {msg.content}")
            
            return "\n".join(context_lines)
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo contexto: {e}")
            return ""
    
    def get_last_agent_used(
        self,
        conversation_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Obtiene el tipo de agente usado en la última respuesta.
        
        Args:
            conversation_id: ID de conversación
            
        Returns:
            Tipo de agente o None
        """
        try:
            if conversation_id is None:
                conversations = self.db_manager.get_active_conversations(limit=1)
                if not conversations:
                    return None
                conversation_id = conversations[0].id
            
            messages = self.db_manager.get_conversation_messages(
                conversation_id=conversation_id,
                limit=10
            )
            
            # Buscar último mensaje del asistente
            for message in reversed(messages):
                if message.role == 'assistant':
                    return message.agent_type
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo último agente: {e}")
            return None