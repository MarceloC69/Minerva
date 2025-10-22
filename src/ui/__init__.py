# ============================================================
# src/ui/__init__.py - v6.0.0
# ============================================================
"""
Módulo de interfaz de usuario de Minerva.
"""

from .chat_interface import create_interface
from .prompt_admin import create_prompt_admin_interface

__all__ = [
    'create_interface',
    'create_prompt_admin_interface'
]