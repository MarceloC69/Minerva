# src/agents/knowledge.py
"""
Agente de conocimiento de Minerva.
Responde preguntas usando documentos indexados (RAG).
"""

from typing import Optional, Dict, Any
from pathlib import Path
import requests
import time

from .base_agent import BaseAgent, AgentExecutionError
from config.prompts import get_agent_config
from config.settings import settings


class KnowledgeAgent(BaseAgent):
    """
    Agente especializado en responder usando documentos.
    
    Características:
    - Búsqueda semántica en documentos indexados
    - Respuestas con citas de fuentes
    - Indica nivel de confianza
    - Usa RAG (Retrieval Augmented Generation)
    """
    
    def __init__(
        self,
        model_name: str = "phi3",
        temperature: float = 0.3,  # Más determinista para conocimiento
        log_dir: Optional[Path] = None,
        db_manager = None,
        indexer = None
    ):
        """
        Inicializa el agente de conocimiento.
        
        Args:
            model_name: Nombre del modelo de Ollama
            temperature: Temperatura (baja para respuestas más precisas)
            log_dir: Directorio para logs
            db_manager: Instancia de DatabaseManager (opcional)
            indexer: Instancia de DocumentIndexer (requerido)
        """
        super().__init__(
            name="knowledge_agent",
            agent_type="knowledge",
            log_dir=log_dir
        )
        
        self.model_name = model_name
        self.temperature = temperature
        self.base_url = settings.OLLAMA_BASE_URL
        self.db_manager = db_manager
        self.indexer = indexer
        
        if not self.indexer:
            raise AgentExecutionError("KnowledgeAgent requiere un DocumentIndexer")
        
        # Obtener configuración de prompts
        self.config = get_agent_config('knowledge')
        
        # Verificar conexión con Ollama
        try:
            self._verify_connection()
            self.logger.info(f"LLM configurado: {model_name}")
        except Exception as e:
            self.logger.error(f"Error configurando LLM: {e}")
            raise AgentExecutionError(f"No se pudo conectar a Ollama: {e}")
    
    def _verify_connection(self) -> None:
        """Verifica que Ollama esté accesible."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
        except Exception as e:
            raise AgentExecutionError(f"Ollama no está accesible: {e}")
    
    def _assess_confidence(self, results: list, query: str) -> str:
        """
        Evalúa el nivel de confianza basado en los resultados.
        
        Args:
            results: Resultados de búsqueda
            query: Consulta original
            
        Returns:
            'Alta', 'Media' o 'Baja'
        """
        if not results:
            return 'Baja'
        
        avg_score = sum(r['score'] for r in results) / len(results)
        
        if avg_score >= 0.7 and len(results) >= 2:
            return 'Alta'
        elif avg_score >= 0.5 or len(results) >= 1:
            return 'Media'
        else:
            return 'Baja'
    
    def _build_rag_prompt(
        self,
        user_message: str,
        context: str,
        confidence: str
    ) -> str:
        """
        Construye el prompt para RAG.
        
        Args:
            user_message: Pregunta del usuario
            context: Contexto recuperado de documentos
            confidence: Nivel de confianza
            
        Returns:
            Prompt completo
        """
        system_prompt = f"""{self.config['role']}

**Tu proceso:**
1. Analiza el contexto proporcionado de los documentos
2. Responde la pregunta basándote en ese contexto
3. Cita las fuentes cuando sea relevante
4. Si el contexto no es suficiente, indícalo claramente

**Nivel de confianza en el contexto: {confidence}**

**IMPORTANTE:**
- Si la información está en el contexto, úsala y cita la fuente
- Si el contexto no tiene la información, admite que no la tienes
- No inventes información que no esté en el contexto
"""
        
        prompt = f"""{system_prompt}

===== CONTEXTO DE DOCUMENTOS =====
{context}
===== FIN DEL CONTEXTO =====

Usuario: {user_message}

Minerva (basándome en los documentos):"""
        
        return prompt
    
    def answer(
        self,
        user_message: str,
        conversation_id: Optional[int] = None,
        collection_name: str = "knowledge_base",
        max_context_chunks: int = 3
    ) -> Dict[str, Any]:
        """
        Responde una pregunta usando documentos.
        
        Args:
            user_message: Pregunta del usuario
            conversation_id: ID de conversación en DB (opcional)
            collection_name: Colección de documentos donde buscar
            max_context_chunks: Máximo de chunks a usar como contexto
            
        Returns:
            Dict con respuesta, fuentes y nivel de confianza
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Buscando conocimiento para: {user_message[:100]}...")
            
            # Guardar mensaje del usuario en DB
            if self.db_manager and conversation_id:
                self.db_manager.add_message(
                    conversation_id=conversation_id,
                    role='user',
                    content=user_message
                )
            
            # 1. Buscar contexto relevante
            results = self.indexer.search_documents(
                query=user_message,
                collection_name=collection_name,
                limit=max_context_chunks,
                score_threshold=0.3
            )
            
            self.logger.info(f"Encontrados {len(results)} chunks relevantes")
            
            # 2. Evaluar confianza
            confidence = self._assess_confidence(results, user_message)
            
            # 3. Si no hay contexto suficiente
            if not results or confidence == 'Baja':
                no_context_response = (
                    "No encontré información relevante en mis documentos sobre eso. "
                    "¿Podrías reformular la pregunta o proporcionar más contexto?"
                )
                
                if self.db_manager and conversation_id:
                    self.db_manager.add_message(
                        conversation_id=conversation_id,
                        role='assistant',
                        content=no_context_response,
                        agent_type=self.agent_type,
                        had_context=False
                    )
                
                return {
                    'answer': no_context_response,
                    'confidence': 'Baja',
                    'sources': [],
                    'num_sources': 0
                }
            
            # 4. Construir contexto
            context = self.indexer.get_document_context(
                query=user_message,
                collection_name=collection_name,
                max_chunks=max_context_chunks
            )
            
            # 5. Construir prompt RAG
            prompt = self._build_rag_prompt(user_message, context, confidence)
            
            # 6. Llamar a Ollama
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "temperature": self.temperature,
                    "stream": False
                },
                timeout=90
            )
            
            response.raise_for_status()
            result = response.json()
            
            answer = result.get('response', '').strip()
            
            if not answer:
                raise AgentExecutionError("Ollama no devolvió respuesta")
            
            # 7. Preparar fuentes - FIX: Manejar diferentes estructuras de payload
            sources = []
            for r in results:
                payload = r.get('payload', {})
                
                source_info = {
                    'filename': payload.get('filename') or payload.get('source') or payload.get('document_name') or 'Desconocido',
                    'chunk_index': payload.get('chunk_index', 0),
                    'score': r.get('score', 0.0),
                    'text_preview': payload.get('text', '')[:150] + "..." if payload.get('text') else "Sin preview"
                }
                sources.append(source_info)
            
            # 8. Calcular duración
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 9. Guardar respuesta en DB
            if self.db_manager and conversation_id:
                self.db_manager.add_message(
                    conversation_id=conversation_id,
                    role='assistant',
                    content=answer,
                    agent_type=self.agent_type,
                    model=self.model_name,
                    temperature=self.temperature,
                    tokens=result.get('eval_count', 0),
                    had_context=True,
                    context_source='qdrant',
                    metadata={
                        'confidence': confidence,
                        'num_sources': len(sources),
                        'collection': collection_name
                    }
                )
            
            # 10. Log
            self.log_interaction(
                input_text=user_message,
                output_text=answer,
                metadata={
                    'model': self.model_name,
                    'confidence': confidence,
                    'num_sources': len(sources),
                    'duration_ms': duration_ms
                }
            )
            
            self.logger.info(
                f"Respuesta generada con confianza {confidence} "
                f"({len(sources)} fuentes)"
            )
            
            return {
                'answer': answer,
                'confidence': confidence,
                'sources': sources,
                'num_sources': len(sources)
            }
            
        except requests.exceptions.Timeout:
            self.logger.error("Timeout esperando respuesta de Ollama")
            raise AgentExecutionError("Timeout: Ollama tardó demasiado")
        except Exception as e:
            self.logger.error(f"Error en answer: {e}", exc_info=True)
            raise AgentExecutionError(f"Error procesando pregunta: {e}")


def create_knowledge_agent(**kwargs):
    """
    Factory function para crear agente de conocimiento.
    
    Args:
        **kwargs: Argumentos para KnowledgeAgent
        
    Returns:
        Instancia de KnowledgeAgent
    """
    return KnowledgeAgent(**kwargs)