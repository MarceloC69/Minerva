# src/crew/minerva_crew.py
"""
MinervaCrew - Coordinador principal con routing inteligente por LLM
Lee classification_prompt desde DB
"""

import logging
from typing import Dict, Any, Optional, List
import ollama

from config.settings import settings
from src.database.manager import DatabaseManager
from src.database.prompt_manager import PromptManager
from src.processing.indexer import DocumentIndexer

logger = logging.getLogger('minerva.crew')


class MinervaCrew:
    """
    Coordinador principal con routing inteligente.
    Usa LLM + classification_prompt de DB para clasificar intención.
    """
    
    def __init__(
        self,
        conversational_agent,
        knowledge_agent,
        web_agent,
        db_manager: DatabaseManager,
        indexer: DocumentIndexer,
        memory_service=None
    ):
        """Inicializa MinervaCrew."""
        logger.info("🚀 Inicializando MinervaCrew...")
        
        self.db_manager = db_manager
        self.indexer = indexer
        self.prompt_manager = PromptManager(db_manager)
        self.memory_service = memory_service
        
        # Agentes
        self.conversational_agent = conversational_agent
        self.knowledge_agent = knowledge_agent
        self.web_agent = web_agent
        
        # Cargar classification_prompt desde DB
        self._load_classification_prompt()
        
        logger.info("✅ MinervaCrew inicializado correctamente")
    
    def _load_classification_prompt(self):
        """Carga classification_prompt desde la base de datos."""
        try:
            self.classification_prompt = self.prompt_manager.get_active_prompt(
                agent_type='router',
                prompt_name='classification_prompt'
            )
            
            if not self.classification_prompt:
                logger.error("❌ CRITICAL: classification_prompt no encontrado en DB")
                raise Exception("classification_prompt no encontrado en DB")
            
            logger.info("✅ classification_prompt cargado desde DB")
            
        except Exception as e:
            logger.error(f"❌ Error cargando classification_prompt: {e}")
            raise
    
    def _classify_intent(self, query: str) -> str:
        """
        Clasifica intención usando LLM + prompt de DB.
        
        Args:
            query: Query del usuario
            
        Returns:
            'personal', 'source_request', 'web_search', 'knowledge', 'conversation'
        """
        try:
            # Formatear prompt con la query
            prompt = self.classification_prompt.format(query=query)
            
            # Llamar a LLM
            response = ollama.chat(
                model=settings.OLLAMA_MODEL,
                messages=[
                    {
                        'role': 'system',
                        'content': 'Eres un clasificador de intenciones. Respondes con UNA sola palabra.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                options={'temperature': 0.1}
            )
            
            intent = response['message']['content'].strip().lower()
            
            # Validar respuesta
            valid_intents = ['personal', 'source_request', 'web_search', 'knowledge', 'conversation']
            
            if intent not in valid_intents:
                # Mapeo de sinónimos comunes
                intent_map = {
                    'personal_question': 'personal',
                    'sources': 'source_request',
                    'source': 'source_request',
                    'web': 'web_search',
                    'search': 'web_search',
                    'docs': 'knowledge',
                    'chat': 'conversation',
                    'general': 'conversation'
                }
                intent = intent_map.get(intent, 'conversation')
            
            return intent
            
        except Exception as e:
            logger.error(f"❌ Error clasificando intención: {e}")
            return 'conversation'
    
    def route(self, user_message: str, conversation_id: int) -> Dict[str, Any]:
        """
        Enruta query del usuario al agente apropiado.
        
        Args:
            user_message: Mensaje del usuario
            conversation_id: ID de la conversación activa
        
        Returns:
            Dict con respuesta y metadata
        """
        logger.info(f"🔀 Routing query: '{user_message[:50]}...'")
        
        try:
            # 1. Clasificar intención con LLM
            intent = self._classify_intent(user_message)
            logger.info(f"📍 Intención clasificada: {intent}")
            
            # 2. Enrutar según intención
            if intent == 'personal':
                return self._handle_personal(user_message, conversation_id)
            
            elif intent == 'source_request':
                return self._handle_source_request(user_message, conversation_id)
            
            elif intent == 'web_search':
                return self._handle_web_search(user_message, conversation_id)
            
            elif intent == 'knowledge':
                return self._handle_knowledge(user_message, conversation_id)
            
            else:  # conversation
                return self._handle_conversation(user_message, conversation_id)
        
        except Exception as e:
            logger.error(f"❌ Error en routing: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'answer': f"❌ Error: {str(e)}",
                'agent': 'error',
                'confidence': 0.0,
                'sources': []
            }
    
    def _handle_personal(self, query: str, conversation_id: int) -> Dict[str, Any]:
        """
        Maneja afirmaciones personales.
        """
        logger.info("👤 Procesando afirmación personal...")
        
        try:
            # Responder con conversational agent
            # (el guardado en mem0 se hace automáticamente en conversational_agent.chat)
            response = self.conversational_agent.chat(
                user_message=query,
                conversation_id=conversation_id
            )
            
            return {
                'answer': response,
                'agent': 'personal',
                'confidence': 0.9,
                'sources': []
            }
            
        except Exception as e:
            logger.error(f"Error en personal: {e}")
            return {
                'answer': f"❌ Error: {str(e)}",
                'agent': 'error',
                'confidence': 0.0,
                'sources': []
            }
    
    def _handle_source_request(self, query: str, conversation_id: int) -> Dict[str, Any]:
        """Maneja pedidos de fuentes."""
        logger.info("🔗 Procesando pedido de fuentes...")
        
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT metadata FROM messages 
                WHERE conversation_id = ? 
                AND role = 'assistant'
                AND metadata IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT 1
            """, (conversation_id,))
            
            result = cursor.fetchone()
            
            if result and result[0]:
                import json
                metadata = json.loads(result[0])
                sources = metadata.get('sources', [])
                
                if sources:
                    answer = "📚 **Fuentes de mi última respuesta:**\n\n"
                    for i, source in enumerate(sources, 1):
                        title = source.get('title', 'Sin título')
                        url = source.get('link', source.get('url', '#'))
                        answer += f"{i}. [{title}]({url})\n"
                    
                    return {
                        'answer': answer,
                        'agent': 'source_retrieval',
                        'confidence': 1.0,
                        'sources': sources
                    }
            
            return {
                'answer': "No encontré fuentes en mi última respuesta.",
                'agent': 'source_retrieval',
                'confidence': 0.5,
                'sources': []
            }
            
        except Exception as e:
            logger.error(f"Error recuperando fuentes: {e}")
            return {
                'answer': f"❌ Error: {str(e)}",
                'agent': 'error',
                'confidence': 0.0,
                'sources': []
            }
    
    def _handle_web_search(self, query: str, conversation_id: int) -> Dict[str, Any]:
        """Delega a WebAgent."""
        logger.info("🌐 Delegando a WebAgent...")
        
        try:
            result = self.web_agent.search_and_answer(
                query=query,
                search_type="general",
                conversation_id=conversation_id
            )
            
            return {
                'answer': result.get('answer', ''),
                'agent': 'web',
                'confidence': 0.9 if result.get('success') else 0.3,
                'sources': result.get('sources', [])
            }
        except Exception as e:
            logger.error(f"Error en web search: {e}")
            return {
                'answer': f"❌ Error: {str(e)}",
                'agent': 'error',
                'confidence': 0.0,
                'sources': []
            }
    
    def _handle_knowledge(self, query: str, conversation_id: int) -> Dict[str, Any]:
        """Delega a KnowledgeAgent."""
        logger.info("📚 Delegando a KnowledgeAgent...")
        
        try:
            result = self.knowledge_agent.answer(
                user_message=query,
                conversation_id=conversation_id
            )
            
            return {
                'answer': result.get('answer', ''),
                'agent': 'knowledge',
                'confidence': result.get('confidence', 'Media'),
                'sources': result.get('sources', [])
            }
        except Exception as e:
            logger.error(f"Error en knowledge: {e}")
            return {
                'answer': f"❌ Error: {str(e)}",
                'agent': 'error',
                'confidence': 0.0,
                'sources': []
            }
    
    def _handle_conversation(self, query: str, conversation_id: int) -> Dict[str, Any]:
        """Delega a ConversationalAgent."""
        logger.info("💬 Delegando a ConversationalAgent...")
        
        try:
            response = self.conversational_agent.chat(
                user_message=query,
                conversation_id=conversation_id
            )
            
            return {
                'answer': response,
                'agent': 'conversational',
                'confidence': 0.8,
                'sources': []
            }
        except Exception as e:
            logger.error(f"Error en conversation: {e}")
            return {
                'answer': f"❌ Error: {str(e)}",
                'agent': 'error',
                'confidence': 0.0,
                'sources': []
            }
    
    def get_conversation_history(self, conversation_id: int, limit: int = 10) -> List[Dict]:
        """Obtiene historial de conversación."""
        try:
            return self.db_manager.get_conversation_messages(conversation_id, limit)
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            return []