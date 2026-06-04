"""Tests for the Config class."""
import os
import tempfile
import yaml
import pytest
from sensor_monitor.core.config import Config
from sensor_monitor.sources.base import SensorReading


class TestConfig:
    def test_missing_config_file(self):
        cfg = Config("/nonexistent/config.yaml")
        assert cfg.companion_config["host"] == "localhost"
        assert cfg.sensor_mappings == []

    def test_repair_sensor_mappings(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"sensors": [{"variable": "cpu_temp", "chip": "old-chip", "sensor": "core_0"}]}, f)
            fname = f.name
        try:
            cfg = Config(fname)
            readings = [SensorReading("coretemp-0", "core_0", 45.0, "\u00b0C", "temperature")]
            assert cfg.repair_sensor_mappings(readings)
            assert cfg.sensor_mappings[0]["chip"] == "coretemp-0"
        finally:
            os.unlink(fname)

    def test_load_config_with_values(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({
                "companion": {"host": "192.168.1.100", "port": 9000},
                "monitoring": {"update_interval": 2, "max_errors": 10},
                "sensors": [{"variable": "cpu_temp", "chip": "coretemp-0", "sensor": "temp1"}],
                "enable_nvidia": False,
            }, f)
            fname = f.name
        try:
            cfg = Config(fname)
            assert cfg.companion_config["host"] == "192.168.1.100"
            assert not cfg.enable_nvidia
            assert len(cfg.sensor_mappings) == 1
        finally:
            os.unlink(fname)
