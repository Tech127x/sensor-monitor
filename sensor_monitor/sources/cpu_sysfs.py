# Sensor Monitor - Hardware sensor monitoring for Bitfocus Companion
# Created by Tech127x (https://github.com/tech127x)
# Repository: https://github.com/tech127x/sensor-monitor-ds

from pathlib import Path
from typing import List
from .base import SensorSource, SensorReading
from ..utils.helpers import read_sysfs_text

class CpuSysfsSource(SensorSource):
    def name(self) -> str:
        return "Linux CPU sysfs"

    def read(self) -> List[SensorReading]:
        readings = []
        base = Path('/sys/class/thermal')
        for zdir in base.glob('thermal_zone*'):
            tpath = zdir / 'type'
            temp_path = zdir / 'temp'
            if not tpath.is_file() or not temp_path.is_file():
                continue
            zone_type = read_sysfs_text(tpath).strip().lower()
            if not any(x in zone_type for x in ['cpu', 'x86_pkg_temp', 'coretemp', 'k10temp']):
                continue
            temp_raw = read_sysfs_text(temp_path)
            try:
                temp_c = int(temp_raw) / 1000.0
                if 0 < temp_c < 125:
                    readings.append(SensorReading('linux-cpu-thermal', zone_type, temp_c, '°C', 'temperature'))
            except:
                pass
        
        cpu_base = Path('/sys/devices/system/cpu')
        for cpu_dir in cpu_base.glob('cpu[0-9]*'):
            freq_path = cpu_dir / 'cpufreq' / 'scaling_cur_freq'
            if freq_path.is_file():
                khz = read_sysfs_text(freq_path)
                if khz.isdigit():
                    mhz = int(khz) / 1000.0
                    readings.append(SensorReading('linux-cpufreq', cpu_dir.name, mhz, 'MHz', 'other'))
        return readings