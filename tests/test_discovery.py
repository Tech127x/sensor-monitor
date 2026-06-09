"""Tests for the SensorDiscovery module."""
# Sensor Monitor - Hardware sensor monitoring for Bitfocus Companion
# Created by Tech127x (https://github.com/tech127x)
# Repository: https://github.com/tech127x/sensor-monitor-ds

from unittest.mock import patch, MagicMock
from sensor_monitor.core.discovery import SensorDiscovery, DiscoveredSensor
from sensor_monitor.sources.base import SensorReading


class TestDiscoveredSensor:
    def test_simple_name_created(self):
        reading = SensorReading("coretemp-0", "core_0", 45.0, "\u00b0C", "temperature")
        ds = DiscoveredSensor(reading)
        assert ds.chip == "coretemp-0"
        assert ds.unit == "\u00b0C"


class TestSensorDiscovery:
    def test_sorted_sensors_empty(self):
        assert SensorDiscovery().sorted_sensors() == []

    def test_assign_default_variables_unique(self):
        d = SensorDiscovery()
        names = d.assign_default_variables([
            DiscoveredSensor(SensorReading("t", "a", 1.0, "\u00b0C", "temperature")),
            DiscoveredSensor(SensorReading("t", "b", 2.0, "\u00b0C", "temperature")),
        ])
        assert len(names) == 2
        assert names[0] != names[1]

    def test_companion_format_yaml_rpm(self):
        reading = SensorReading("nct6798-0", "fan1", 1200.0, "RPM", "fan")
        fmt = SensorDiscovery.companion_format_yaml(DiscoveredSensor(reading))
        assert "{value:.0f}RPM" in fmt
