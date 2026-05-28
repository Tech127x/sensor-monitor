"""Sensor data sources for various hardware monitoring tools."""
from .base import SensorSource, SensorReading
from .lmsensors import LmSensorsSource
from .nvidia import NvidiaSmiSource
from .amd import AmdGpuSource
from .disk import DiskTempSource
from .cpu_sysfs import CpuSysfsSource
from .procstat import ProcStatSource