"""
Procesador de documentos para extraer texto de PDF, DOCX y TXT.
"""

from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

# Intentar importar PyMuPDF con ambos nombres
try:
    import pymupdf as fitz  # PyMuPDF versión nueva
except ImportError:
    try:
        import fitz  # PyMuPDF versión vieja
    except ImportError:
        raise ImportError(
            "PyMuPDF no está instalado. Ejecuta: pip install PyMuPDF>=1.23.0"
        )

from docx import Document
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Representa un fragmento de documento procesado."""
    text: str
    chunk_index: int
    source_file: str
    page_number: Optional[int] = None
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DocumentProcessor:
    """
    Procesa documentos de diferentes formatos y los divide en chunks.
    """
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        """
        Inicializa el procesador.
        
        Args:
            chunk_size: Tamaño máximo de cada chunk en caracteres
            chunk_overlap: Cantidad de caracteres que se solapan entre chunks
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        logger.info(f"DocumentProcessor inicializado (size={self.chunk_size}, overlap={self.chunk_overlap})")
    
    def process_file(self, file_path: str) -> List[DocumentChunk]:
        """
        Procesa un archivo y retorna sus chunks.
        
        Args:
            file_path: Ruta al archivo
            
        Returns:
            Lista de DocumentChunk
            
        Raises:
            ValueError: Si el formato no es soportado
            FileNotFoundError: Si el archivo no existe
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        # Detectar tipo de archivo
        suffix = path.suffix.lower()
        
        if suffix == '.pdf':
            text = self._extract_pdf(path)
        elif suffix == '.docx':
            text = self._extract_docx(path)
        elif suffix == '.txt':
            text = self._extract_txt(path)
        else:
            raise ValueError(f"Formato no soportado: {suffix}")
        
        # Dividir en chunks
        chunks = self._create_chunks(text, str(path))
        
        logger.info(f"Procesado {path.name}: {len(chunks)} chunks")
        return chunks
    
    def _extract_pdf(self, path: Path) -> str:
        """Extrae texto de un PDF."""
        try:
            doc = fitz.open(path)
            text = ""
            
            for page_num, page in enumerate(doc, 1):
                page_text = page.get_text()
                text += f"\n[Página {page_num}]\n{page_text}"
            
            doc.close()
            return text
        except Exception as e:
            logger.error(f"Error extrayendo PDF {path.name}: {e}")
            raise
    
    def _extract_docx(self, path: Path) -> str:
        """Extrae texto de un DOCX."""
        try:
            doc = Document(path)
            text = "\n\n".join([para.text for para in doc.paragraphs])
            return text
        except Exception as e:
            logger.error(f"Error extrayendo DOCX {path.name}: {e}")
            raise
    
    def _extract_txt(self, path: Path) -> str:
        """Extrae texto de un archivo TXT."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Intentar con latin-1 como fallback
            with open(path, 'r', encoding='latin-1') as f:
                return f.read()
    
    def _create_chunks(self, text: str, source_file: str) -> List[DocumentChunk]:
        """
        Divide el texto en chunks con overlap.
        
        Args:
            text: Texto completo
            source_file: Nombre del archivo fuente
            
        Returns:
            Lista de DocumentChunk
        """
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # Calcular end del chunk
            end = start + self.chunk_size
            
            # Si no es el último chunk, intentar cortar en espacio/punto
            if end < len(text):
                # Buscar el último espacio o punto en los últimos 50 caracteres
                cut_window = text[end-50:end]
                last_space = cut_window.rfind(' ')
                last_period = cut_window.rfind('.')
                
                cut_pos = max(last_space, last_period)
                if cut_pos != -1:
                    end = end - 50 + cut_pos + 1
            
            # Extraer chunk
            chunk_text = text[start:end].strip()
            
            if chunk_text:  # Solo agregar chunks no vacíos
                chunk = DocumentChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    source_file=source_file,
                    metadata={
                        'char_start': start,
                        'char_end': end,
                        'length': len(chunk_text)
                    }
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # Mover start con overlap
            start = end - self.chunk_overlap
        
        return chunks


# Función helper para uso directo
def process_document(file_path: str, chunk_size: int = None, chunk_overlap: int = None) -> List[DocumentChunk]:
    """
    Procesa un documento y retorna sus chunks.
    Función de conveniencia.
    """
    processor = DocumentProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return processor.process_file(file_path)