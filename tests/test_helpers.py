# Sensor Monitor - Hardware sensor monitoring for Bitfocus Companion
# Created by Tech127x (https://github.com/tech127x)
# Repository: https://github.com/tech127x/sensor-monitor-ds

import pytest
from sensor_monitor.utils.helpers import sanitize_variable_name,get_unit,normalize_hardware_key

class T:
    def test_a(self):
        assert sanitize_variable_name("hello")=="hello"
    def test_b(self):
        assert get_unit("temp1")=="°C"
