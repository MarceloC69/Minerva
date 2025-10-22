# main.py - v6.0.0 - Minerva con CrewAI + mem0
"""
Punto de entrada principal de Minerva.
Inicializa todos los componentes y lanza la UI de Gradio.
"""

import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Inicializa Minerva y lanza la UI."""
    
    logger.info("=" * 70)
    logger.info("🧠 MINERVA v6.0.0 - Con CrewAI + mem0")
    logger.info("=" * 70)
    
    try:
        # Importar configuración
        from config.settings import settings
        logger.info(f"✅ Configuración cargada desde {settings.SQLITE_PATH}")
        
        # Importar componentes
        from src.database import DatabaseManager
        from src.embeddings import EmbeddingService
        from src.memory.vector_store import VectorMemory
        from src.processing.indexer import DocumentIndexer
        from src.tools.web_search import WebSearchTool
        from src.crew.minerva_crew import MinervaCrew
        
        # 1. Database Manager
        logger.info("1/6 Inicializando Database Manager...")
        db_manager = DatabaseManager(db_path=settings.SQLITE_PATH)
        
        # 2. Embedding Service
        logger.info("2/6 Inicializando Embedding Service...")
        embedding_service = EmbeddingService(
            model_name=settings.EMBEDDING_MODEL
        )
        
        # 3. Vector Memory (para documentos, no para mem0)
        logger.info("3/6 Inicializando Vector Memory...")
        vector_memory = VectorMemory(
            path=str(settings.QDRANT_STORAGE_PATH),
            collection_name="knowledge_base",  # Para documentos
            vector_size=settings.EMBEDDING_DIM
        )
        
        # 4. Document Indexer
        logger.info("4/6 Inicializando Document Indexer...")
        indexer = DocumentIndexer(
            vector_memory=vector_memory,
            db_manager=db_manager,
            embedding_service=embedding_service,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        # 5. Web Search Service
        logger.info("5/6 Inicializando Web Search...")
        web_search = WebSearchTool(api_key=settings.SERPER_API_KEY)
        
        # 6. MinervaCrew (con CrewAI + mem0)
        logger.info("6/6 Inicializando MinervaCrew (CrewAI + mem0)...")
        crew = MinervaCrew(
            db_manager=db_manager,
            indexer=indexer,
            web_search_service=web_search
        )
        
        logger.info("=" * 70)
        logger.info("✅ Todos los componentes inicializados correctamente")
        logger.info("=" * 70)
        
        # Lanzar UI
        logger.info("🚀 Lanzando interfaz Gradio...")
        from src.ui.chat_interface import create_interface
        
        interface = create_interface()
        
        interface.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            show_error=True
        )
        
    except KeyboardInterrupt:
        logger.info("\n👋 Minerva detenido por el usuario")
    
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()