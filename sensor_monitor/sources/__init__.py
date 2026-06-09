"""Sensor data sources for various hardware monitoring tools."""
# Sensor Monitor - Hardware sensor monitoring for Bitfocus Companion
# Created by Tech127x (https://github.com/tech127x)
# Repository: https://github.com/tech127x/sensor-monitor-ds

from .base import SensorSource, SensorReading
from .lmsensors import LmSensorsSource
from .nvidia import NvidiaSmiSource
from .amd import AmdGpuSource
from .disk import DiskTempSource
from .cpu_sysfs import CpuSysfsSource
from .procstat import ProcStatSource
from .nvme import NvmeTempSource