# src/modules/auth.py
from __future__ import annotations
import time
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src.utils.logger import logger

class GraphAuth:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, timeout: int = 30):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout

        self._token: Optional[str] = None
        self._expires_at: float = 0.0

    def _session_with_retries(self) -> requests.Session:
        s = requests.Session()
        s.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=0.5,
                                                         status_forcelist=(500,502,503,504))))
        return s

    def _request_new_token(self) -> Dict[str, Any]:
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": self.client_id,
            "scope": "https://graph.microsoft.com/.default",
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        logger.debug("Solicitando nuevo token a MS identity")
        session = self._session_with_retries()
        resp = session.post(url, data=data, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_token(self) -> str:
        now = time.time()
        if self._token and now < self._expires_at - 60:
            return self._token
        data = self._request_new_token()
        access = data.get("access_token")
        expires = data.get("expires_in", 0)
        if not access:
            raise RuntimeError("No se obtuvo access_token")
        self._token = access
        self._expires_at = now + int(expires)
        logger.info("Token obtenido; expira en %s segundos", expires)
        return self._token
