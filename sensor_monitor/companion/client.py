import requests
import time
import logging
from typing import Optional, Tuple
from ..utils.helpers import sanitize_variable_name

logger = logging.getLogger(__name__)

class CompanionClient:
    def __init__(self, host='localhost', port=8000, use_ssl=False, reconnect_interval=10):
        self.base_url = f"{'https' if use_ssl else 'http'}://{host}:{port}"
        self.reconnect_interval = reconnect_interval
        self._session = requests.Session()
        self._last_success = 0.0
        self._connected = False
        self._created_variables = set()

    def _request(self, method, endpoint, **kwargs):
        url = self.base_url + endpoint
        try:
            resp = self._session.request(method, url, timeout=5, **kwargs)
            if resp.status_code < 500:
                self._connected = True
                self._last_success = time.time()
                return resp
            else:
                self._connected = False
                logger.warning(f"HTTP {resp.status_code} for {method} {endpoint}")
                return None
        except requests.exceptions.ConnectionError:
            self._connected = False
            return None
        except requests.exceptions.Timeout:
            self._connected = False
            return None
        except Exception as e:
            self._connected = False
            logger.error(f"Request failed: {e}")
            return None

    def ensure_connected(self) -> bool:
        if self._connected:
            return True
        if time.time() - self._last_success < self.reconnect_interval:
            return False
        try:
            resp = self._session.get(f"{self.base_url}/api/location/1", timeout=2)
            if resp.status_code < 500:
                self._connected = True
                self._last_success = time.time()
                logger.info("Connected to Companion")
                return True
        except Exception:
            pass
        return False

    def create_custom_variable(self, name: str) -> bool:
        clean = sanitize_variable_name(name)
        if clean in self._created_variables:
            return True
        if not self.ensure_connected():
            return False
        
        resp = self._request('POST', f'/api/custom-variable/{clean}/value',
                           data="0", headers={'Content-Type': 'text/plain'})
        if resp and resp.status_code in (200, 201):
            self._created_variables.add(clean)
            logger.info(f"Created variable: {clean}")
            return True
        return False

    def set_variable(self, name: str, value: str) -> bool:
        if not self.ensure_connected():
            return False
        clean = sanitize_variable_name(name)
        
        if clean not in self._created_variables:
            if not self.create_custom_variable(clean):
                return False
        
        resp = self._request('POST', f'/api/custom-variable/{clean}/value',
                           data=value, headers={'Content-Type': 'text/plain'})
        if resp and resp.status_code == 200:
            logger.debug(f"Set {clean} = {value}")
            return True
        return False

    def variable_exists(self, name: str) -> Tuple[bool, bool]:
        if not self.ensure_connected():
            return False, False
        clean = sanitize_variable_name(name)
        resp = self._request('GET', f'/api/custom-variable/{clean}/value')
        if resp is None:
            return False, False
        return resp.status_code == 200, True