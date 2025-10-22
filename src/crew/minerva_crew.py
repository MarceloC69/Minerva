# src/crew/minerva_crew.py - v6.0.0 - Con CrewAI real + mem0
"""
Coordinador principal de Minerva usando CrewAI.
Orquesta agentes con memoria persistente (mem0).
"""

from typing import Dict, Any, Optional
import logging

from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool

from src.memory.mem0_wrapper import Mem0Wrapper
from src.crew.tools.memory_search_tool import MemorySearchTool
from src.crew.tools.source_retrieval_tool import SourceRetrievalTool
from src.crew.tools.document_search_tool import DocumentSearchTool
from config.settings import settings


class MinervaCrew:
    """
    Crew principal de Minerva con CrewAI + mem0.
    
    Componentes:
    - mem0: Memoria persistente compartida
    - 3 Agentes CrewAI: Conversational, Knowledge, Web
    - Tools: MemorySearch, SourceRetrieval, DocumentSearch
    """
    
    def __init__(
        self,
        db_manager,
        indexer,
        web_search_service
    ):
        """
        Inicializa MinervaCrew.
        
        Args:
            db_manager: DatabaseManager para SQLite
            indexer: DocumentIndexer para RAG
            web_search_service: Servicio de búsqueda web
        """
        self.logger = logging.getLogger("minerva.crew")
        self.db_manager = db_manager
        self.indexer = indexer
        self.web_search = web_search_service
        
        # Inicializar mem0
        self.logger.info("🧠 Inicializando mem0...")
        self.mem0 = Mem0Wrapper(user_id="marcelo")
        
        # Inicializar Tools
        self.logger.info("🔧 Inicializando Tools...")
        self.memory_search_tool = MemorySearchTool(mem0_wrapper=self.mem0)
        self.source_retrieval_tool = SourceRetrievalTool(db_manager=db_manager)
        self.document_search_tool = DocumentSearchTool(indexer=indexer)
        
        # Inicializar Agentes
        self.logger.info("🤖 Inicializando Agentes CrewAI...")
        self._init_agents()
        
        # Crew (se crea por demanda según la query)
        self.crew = None
        
        self.logger.info("✅ MinervaCrew con CrewAI + mem0 inicializado")
    
    def _init_agents(self):
        """Inicializa los agentes de CrewAI."""
        
        # Configuración de LLM para Ollama
        from langchain_community.llms import Ollama
        llm = Ollama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.7
        )
        
        # === CONVERSATIONAL AGENT ===
        self.conversational_agent = Agent(
            role="Conversational Assistant",
            goal="Ayudar al usuario con conversaciones naturales, recordando información previa",
            backstory="""Eres Minerva, un asistente personal inteligente con memoria persistente.
            Recuerdas todas las conversaciones anteriores y usas esa información para dar respuestas
            personalizadas y contextualizadas. Siempre eres amable, clara y directa.""",
            tools=[self.memory_search_tool],
            llm=llm,
            verbose=True,
            allow_delegation=False
        )
        
        # === KNOWLEDGE AGENT ===
        self.knowledge_agent = Agent(
            role="Knowledge Specialist",
            goal="Responder preguntas usando documentos indexados con precisión",
            backstory="""Eres un especialista en extraer información de documentos técnicos.
            Tienes acceso a todos los documentos que el usuario ha subido (PDF, DOCX, etc.)
            y puedes buscar información específica en ellos. Siempre citas tus fuentes.""",
            tools=[self.document_search_tool],
            llm=llm,
            verbose=True,
            allow_delegation=False
        )
        
        # === WEB AGENT ===
        self.web_agent = Agent(
            role="Web Research Specialist",
            goal="Buscar información actualizada en internet cuando sea necesario",
            backstory="""Eres un investigador experto en búsqueda web.
            Tienes acceso a internet y puedes buscar información actualizada sobre
            noticias, clima, precios, eventos recientes, etc. Siempre proporcionas fuentes.""",
            tools=[],  # Web search se maneja custom por las limitaciones de la API
            llm=llm,
            verbose=True,
            allow_delegation=False
        )
        
        self.logger.info("✅ 3 Agentes CrewAI inicializados")
    
    def _classify_intent(self, query: str) -> str:
        """
        Clasifica la intención del usuario usando el LLM.
        
        Args:
            query: Query del usuario
            
        Returns:
            'conversation', 'knowledge', 'web', 'source_request'
        """
        try:
            # Cargar prompt de clasificación desde DB
            from src.database.prompt_manager import PromptManager
            pm = PromptManager(self.db_manager)
            
            classification_prompt_template = pm.get_active_prompt(
                agent_type='router',
                prompt_name='classification_prompt'
            )
            
            if not classification_prompt_template:
                self.logger.warning("No se encontró prompt de router, usando fallback")
                classification_prompt_template = """Clasifica: {query}
Categorías: conversation, knowledge, web, source_request
Categoría:"""
            
            # Construir prompt
            classification_prompt = classification_prompt_template.format(query=query)
            
            # Llamar a Ollama
            import requests
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": classification_prompt,
                    "temperature": 0.1,
                    "stream": False
                },
                timeout=10
            )
            
            response.raise_for_status()
            result = response.json()
            intent = result.get('response', '').strip().lower()
            
            # Validar
            valid_intents = ['conversation', 'knowledge', 'web', 'source_request']
            for valid in valid_intents:
                if valid in intent:
                    self.logger.info(f"🎯 Intención clasificada: {valid}")
                    return valid
            
            # Fallback
            self.logger.warning(f"Intención inválida '{intent}', usando 'conversation'")
            return 'conversation'
            
        except Exception as e:
            self.logger.error(f"Error clasificando intención: {e}")
            return 'conversation'
    
    def route(
        self,
        user_message: str,
        conversation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Procesa un mensaje del usuario.
        
        Args:
            user_message: Mensaje del usuario
            conversation_id: ID de conversación
            
        Returns:
            Dict con respuesta y metadata
        """
        try:
            self.logger.info(f"📨 Procesando: '{user_message[:50]}...'")
            
            # Clasificar intención
            intent = self._classify_intent(user_message)
            
            # Obtener contexto de mem0
            memory_context = self.mem0.get_relevant_context(user_message, limit=3)
            
            # Rutear según intención
            if intent == 'source_request':
                return self._handle_source_request(user_message, conversation_id)
            
            elif intent == 'web':
                return self._handle_web_search(user_message, conversation_id, memory_context)
            
            elif intent == 'knowledge':
                return self._handle_knowledge(user_message, conversation_id, memory_context)
            
            else:  # conversation
                return self._handle_conversation(user_message, conversation_id, memory_context)
        
        except Exception as e:
            self.logger.error(f"❌ Error en route: {e}", exc_info=True)
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
        self.logger.info("📋 Recuperando fuentes...")
        
        result = self.source_retrieval_tool._run(conversation_id=conversation_id)
        
        return {
            'answer': result,
            'agent_used': 'source_retrieval',
            'confidence': 'Alta',
            'sources': []
        }
    
    def _handle_conversation(
        self,
        user_message: str,
        conversation_id: Optional[int],
        memory_context: str
    ) -> Dict[str, Any]:
        """Maneja conversación general con mem0."""
        self.logger.info("💬 Conversational Agent con mem0...")
        
        # Crear Task
        task = Task(
            description=f"""Responde al usuario de forma natural y personalizada.

Contexto de memoria:
{memory_context if memory_context else "No hay contexto previo relevante"}

Mensaje del usuario: {user_message}

IMPORTANTE:
- Usa el contexto de memoria cuando sea relevante
- Responde de forma directa y natural
- No menciones que tienes memoria o contexto
- Si no sabes algo, di "No lo sé"
""",
            agent=self.conversational_agent,
            expected_output="Respuesta natural y contextualizada al usuario"
        )
        
        # Ejecutar con Crew
        crew = Crew(
            agents=[self.conversational_agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False
        )
        
        result = crew.kickoff()
        answer = str(result)
        
        # Actualizar mem0 con el intercambio
        self.mem0.update_from_conversation(
            user_message=user_message,
            assistant_message=answer,
            conversation_id=conversation_id
        )
        
        # Guardar en DB
        if self.db_manager and conversation_id:
            self.db_manager.add_message(
                conversation_id=conversation_id,
                role='user',
                content=user_message
            )
            self.db_manager.add_message(
                conversation_id=conversation_id,
                role='assistant',
                content=answer,
                agent_type='conversational'
            )
        
        return {
            'answer': answer,
            'agent_used': 'conversational',
            'confidence': 'Alta',
            'sources': []
        }
    
    def _handle_knowledge(
        self,
        user_message: str,
        conversation_id: Optional[int],
        memory_context: str
    ) -> Dict[str, Any]:
        """Maneja búsqueda en documentos."""
        self.logger.info("📚 Knowledge Agent...")
        
        # Crear Task
        task = Task(
            description=f"""Busca información en los documentos indexados.

Contexto de memoria (usa si es relevante):
{memory_context if memory_context else "Sin contexto previo"}

Pregunta: {user_message}

IMPORTANTE:
- Busca SOLO en documentos usando la tool
- Cita las fuentes
- Si no encuentras información, dilo claramente
""",
            agent=self.knowledge_agent,
            expected_output="Respuesta basada en documentos con citas"
        )
        
        # Ejecutar
        crew = Crew(
            agents=[self.knowledge_agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False
        )
        
        result = crew.kickoff()
        answer = str(result)
        
        # Guardar en DB
        if self.db_manager and conversation_id:
            self.db_manager.add_message(
                conversation_id=conversation_id,
                role='user',
                content=user_message
            )
            self.db_manager.add_message(
                conversation_id=conversation_id,
                role='assistant',
                content=answer,
                agent_type='knowledge'
            )
        
        return {
            'answer': answer,
            'agent_used': 'knowledge',
            'confidence': 'Alta',
            'sources': []
        }
    
    def _handle_web_search(
        self,
        user_message: str,
        conversation_id: Optional[int],
        memory_context: str
    ) -> Dict[str, Any]:
        """Maneja búsqueda web."""
        self.logger.info("🌐 Web Agent...")
        
        # Búsqueda web (custom, no via CrewAI tool por limitaciones)
        try:
            from src.tools.web_search import WebSearchTool
            from src.tools.date_normalizer import DateNormalizer
            
            date_normalizer = DateNormalizer()
            normalized_query = date_normalizer.normalize(user_message)
            
            web_tool = WebSearchTool(api_key=settings.SERPER_API_KEY)
            search_results = web_tool.search(normalized_query, num_results=5)
            
            if not search_results:
                return {
                    'answer': "No encontré resultados en la web.",
                    'agent_used': 'web',
                    'confidence': 'Baja',
                    'sources': []
                }
            
            # Crear Task para sintetizar
            task = Task(
                description=f"""Sintetiza información de búsqueda web.

Resultados:
{search_results}

Pregunta original: {user_message}

IMPORTANTE:
- Sintetiza la información más relevante
- No inventes datos
- Sé conciso
""",
                agent=self.web_agent,
                expected_output="Síntesis de resultados web"
            )
            
            crew = Crew(
                agents=[self.web_agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False
            )
            
            result = crew.kickoff()
            answer = str(result)
            
            # Extraer fuentes
            sources = []
            for res in search_results.get('organic', [])[:3]:
                sources.append({
                    'title': res.get('title', ''),
                    'url': res.get('link', ''),
                    'snippet': res.get('snippet', '')
                })
            
            # Guardar en DB
            if self.db_manager and conversation_id:
                self.db_manager.add_message(
                    conversation_id=conversation_id,
                    role='user',
                    content=user_message
                )
                self.db_manager.add_message(
                    conversation_id=conversation_id,
                    role='assistant',
                    content=answer,
                    agent_type='web',
                    metadata={'sources': sources}
                )
            
            return {
                'answer': answer,
                'agent_used': 'web',
                'confidence': 'Alta',
                'sources': sources
            }
            
        except Exception as e:
            self.logger.error(f"Error en web search: {e}")
            return {
                'answer': f"Error en búsqueda web: {str(e)}",
                'agent_used': 'web',
                'confidence': 'Baja',
                'sources': []
            }