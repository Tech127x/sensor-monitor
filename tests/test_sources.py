"""Tests for sensor data sources."""
# Sensor Monitor - Hardware sensor monitoring for Bitfocus Companion
# Created by Tech127x (https://github.com/tech127x)
# Repository: https://github.com/tech127x/sensor-monitor-ds

from unittest.mock import patch, MagicMock
from sensor_monitor.sources.nvidia import NvidiaSmiSource
from sensor_monitor.sources.disk import DiskTempSource
from sensor_monitor.sources.cpu_sysfs import CpuSysfsSource
from sensor_monitor.sources.nvme import NvmeTempSource


class TestNvidiaSmiSource:
    def test_csv_line_parsing(self):
        source = NvidiaSmiSource(cache_seconds=0)
        mr = MagicMock(returncode=0, stdout="0,GPU-abc,45,78,120.5,65,1024,8192\n")
        with patch("subprocess.run", return_value=mr):
            readings = source.read()
        assert len(readings) == 6
        assert readings[0].value == 45.0

    def test_caching(self):
        source = NvidiaSmiSource(cache_seconds=10.0)
        mr = MagicMock(returncode=0, stdout="0,GPU-abc,45,78,120.5,65,1024,8192\n")
        with patch("subprocess.run", return_value=mr) as m:
            source.read()
            source.read()
            assert m.call_count == 1


class TestDiskTempSource:
    def test_no_drives(self):
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="")):
            assert DiskTempSource().read() == []


class TestCpuSysfsSource:
    def test_no_thermal_zones(self):
        with patch("pathlib.Path.glob", return_value=[]):
            assert CpuSysfsSource().read() == []


class TestNvmeTempSource:
    def test_no_nvme_devices(self):
        with patch("pathlib.Path.glob", return_value=[]):
            assert NvmeTempSource().read() == []
