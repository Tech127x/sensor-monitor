"""Tests for the SensorMonitor class."""
from unittest.mock import patch, MagicMock
from sensor_monitor.core.monitor import SensorMonitor
from sensor_monitor.sources.base import SensorReading


class TestSensorMonitor:
    @staticmethod
    def _make_config(content):
        c = MagicMock()
        c.companion_config = content["companion"]
        c.monitoring = content["monitoring"]
        c.alerts = []
        c.sensor_mappings = content["sensors"]
        for k in ["enable_lmsensors", "enable_nvidia", "enable_amd",
                   "enable_disk_temp", "enable_cpu_sysfs", "enable_cpu_usage",
                   "enable_nvme", "use_libsensors"]:
            setattr(c, k, content.get(k, False))
        c.config = content
        return c

    def test_update_variables_found(self):
        config = {
            "companion": {"host": "localhost", "port": 8000, "use_ssl": False},
            "monitoring": {"update_interval": 1, "max_errors": 5,
                          "variable_prefix": "", "variable_suffix": ""},
            "sensors": [{"variable": "cpu_temp", "chip": "coretemp-0",
                        "sensor": "temp1", "format": "{value:.1f}"}],
            "alerts": [], "enable_lmsensors": True,
            "enable_nvidia": False, "enable_amd": False,
            "enable_disk_temp": False, "enable_cpu_sysfs": False,
            "enable_cpu_usage": False, "enable_nvme": False,
            "use_libsensors": False,
        }
        readings = [SensorReading("coretemp-0", "temp1", 45.0, "\u00b0C", "temperature")]
        with patch("sensor_monitor.core.monitor.Config") as Mc, \
             patch.object(SensorMonitor, "read_all", return_value=readings):
            Mc.return_value = self._make_config(config)
            with patch("sensor_monitor.core.monitor.CompanionClient") as Cc:
                mc = MagicMock()
                mc.set_variable.return_value = True
                Cc.return_value = mc
                mon = SensorMonitor("/fake.yaml")
                assert mon.update_variables() == 1
                mc.set_variable.assert_called_once_with("cpu_temp", "45.0")

    def test_update_variables_not_found(self):
        config = {
            "companion": {"host": "localhost", "port": 8000, "use_ssl": False},
            "monitoring": {"update_interval": 1, "max_errors": 5,
                          "variable_prefix": "", "variable_suffix": ""},
            "sensors": [{"variable": "cpu_temp", "chip": "coretemp-0",
                        "sensor": "temp1", "format": "{value:.1f}"}],
            "alerts": [], "enable_lmsensors": True,
            "enable_nvidia": False, "enable_amd": False,
            "enable_disk_temp": False, "enable_cpu_sysfs": False,
            "enable_cpu_usage": False, "enable_nvme": False,
            "use_libsensors": False,
        }
        with patch("sensor_monitor.core.monitor.Config") as Mc, \
             patch.object(SensorMonitor, "read_all", return_value=[]):
            Mc.return_value = self._make_config(config)
            with patch("sensor_monitor.core.monitor.CompanionClient"):
                mon = SensorMonitor("/fake.yaml")
                assert mon.update_variables() == 0
