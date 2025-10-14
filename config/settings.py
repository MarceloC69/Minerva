from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    """Configuración centralizada del proyecto"""
    
    # Paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "phi3"
    
    # Qdrant
    QDRANT_PATH: str = str(DATA_DIR / "qdrant_storage")
    QDRANT_COLLECTION_CONVERSATIONS: str = "conversations"
    QDRANT_COLLECTION_KNOWLEDGE: str = "knowledge_chunks"
    
    # SQLite
    SQLITE_DB_PATH: str = str(DATA_DIR / "sqlite" / "minerva.db")
    
    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSIONS: int = 384
    
    # Logs
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Crear directorios si no existen
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / "qdrant_storage").mkdir(exist_ok=True)
        (self.DATA_DIR / "sqlite").mkdir(exist_ok=True)
        (self.DATA_DIR / "uploads").mkdir(exist_ok=True)