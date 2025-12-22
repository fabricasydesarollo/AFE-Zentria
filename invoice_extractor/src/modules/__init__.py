# src/modules/__init__.py
"""
Módulo modules - Funcionalidades de integración con servicios externos.
"""
from src.modules.auth import GraphAuth
from src.modules.email_reader import EmailReader
from src.modules.graph_client import get_user_messages, get_message_attachments
from src.modules.storage import LocalJSONWriter, WriterInterface
from src.modules.attachments import save_attachment

__all__ = [
    'GraphAuth',
    'EmailReader',
    'get_user_messages',
    'get_message_attachments',
    'LocalJSONWriter',
    'WriterInterface',
    'save_attachment',
]