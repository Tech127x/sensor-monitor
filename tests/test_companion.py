"""Tests for the Companion client."""
from unittest.mock import patch, MagicMock
from sensor_monitor.companion.client import CompanionClient


class TestCompanionClient:
    def test_base_url_no_ssl(self):
        assert CompanionClient(host="localhost", port=8000, use_ssl=False).base_url == "http://localhost:8000"

    def test_ensure_connected_success(self):
        c = CompanionClient()
        with patch.object(c._session, "get") as g:
            g.return_value = MagicMock(status_code=200)
            assert c.ensure_connected()

    def test_set_variable_creates_first(self):
        c = CompanionClient()
        with patch.object(c, "ensure_connected", return_value=True), \
             patch.object(c, "_request") as r:
            r.side_effect = [MagicMock(status_code=201), MagicMock(status_code=200)]
            assert c.set_variable("my_var", "42.0")
            assert "my_var" in c._created_variables

    def test_set_variable_connection_failure(self):
        c = CompanionClient()
        with patch.object(c, "ensure_connected", return_value=False):
            assert not c.set_variable("my_var", "42.0")
