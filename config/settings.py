"""
Configuración centralizada de Minerva usando Pydantic Settings.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Configuración global de Minerva."""
    
    # Configuración de Pydantic (nueva sintaxis)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignorar variables extra del .env
    )
    
    # Directorios del proyecto
    PROJECT_ROOT: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    DATA_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data")
    QDRANT_STORAGE_PATH: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "data" / "qdrant_storage"
    )
    SQLITE_PATH: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "data" / "sqlite" / "minerva.db"
    )
    UPLOADS_DIR: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "data" / "uploads"
    )
    LOGS_DIR: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "logs"
    )
    
    # Configuración de embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    
    # Configuración de Qdrant
    QDRANT_COLLECTION_NAME: str = "minerva_memory"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    
    # Configuración de Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "phi3"
    OLLAMA_TEMPERATURE: float = 0.7
    
    # Límites y configuraciones
    MAX_SEARCH_RESULTS: int = 5
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Crear directorios necesarios
        self._create_directories()
    
    def _create_directories(self):
        """Crea los directorios necesarios si no existen."""
        directories = [
            self.DATA_DIR,
            self.QDRANT_STORAGE_PATH,
            self.SQLITE_PATH.parent,
            self.UPLOADS_DIR,
            self.LOGS_DIR
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# Instancia global de configuración
settings = Settings()