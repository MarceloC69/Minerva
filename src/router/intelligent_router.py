# src/router/intelligent_router.py - v2.2.0
"""
Router inteligente que decide qué agente usar según la consulta del usuario.
Ahora con WebAgent usando Crawl4AI (mucho más robusto).
"""

from typing import Dict, Any, Optional
import logging
import re

from src.agents.conversational import ConversationalAgent
from src.agents.knowledge import KnowledgeAgent
from src.agents.web import WebAgent


class IntelligentRouter:
    """
    Router que analiza queries y decide qué agente usar.
    
    Agentes disponibles:
    - Conversational: Chat general, preguntas personales
    - Knowledge: Consultas sobre documentos indexados
    - Web: Búsqueda de información actualizada (con Crawl4AI)
    """
    
    def __init__(
        self,
        conversational_agent: ConversationalAgent,
        knowledge_agent: KnowledgeAgent,
        indexer,
        knowledge_threshold: float = 0.5,
        web_agent: Optional[WebAgent] = None
    ):
        """
        Inicializa el router con los agentes disponibles.
        
        Args:
            conversational_agent: Agente conversacional
            knowledge_agent: Agente de conocimiento/RAG
            indexer: Indexer de documentos
            knowledge_threshold: Umbral para usar knowledge agent
            web_agent: Agente web (se crea si no se proporciona)
        """
        self.conversational_agent = conversational_agent
        self.knowledge_agent = knowledge_agent
        self.web_agent = web_agent or WebAgent(
            model_name="phi3:latest",  # Cambiado de phi3:mini
            temperature=0.3,
            db_manager=conversational_agent.db_manager
        )
        self.indexer = indexer
        self.threshold = knowledge_threshold
        self.logger = logging.getLogger("minerva.router")
        
        # Web habilitado con Crawl4AI
        self.web_enabled = True
        self.logger.info("✅ WebAgent habilitado con Crawl4AI")
    
    def _needs_web_search(self, query: str) -> bool:
        """
        Detecta si una query necesita búsqueda web.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            True si necesita búsqueda web
        """
        query_lower = query.lower()
        
        # Palabras clave temporales
        time_keywords = [
            'hoy', 'ahora', 'actual', 'últimas', 'reciente',
            'este año', '2025', 'esta semana'
        ]
        
        # Temas actualizables
        current_topics = [
            'clima', 'weather', 'temperatura', 'pronóstico',
            'precio', 'cotización', 'dólar',
            'noticia', 'news', 'novedades'
        ]
        
        # Verificar keywords
        if any(keyword in query_lower for keyword in time_keywords):
            return True
        
        if any(topic in query_lower for topic in current_topics):
            return True
        
        return False
    
    def _is_news_query(self, query: str) -> bool:
        """Detecta si es query de noticias."""
        query_lower = query.lower()
        news_keywords = ['noticia', 'news', 'últimas', 'novedades']
        return any(keyword in query_lower for keyword in news_keywords)
    
    def route(
        self,
        user_message: str,
        conversation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Rutea el mensaje al agente apropiado.
        
        Lógica:
        1. ¿Necesita info actualizada? → WebAgent
        2. ¿Hay documentos relevantes? → KnowledgeAgent
        3. Sino → ConversationalAgent
        """
        self.logger.info(f"🎯 Router recibió: '{user_message[:50]}...'")
        
        try:
            # 1. Verificar si necesita web
            if self.web_enabled and self._needs_web_search(user_message):
                self.logger.info("🌐 Decisión: WebAgent (info actualizada)")
                
                search_type = "news" if self._is_news_query(user_message) else "general"
                
                result = self.web_agent.search_and_answer(
                    query=user_message,
                    search_type=search_type,
                    conversation_id=conversation_id
                )
                
                return {
                    'answer': result['answer'],
                    'agent_used': 'web',
                    'confidence': 'Alta',
                    'sources': result.get('sources', []),
                    'search_type': search_type
                }
            
            # 2. Verificar documentos
            has_documents = self.indexer.has_documents()
            
            if has_documents:
                # Buscar documentos relevantes
                search_results = self.indexer.search(user_message, top_k=3)
                
                if search_results and len(search_results) > 0:
                    best_score = search_results[0]['score']
                    
                    if best_score >= self.threshold:
                        self.logger.info(
                            f"📚 Decisión: KnowledgeAgent (score={best_score:.3f})"
                        )
                        
                        response = self.knowledge_agent.answer_with_context(
                            question=user_message,
                            conversation_id=conversation_id
                        )
                        
                        return {
                            'answer': response['answer'],
                            'agent_used': 'knowledge',
                            'confidence': response.get('confidence', 'Media'),
                            'sources': response.get('sources', []),
                            'search_score': best_score
                        }
                    else:
                        self.logger.info(
                            f"⚠️ Documentos pero score bajo ({best_score:.3f})"
                        )
            
            # 3. Conversational por defecto
            self.logger.info("💬 Decisión: ConversationalAgent")
            
            response = self.conversational_agent.chat(
                user_message=user_message,
                conversation_id=conversation_id
            )
            
            return {
                'answer': response,
                'agent_used': 'conversational',
                'confidence': 'Alta',
                'sources': []
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error en routing: {e}", exc_info=True)
            
            # Fallback al agente conversacional
            try:
                response = self.conversational_agent.chat(
                    user_message=user_message,
                    conversation_id=conversation_id
                )
                return {
                    'answer': response,
                    'agent_used': 'conversational',
                    'confidence': 'Media',
                    'sources': [],
                    'error': str(e)
                }
            except Exception as e2:
                return {
                    'answer': f"Lo siento, ocurrió un error al procesar tu mensaje: {str(e2)}",
                    'agent_used': 'error',
                    'confidence': 'Baja',
                    'sources': [],
                    'error': str(e2)
                }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del router.
        
        Returns:
            Diccionario con estadísticas
        """
        return {
            'agents_available': ['conversational', 'knowledge', 'web'],
            'has_documents': self.indexer.has_documents(),
            'knowledge_threshold': self.threshold,
            'web_agent_enabled': True  # Habilitado con Crawl4AI
        }


# Para testing directo
if __name__ == "__main__":
    print("Router v2.1.0 - Web temporalmente deshabilitado")
    print("Agentes activos: Conversational + Knowledge (RAG)")