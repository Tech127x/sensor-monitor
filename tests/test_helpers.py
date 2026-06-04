import pytest
from sensor_monitor.utils.helpers import sanitize_variable_name,get_unit,normalize_hardware_key

class T:
    def test_a(self):
        assert sanitize_variable_name("hello")=="hello"
    def test_b(self):
        assert get_unit("temp1")=="°C"
