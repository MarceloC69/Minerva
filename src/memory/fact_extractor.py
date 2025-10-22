# src/memory/fact_extractor.py
"""
Extractor de hechos usando Ollama para memoria a largo plazo.
Convierte conversaciones en hechos persistentes.
"""

from typing import List, Dict, Optional
import requests
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FactExtractor:
    """
    Extrae hechos clave de conversaciones usando Ollama.
    
    Características:
    - Usa Ollama/Phi3 local
    - Extrae información persistente
    - Categoriza hechos por tipo
    - Prompt cargado desde DB
    """
    
    def __init__(
        self,
        model_name: str = "phi3",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.3,
        db_manager = None
    ):
        """
        Inicializa el extractor de hechos.
        
        Args:
            model_name: Modelo de Ollama a usar
            base_url: URL base de Ollama
            temperature: Temperatura (baja = más preciso)
            db_manager: Database manager para cargar prompt
        """
        self.model_name = model_name
        self.base_url = base_url
        self.temperature = temperature
        self.db_manager = db_manager
        
        # Cargar prompt desde DB
        self._load_prompt()
        
        logger.info(f"✅ FactExtractor inicializado con {model_name}")
    
    def _load_prompt(self):
        """Carga el prompt de extracción desde la base de datos."""
        if not self.db_manager:
            logger.error("❌ No hay db_manager, usando prompt por defecto")
            self.extraction_prompt = """Analiza la conversación y extrae hechos importantes.
Responde con JSON: {"facts": [{"category": "tipo", "fact": "texto"}]}"""
            return
        
        try:
            from src.database.prompt_manager import PromptManager
            pm = PromptManager(self.db_manager)
            
            self.extraction_prompt = pm.get_active_prompt(
                agent_type='fact_extractor',
                prompt_name='extraction_prompt'
            )
            
            if not self.extraction_prompt:
                logger.error("❌ No se encontró prompt de extracción en DB")
                raise Exception("Prompt 'fact_extractor/extraction_prompt' no encontrado")
            
            # LOG: Mostrar qué prompt se cargó
            logger.info("=" * 60)
            logger.info("📝 PROMPT FACT_EXTRACTOR CARGADO:")
            logger.info("-" * 60)
            logger.info(self.extraction_prompt[:200] + "...")
            logger.info("=" * 60)
            logger.info("✅ Prompt de extracción cargado desde DB")
            
        except Exception as e:
            logger.error(f"❌ Error cargando prompt: {e}")
            raise
    
    def extract_facts(
        self,
        user_messages: List[str],
        ai_messages: List[str]
    ) -> List[Dict[str, str]]:
        """
        Extrae hechos de una conversación.
        
        Args:
            user_messages: Lista de mensajes del usuario
            ai_messages: Lista de respuestas de la IA
            
        Returns:
            Lista de hechos extraídos con categorías
        """
        if not user_messages or not ai_messages:
            logger.warning("No hay mensajes para extraer hechos")
            return []
        
        # Formatear conversación
        conversation = self._format_conversation(user_messages, ai_messages)
        
        # Construir prompt
        prompt = self.extraction_prompt.format(conversation=conversation)
        
        try:
            # Llamar a Ollama
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "temperature": self.temperature,
                    "stream": False
                },
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extraer respuesta
            raw_output = result.get('response', '').strip()
            
            # Parsear JSON
            facts = self._parse_facts_json(raw_output)
            
            if facts:
                logger.info(f"✅ {len(facts)} hechos extraídos")
            else:
                logger.info("ℹ️ No se encontraron hechos relevantes")
            
            return facts
            
        except requests.RequestException as e:
            logger.error(f"❌ Error llamando a Ollama: {e}")
            return []
        
        except Exception as e:
            logger.error(f"❌ Error extrayendo hechos: {e}")
            return []
    
    def _format_conversation(
        self,
        user_messages: List[str],
        ai_messages: List[str]
    ) -> str:
        """Formatea la conversación para el prompt."""
        conversation = ""
        
        # Intercalar mensajes
        for i in range(min(len(user_messages), len(ai_messages))):
            conversation += f"Usuario: {user_messages[i]}\n"
            conversation += f"Minerva: {ai_messages[i]}\n\n"
        
        return conversation.strip()
    
    def _parse_facts_json(self, raw_output: str) -> List[Dict[str, str]]:
        """
        Parsea la respuesta JSON del modelo.
        
        Args:
            raw_output: Salida cruda del modelo
            
        Returns:
            Lista de hechos parseados
        """
        try:
            # Intentar parsear JSON directamente
            data = json.loads(raw_output)
            facts = data.get('facts', [])
            
            # Validar estructura
            valid_facts = []
            for fact in facts:
                if isinstance(fact, dict) and 'category' in fact and 'fact' in fact:
                    valid_facts.append({
                        'category': fact['category'],
                        'fact': fact['fact'],
                        'extracted_at': datetime.now().isoformat()
                    })
            
            return valid_facts
            
        except json.JSONDecodeError:
            # Intentar extraer JSON del texto
            try:
                # Buscar JSON entre llaves
                start = raw_output.find('{')
                end = raw_output.rfind('}') + 1
                
                if start != -1 and end > start:
                    json_str = raw_output[start:end]
                    data = json.loads(json_str)
                    facts = data.get('facts', [])
                    
                    valid_facts = []
                    for fact in facts:
                        if isinstance(fact, dict) and 'category' in fact and 'fact' in fact:
                            valid_facts.append({
                                'category': fact['category'],
                                'fact': fact['fact'],
                                'extracted_at': datetime.now().isoformat()
                            })
                    
                    return valid_facts
                    
            except Exception as e:
                logger.error(f"❌ Error parseando JSON: {e}")
        
        logger.warning("⚠️ No se pudo parsear la respuesta del modelo")
        return []


class FactMemoryService:
    """
    Servicio que combina extracción de hechos con almacenamiento vectorial.
    """
    
    def __init__(
        self,
        fact_extractor: FactExtractor,
        vector_memory,  # VectorMemory
        embedding_service,  # EmbeddingService
        extraction_interval: int = 5
    ):
        """
        Inicializa el servicio de memoria de hechos.
        
        Args:
            fact_extractor: Extractor de hechos
            vector_memory: Almacenamiento vectorial (Qdrant)
            embedding_service: Servicio de embeddings
            extraction_interval: Cada cuántos mensajes extraer hechos
        """
        self.fact_extractor = fact_extractor
        self.vector_memory = vector_memory
        self.embedding_service = embedding_service
        self.extraction_interval = extraction_interval
        
        self.message_count = 0
        self.pending_user_messages = []
        self.pending_ai_messages = []
        
        logger.info(f"✅ FactMemoryService inicializado (intervalo: cada {extraction_interval} mensajes)")
    
    def add_exchange(self, user_message: str, ai_message: str):
        """
        Agrega un intercambio de mensajes y verifica si extraer hechos.
        
        Args:
            user_message: Mensaje del usuario
            ai_message: Respuesta de la IA
        """
        self.pending_user_messages.append(user_message)
        self.pending_ai_messages.append(ai_message)
        self.message_count += 1
        
        # Verificar si es momento de extraer hechos
        if self.message_count % self.extraction_interval == 0:
            logger.info(f"🧠 Llegamos a {self.message_count} mensajes, extrayendo hechos...")
            self._extract_and_store_facts()
    
    def _extract_and_store_facts(self):
        """Extrae hechos de mensajes pendientes y los almacena."""
        if not self.pending_user_messages:
            return
        
        # Extraer hechos
        facts = self.fact_extractor.extract_facts(
            self.pending_user_messages,
            self.pending_ai_messages
        )
        
        if facts:
            logger.info(f"📝 Extrayendo {len(facts)} hechos...")
            
            # Preparar para almacenamiento en batch
            fact_texts = []
            fact_embeddings = []
            fact_payloads = []
            
            for fact_data in facts:
                fact_text = f"[{fact_data['category']}] {fact_data['fact']}"
                
                try:
                    # Generar embedding
                    embedding = self.embedding_service.embed_text(fact_text)
                    
                    # Agregar a batch
                    fact_texts.append(fact_text)
                    fact_embeddings.append(embedding)
                    fact_payloads.append({
                        'text': fact_text,
                        'type': 'fact',
                        'category': fact_data['category'],
                        'extracted_at': fact_data['extracted_at']
                    })
                    
                except Exception as e:
                    logger.error(f"❌ Error generando embedding para hecho: {e}")
            
            # Guardar batch en Qdrant usando add_texts
            if fact_texts:
                try:
                    self.vector_memory.add_texts(
                        texts=fact_texts,
                        embeddings=fact_embeddings,
                        payloads=fact_payloads
                    )
                    logger.info(f"💾 {len(fact_texts)} hechos almacenados en Qdrant")
                    
                except Exception as e:
                    logger.error(f"❌ Error almacenando hechos en Qdrant: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Limpiar buffer
        self.pending_user_messages.clear()
        self.pending_ai_messages.clear()
    
    def get_relevant_facts(self, query: str, limit: int = 3) -> List[str]:
        """
        Recupera hechos relevantes basados en una consulta.
        
        Args:
            query: Consulta del usuario
            limit: Número máximo de hechos
            
        Returns:
            Lista de hechos relevantes
        """
        try:
            # Generar embedding de la query
            query_embedding = self.embedding_service.embed_text(query)
            
            # Buscar en Qdrant
            results = self.vector_memory.search(
                query_embedding=query_embedding,
                limit=limit * 2  # Buscar más porque filtramos después
            )
            
            # Filtrar solo hechos y extraer texto
            facts = []
            for r in results:
                payload = r.get('payload', {})
                if payload.get('type') == 'fact':
                    fact_text = payload.get('text', '')
                    if fact_text:
                        facts.append(fact_text)
            
            # Limitar a la cantidad solicitada
            facts = facts[:limit]
            
            if facts:
                logger.info(f"✅ {len(facts)} hechos recuperados")
            
            return facts
            
        except Exception as e:
            logger.error(f"❌ Error recuperando hechos: {e}")
            return []