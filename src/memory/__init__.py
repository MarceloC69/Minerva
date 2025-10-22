# src/memory/__init__.py - v6.0.0
"""
Módulo de memoria de Minerva.
Incluye mem0 wrapper y vector store para documentos.
"""

# Vector store (para documentos)
from .vector_store import VectorMemory

# mem0 wrapper (para memoria persistente)
from .mem0_wrapper import Mem0Wrapper

__all__ = [
    'VectorMemory',
    'Mem0Wrapper'
]