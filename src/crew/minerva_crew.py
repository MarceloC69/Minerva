# src/crew/minerva_crew.py - v3.0.0 - Router inteligente con LLM
"""
Coordinador CrewAI de Minerva CON MEMORIA PERSISTENTE.
Orquesta todos los agentes y gestiona la memoria.
Router inteligente usando LLM para clasificación (sin keywords hardcodeadas).
"""

from typing import Dict, Any, Optional
import logging
import requests

from src.agents.conversational import ConversationalAgent
from src.agents.knowledge import KnowledgeAgent
from src.agents.web import WebAgent
from .agents.memory_agent import MemoryAgent


class MinervaCrew:
    """
    Crew principal de Minerva que coordina todos los agentes.
    
    Agentes:
    - MemoryAgent: Busca en DB (conversaciones, fuentes, metadata)
    - ConversationalAgent: Chat general CON MEMORIA PERSISTENTE
    - KnowledgeAgent: RAG/documentos
    - WebAgent: Búsqueda internet
    
    Router: Usa LLM para clasificar intención (sin keywords)
    """
    
    def __init__(
        self,
        conversational_agent: ConversationalAgent,
        knowledge_agent: KnowledgeAgent,
        web_agent: WebAgent,
        db_manager,
        indexer,
        memory_service=None
    ):
        """
        Inicializa el crew de Minerva.
        
        Args:
            conversational_agent: Agente conversacional existente
            knowledge_agent: Agente de conocimiento existente
            web_agent: Agente web existente
            db_manager: Database manager para memoria
            indexer: Document indexer
            memory_service: Servicio de memoria persistente (deprecado)
        """
        self.logger = logging.getLogger("minerva.crew")
        
        # Agentes existentes
        self.conversational_agent = conversational_agent
        self.knowledge_agent = knowledge_agent
        self.web_agent = web_agent
        self.db_manager = db_manager
        self.indexer = indexer
        
        # Servicio de memoria persistente (deprecado pero mantenido para compatibilidad)
        self.memory_service = memory_service
        if self.memory_service:
            self.logger.info("✅ MemoryService integrado en MinervaCrew")
        else:
            self.logger.warning("⚠️ MinervaCrew sin MemoryService")
        
        # Crear agente de memoria (para búsquedas en DB)
        self.memory_agent = MemoryAgent(
            db_manager=db_manager,
            logger=self.logger
        )
        
        # Cargar prompt de clasificación desde DB
        self._load_router_prompt()
        
        self.logger.info("✅ MinervaCrew inicializado con router inteligente (LLM)")
    
    def _load_router_prompt(self):
        """Carga el prompt de clasificación desde la DB."""
        try:
            from src.database.prompt_manager import PromptManager
            pm = PromptManager(self.db_manager)
            
            self.classification_prompt_template = pm.get_active_prompt(
                agent_type='router',
                prompt_name='classification_prompt'
            )
            
            if not self.classification_prompt_template:
                self.logger.warning("⚠️ No se encontró prompt de router en DB, usando fallback")
                # Fallback temporal si no existe el prompt
                self.classification_prompt_template = """Clasifica esta pregunta en UNA categoría:

CATEGORÍAS:
1. source_request - Pregunta por fuentes/links
2. web_search - Necesita info actualizada de internet
3. knowledge - Pregunta sobre documentos técnicos
4. conversation - Todo lo demás (preguntas personales, chat general)

PREGUNTA: {query}

Responde SOLO con el nombre de la categoría.
CATEGORÍA:"""
            else:
                self.logger.info("✅ Prompt de router cargado desde DB")
                
        except Exception as e:
            self.logger.error(f"Error cargando prompt router: {e}")
            # Fallback básico
            self.classification_prompt_template = "Clasifica: {query}\nCategoría:"
    
    def _detect_intent_with_llm(self, query: str) -> str:
        """
        Usa el LLM para detectar intención (NO keywords).
        
        Args:
            query: Query del usuario
            
        Returns:
            Intención detectada: 'source_request', 'web_search', 'knowledge', 'conversation'
        """
        
        # Construir prompt con el template desde DB
        classification_prompt = self.classification_prompt_template.format(query=query)
        
        try:
            response = requests.post(
                f"{self.conversational_agent.base_url}/api/generate",
                json={
                    "model": self.conversational_agent.model_name,
                    "prompt": classification_prompt,
                    "temperature": 0.1,  # Muy determinista
                    "stream": False
                },
                timeout=10
            )
            
            response.raise_for_status()
            result = response.json()
            intent = result.get('response', '').strip().lower()
            
            # Validar que sea una categoría válida
            valid_intents = ['source_request', 'web_search', 'knowledge', 'conversation']
            
            # Limpiar la respuesta (a veces el LLM agrega texto extra)
            for valid_intent in valid_intents:
                if valid_intent in intent:
                    intent = valid_intent
                    break
            
            if intent not in valid_intents:
                self.logger.warning(f"Intent inválido '{intent}', usando 'conversation'")
                intent = 'conversation'
            
            self.logger.info(f"🤖 LLM clasificó como: {intent}")
            return intent
            
        except Exception as e:
            self.logger.error(f"Error en clasificación LLM: {e}")
            return self._detect_intent_fallback(query)
    
    def _detect_intent_fallback(self, query: str) -> str:
        """
        Fallback simple si falla el LLM.
        SOLO para casos de emergencia, con keywords mínimas.
        """
        query_lower = query.lower()
        
        # Solo los casos MÁS obvios
        if 'fuente' in query_lower or 'link' in query_lower or 'url' in query_lower:
            return 'source_request'
        
        if any(word in query_lower for word in ['hoy', 'ahora', 'clima', 'temperatura', 'noticia']):
            return 'web_search'
        
        # Verificar si hay docs antes de usar knowledge
        if self.indexer.has_documents():
            try:
                results = self.indexer.search_documents(
                    query=query,
                    collection_name='knowledge_base',
                    limit=1,
                    score_threshold=0.6
                )
                if results:
                    return 'knowledge'
            except:
                pass
        
        # Por defecto: conversación
        return 'conversation'
    
    def route(
        self,
        user_message: str,
        conversation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Rutea el mensaje al agente apropiado usando LLM.
        
        Args:
            user_message: Mensaje del usuario
            conversation_id: ID de conversación
            
        Returns:
            Diccionario con respuesta y metadata
        """
        try:
            self.logger.info(f"🎯 MinervaCrew procesando: '{user_message[:50]}...'")
            
            # Detectar intención CON LLM
            intent = self._detect_intent_with_llm(user_message)
            self.logger.info(f"🔍 Intención detectada: {intent}")
            
            # Rutear según intención
            if intent == 'source_request':
                return self._handle_source_request(user_message, conversation_id)
            
            elif intent == 'web_search':
                return self._handle_web_search(user_message, conversation_id)
            
            elif intent == 'knowledge':
                return self._handle_knowledge_query(user_message, conversation_id)
            
            else:  # 'conversation' (incluye preguntas personales)
                return self._handle_conversation(user_message, conversation_id)
        
        except Exception as e:
            self.logger.error(f"❌ Error en crew: {e}", exc_info=True)
            return {
                'answer': f"Ocurrió un error: {str(e)}",
                'agent_used': 'error',
                'confidence': 'Baja',
                'sources': []
            }
    
    def _handle_source_request(
        self,
        user_message: str,
        conversation_id: Optional[int]
    ) -> Dict[str, Any]:
        """Maneja solicitudes de fuentes."""
        self.logger.info("📋 Buscando fuentes del último mensaje...")
        
        result = self.memory_agent.get_last_sources(conversation_id)
        
        if result['found']:
            sources = result['sources']
            
            if sources:
                answer = "Las fuentes que usé fueron:\n\n"
                for i, source in enumerate(sources, 1):
                    answer += f"{i}. **{source['title']}**\n"
                    answer += f"   {source['url']}\n\n"
            else:
                answer = "No encontré fuentes en mi última respuesta. Es posible que haya usado mi conocimiento interno."
            
            return {
                'answer': answer,
                'agent_used': 'memory',
                'confidence': 'Alta',
                'sources': sources
            }
        else:
            return {
                'answer': "No tengo fuentes de mi última respuesta en la memoria.",
                'agent_used': 'memory',
                'confidence': 'Baja',
                'sources': []
            }
    
    def _handle_web_search(
        self,
        user_message: str,
        conversation_id: Optional[int]
    ) -> Dict[str, Any]:
        """Maneja búsquedas web."""
        self.logger.info("🌐 Delegando a WebAgent...")
        
        result = self.web_agent.search_and_answer(
            query=user_message,
            conversation_id=conversation_id
        )
        
        return {
            'answer': result['answer'],
            'agent_used': 'web',
            'confidence': 'Alta' if result['success'] else 'Baja',
            'sources': result.get('sources', [])
        }
    
    def _handle_knowledge_query(
        self,
        user_message: str,
        conversation_id: Optional[int]
    ) -> Dict[str, Any]:
        """Maneja queries sobre documentos."""
        self.logger.info("📚 Delegando a KnowledgeAgent...")
        
        result = self.knowledge_agent.answer(
            user_message=user_message,
            conversation_id=conversation_id
        )
        
        return {
            'answer': result['answer'],
            'agent_used': 'knowledge',
            'confidence': result['confidence'],
            'sources': result.get('sources', [])
        }
    
    def _handle_conversation(
        self,
        user_message: str,
        conversation_id: Optional[int]
    ) -> Dict[str, Any]:
        """
        Maneja conversación general CON MEMORIA PERSISTENTE.
        Incluye preguntas personales sobre el usuario.
        """
        self.logger.info("💬 Delegando a ConversationalAgent (con memoria)...")
        
        response = self.conversational_agent.chat(
            user_message=user_message,
            conversation_id=conversation_id
        )
        
        return {
            'answer': response,
            'agent_used': 'conversational',
            'confidence': 'Alta',
            'sources': [],
            'had_memory': True
        }