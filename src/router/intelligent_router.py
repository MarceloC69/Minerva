"""
Router Inteligente de Minerva.
Decide qué agente usar según la consulta del usuario.
"""

from typing import Dict, Any, Optional
import logging

from src.agents import ConversationalAgent, KnowledgeAgent
from src.processing import DocumentIndexer


class IntelligentRouter:
    """
    Router que decide qué agente invocar según la consulta.
    
    Proceso:
    1. Analiza la consulta del usuario
    2. Busca PROACTIVAMENTE en Qdrant (siempre)
    3. Decide qué agente usar según relevancia del contexto
    4. Invoca el agente apropiado
    """
    
    def __init__(
        self,
        conversational_agent: ConversationalAgent,
        knowledge_agent: KnowledgeAgent,
        indexer: DocumentIndexer,
        knowledge_threshold: float = 0.4
    ):
        """
        Inicializa el router.
        
        Args:
            conversational_agent: Agente conversacional
            knowledge_agent: Agente de conocimiento
            indexer: Indexador de documentos
            knowledge_threshold: Umbral para usar agente de conocimiento
        """
        self.conversational_agent = conversational_agent
        self.knowledge_agent = knowledge_agent
        self.indexer = indexer
        self.knowledge_threshold = knowledge_threshold
        
        self.logger = logging.getLogger("minerva.router")
        self.logger.info("Router Inteligente inicializado")
    
    def _check_knowledge_base(
        self,
        query: str,
        collection_name: str = "knowledge_base"
    ) -> Dict[str, Any]:
        """
        Busca proactivamente en la base de conocimiento.
        
        Args:
            query: Consulta del usuario
            collection_name: Colección donde buscar
            
        Returns:
            Dict con resultados y decisión
        """
        try:
            results = self.indexer.search_documents(
                query=query,
                collection_name=collection_name,
                limit=3,
                score_threshold=0.3
            )
            
            if not results:
                return {
                    'has_knowledge': False,
                    'results': [],
                    'max_score': 0.0,
                    'decision': 'conversational'
                }
            
            max_score = max(r['score'] for r in results)
            
            # Decidir según score
            if max_score >= self.knowledge_threshold:
                decision = 'knowledge'
            else:
                decision = 'conversational'
            
            return {
                'has_knowledge': True,
                'results': results,
                'max_score': max_score,
                'decision': decision,
                'num_results': len(results)
            }
            
        except Exception as e:
            self.logger.error(f"Error buscando en knowledge base: {e}")
            return {
                'has_knowledge': False,
                'results': [],
                'max_score': 0.0,
                'decision': 'conversational'
            }
    
    def _detect_query_patterns(self, query: str) -> Dict[str, Any]:
        """
        Detecta patrones en la consulta para ayudar a la decisión.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Dict con patrones detectados
        """
        query_lower = query.lower()
        
        # Patrones que sugieren búsqueda de conocimiento
        knowledge_keywords = [
            'qué es', 'cómo funciona', 'explica', 'cuál es',
            'dime sobre', 'información sobre', 'características de',
            'tecnologías', 'arquitectura', 'documentación'
        ]
        
        # Patrones conversacionales
        conversational_keywords = [
            'hola', 'buenos días', 'gracias', 'ayuda',
            'puedes', 'podrías', 'me gustaría'
        ]
        
        has_knowledge_pattern = any(kw in query_lower for kw in knowledge_keywords)
        has_conversational_pattern = any(kw in query_lower for kw in conversational_keywords)
        
        # Detectar preguntas (termina con ?)
        is_question = query.strip().endswith('?')
        
        return {
            'has_knowledge_pattern': has_knowledge_pattern,
            'has_conversational_pattern': has_conversational_pattern,
            'is_question': is_question,
            'length': len(query)
        }
    
    def route(
        self,
        user_message: str,
        conversation_id: Optional[int] = None,
        collection_name: str = "knowledge_base",
        force_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Procesa una consulta y decide qué agente usar.
        
        Args:
            user_message: Mensaje del usuario
            conversation_id: ID de conversación (opcional)
            collection_name: Colección de documentos
            force_agent: Forzar un agente específico ('conversational' o 'knowledge')
            
        Returns:
            Dict con respuesta y metadata
        """
        self.logger.info(f"Routing consulta: '{user_message[:50]}...'")
        
        try:
            # Si se fuerza un agente específico
            if force_agent:
                self.logger.info(f"Agente forzado: {force_agent}")
                
                if force_agent == 'knowledge':
                    result = self.knowledge_agent.answer(
                        user_message=user_message,
                        conversation_id=conversation_id,
                        collection_name=collection_name
                    )
                    return {
                        'answer': result['answer'],
                        'agent_used': 'knowledge',
                        'confidence': result['confidence'],
                        'sources': result['sources'],
                        'routing_reason': 'forced'
                    }
                else:
                    answer = self.conversational_agent.chat(
                        user_message=user_message,
                        conversation_id=conversation_id
                    )
                    return {
                        'answer': answer,
                        'agent_used': 'conversational',
                        'routing_reason': 'forced'
                    }
            
            # 1. Buscar proactivamente en knowledge base
            kb_check = self._check_knowledge_base(user_message, collection_name)
            
            # 2. Detectar patrones en la consulta
            patterns = self._detect_query_patterns(user_message)
            
            # 3. Decidir agente
            # Prioridad 1: Knowledge base con score alto
            if kb_check['has_knowledge'] and kb_check['max_score'] >= self.knowledge_threshold:
                decision = 'knowledge'
                reason = f"Knowledge base match (score: {kb_check['max_score']:.2f})"
            
            # Prioridad 2: Patrones + algún resultado en KB
            elif patterns['has_knowledge_pattern'] and kb_check['has_knowledge']:
                decision = 'knowledge'
                reason = f"Knowledge pattern + results (score: {kb_check['max_score']:.2f})"
            
            # Prioridad 3: Conversacional por defecto
            else:
                decision = 'conversational'
                if kb_check['has_knowledge']:
                    reason = f"Low relevance (score: {kb_check['max_score']:.2f}), using conversational"
                else:
                    reason = "No knowledge base results, using conversational"
            
            self.logger.info(f"Decisión: {decision} - {reason}")
            
            # 4. Invocar agente seleccionado
            if decision == 'knowledge':
                result = self.knowledge_agent.answer(
                    user_message=user_message,
                    conversation_id=conversation_id,
                    collection_name=collection_name
                )
                
                return {
                    'answer': result['answer'],
                    'agent_used': 'knowledge',
                    'confidence': result['confidence'],
                    'sources': result.get('sources', []),
                    'num_sources': result.get('num_sources', 0),
                    'routing_reason': reason,
                    'kb_max_score': kb_check['max_score']
                }
            
            else:  # conversational
                # Si hay contexto relevante aunque no usemos knowledge agent,
                # podemos pasárselo al conversational
                context = None
                if kb_check['has_knowledge'] and kb_check['max_score'] > 0.3:
                    context = self.indexer.get_document_context(
                        query=user_message,
                        collection_name=collection_name,
                        max_chunks=1
                    )
                
                answer = self.conversational_agent.chat(
                    user_message=user_message,
                    context=context,
                    conversation_id=conversation_id
                )
                
                return {
                    'answer': answer,
                    'agent_used': 'conversational',
                    'routing_reason': reason,
                    'had_context': context is not None,
                    'kb_max_score': kb_check.get('max_score', 0.0)
                }
            
        except Exception as e:
            self.logger.error(f"Error en routing: {e}", exc_info=True)
            
            # Fallback: usar conversational
            try:
                answer = self.conversational_agent.chat(
                    user_message=user_message,
                    conversation_id=conversation_id
                )
                
                return {
                    'answer': answer,
                    'agent_used': 'conversational',
                    'routing_reason': f'error_fallback: {str(e)}',
                    'error': str(e)
                }
                
            except Exception as fallback_error:
                return {
                    'answer': "Lo siento, hubo un error procesando tu mensaje.",
                    'agent_used': 'none',
                    'routing_reason': 'critical_error',
                    'error': str(fallback_error)
                }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de los agentes.
        
        Returns:
            Dict con estadísticas
        """
        return {
            'conversational_agent': self.conversational_agent.get_stats(),
            'knowledge_agent': self.knowledge_agent.get_stats(),
            'threshold': self.knowledge_threshold
        }