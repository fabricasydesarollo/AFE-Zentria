# src/modules/graph_client.py

from __future__ import annotations
from typing import List, Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
from src.utils.logger import logger

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

def _session_with_retries(total: int = 3, backoff: float = 0.5) -> requests.Session:
    """
    Retorna una sesión de requests con reintentos automáticos y backoff exponencial.
    Maneja tanto errores HTTP como timeouts.
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=total,
        backoff_factor=backoff,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def get_user_messages(
    token: str,
    user_id: str,
    top: int = 50,
    filter_query: Optional[str] = None,
    select: Optional[str] = "id,subject,receivedDateTime,from,toRecipients",
    timeout: int = 60,
    max_messages: Optional[int] = None,
    max_retries: int = 5
) -> List[Dict[str, Any]]:
    """
    Recupera mensajes del buzón de un usuario desde Microsoft Graph, manejando paginación (@odata.nextLink).
    Utiliza parámetros seguros, sesión con reintentos y manejo de timeouts.
    Args:
        token: Bearer token OAuth2 válido.
        user_id: ID del usuario (email o GUID).
        top: Máximo de mensajes por página (default 50).
        filter_query: Filtro OData opcional.
        select: Campos a seleccionar (default básicos).
        timeout: Timeout de la petición en segundos (default 60s).
        max_messages: Límite máximo de mensajes a recuperar.
        max_retries: Máximo número de reintentos ante timeout (default 5).
    Returns:
        Lista de mensajes (dicts).
    """
    session = _session_with_retries(total=max_retries, backoff=0.5)
    url = f"{GRAPH_BASE}/users/{user_id}/messages"
    params: Dict[str, Any] = {"$top": top, "$select": select}
    if filter_query:
        params["$filter"] = filter_query

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    results: List[Dict[str, Any]] = []
    retry_count = 0

    while True:
        try:
            resp = session.get(url, headers=headers, params=params, timeout=timeout)
            resp.raise_for_status()
            retry_count = 0  # Reset counter on success

        except requests.exceptions.Timeout as e:
            retry_count += 1
            if retry_count > max_retries:
                logger.error(
                    "Timeout en get_user_messages para user=%s después de %d reintentos",
                    user_id, max_retries
                )
                raise

            wait_time = 2 ** (retry_count - 1)  # Backoff exponencial: 1s, 2s, 4s, 8s...
            logger.warning(
                "Timeout en get_user_messages (intento %d/%d), esperando %ds antes de reintentar",
                retry_count, max_retries, wait_time
            )
            time.sleep(wait_time)
            continue

        except requests.exceptions.ConnectionError as e:
            retry_count += 1
            if retry_count > max_retries:
                logger.error(
                    "Error de conexión en get_user_messages para user=%s después de %d reintentos",
                    user_id, max_retries
                )
                raise

            wait_time = 2 ** (retry_count - 1)
            logger.warning(
                "Error de conexión en get_user_messages (intento %d/%d), esperando %ds",
                retry_count, max_retries, wait_time
            )
            time.sleep(wait_time)
            continue

        body = resp.json()
        items = body.get("value", [])
        if max_messages is not None:
            remaining = max_messages - len(results)
            if remaining <= 0:
                break
            if len(items) > remaining:
                results.extend(items[:remaining])
                break
            results.extend(items)
        else:
            results.extend(items)
        next_link = body.get("@odata.nextLink")
        if not next_link or (max_messages is not None and len(results) >= max_messages):
            break
        url = next_link
        params = None  # nextLink ya incluye los params
    return results

def get_message_attachments(
    token: str,
    user_id: str,
    message_id: str,
    timeout: int = 60,
    max_retries: int = 5
) -> List[Dict[str, Any]]:
    """
    Recupera los adjuntos de un mensaje específico de un usuario en Microsoft Graph.
    Maneja reintentos ante timeout con backoff exponencial.
    Args:
        token: Bearer token OAuth2 válido.
        user_id: ID del usuario.
        message_id: ID del mensaje.
        timeout: Timeout de la petición en segundos (default 60s).
        max_retries: Máximo número de reintentos ante timeout (default 5).
    Returns:
        Lista de adjuntos (dicts).
    """
    session = _session_with_retries(total=max_retries, backoff=0.5)
    url = f"{GRAPH_BASE}/users/{user_id}/messages/{message_id}/attachments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    retry_count = 0
    while True:
        try:
            resp = session.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json().get("value", [])

        except requests.exceptions.Timeout as e:
            retry_count += 1
            if retry_count > max_retries:
                logger.error(
                    "Timeout en get_message_attachments para message=%s después de %d reintentos",
                    message_id, max_retries
                )
                raise

            wait_time = 2 ** (retry_count - 1)
            logger.warning(
                "Timeout en get_message_attachments para %s (intento %d/%d), esperando %ds",
                message_id, retry_count, max_retries, wait_time
            )
            time.sleep(wait_time)
            continue

        except requests.exceptions.ConnectionError as e:
            retry_count += 1
            if retry_count > max_retries:
                logger.error(
                    "Error de conexión en get_message_attachments para message=%s después de %d reintentos",
                    message_id, max_retries
                )
                raise

            wait_time = 2 ** (retry_count - 1)
            logger.warning(
                "Error de conexión en get_message_attachments para %s (intento %d/%d), esperando %ds",
                message_id, retry_count, max_retries, wait_time
            )
            time.sleep(wait_time)
            continue

def get_attachment_content_binary(
    token: str,
    user_id: str,
    message_id: str,
    attachment_id: str,
    timeout: int = 60,
    max_retries: int = 5
) -> Optional[bytes]:
    """
    Descarga el contenido binario de un adjunto usando el endpoint /$value.
    Especialmente útil para adjuntos inline que no tienen contentBytes en la respuesta JSON.

    Args:
        token: Bearer token OAuth2 válido.
        user_id: ID del usuario.
        message_id: ID del mensaje.
        attachment_id: ID del adjunto.
        timeout: Timeout de la petición en segundos (default 60s).
        max_retries: Máximo número de reintentos ante timeout (default 5).

    Returns:
        Contenido binario del adjunto, o None si no se puede descargar.
    """
    session = _session_with_retries(total=max_retries, backoff=0.5)
    url = f"{GRAPH_BASE}/users/{user_id}/messages/{message_id}/attachments/{attachment_id}/$value"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "*/*"
    }

    retry_count = 0
    while True:
        try:
            resp = session.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.content

        except requests.exceptions.Timeout as e:
            retry_count += 1
            if retry_count > max_retries:
                logger.error(
                    "Timeout en get_attachment_content_binary para attachment=%s después de %d reintentos",
                    attachment_id, max_retries
                )
                return None

            wait_time = 2 ** (retry_count - 1)
            logger.warning(
                "Timeout descargando adjunto %s (intento %d/%d), esperando %ds",
                attachment_id, retry_count, max_retries, wait_time
            )
            time.sleep(wait_time)
            continue

        except requests.exceptions.ConnectionError as e:
            retry_count += 1
            if retry_count > max_retries:
                logger.error(
                    "Error de conexión en get_attachment_content_binary para attachment=%s después de %d reintentos",
                    attachment_id, max_retries
                )
                return None

            wait_time = 2 ** (retry_count - 1)
            logger.warning(
                "Error de conexión descargando adjunto %s (intento %d/%d), esperando %ds",
                attachment_id, retry_count, max_retries, wait_time
            )
            time.sleep(wait_time)
            continue

        except requests.exceptions.HTTPError as e:
            # Algunos adjuntos pueden no estar disponibles
            logger.warning(
                "Error HTTP descargando adjunto %s: %s",
                attachment_id, str(e)
            )
            return None

        except Exception as e:
            logger.error(
                "Error inesperado descargando adjunto %s: %s",
                attachment_id, str(e)
            )
            return None
