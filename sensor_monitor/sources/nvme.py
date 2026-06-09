# Sensor Monitor - Hardware sensor monitoring for Bitfocus Companion
# Created by Tech127x (https://github.com/tech127x)
# Repository: https://github.com/tech127x/sensor-monitor-ds

from pathlib import Path
from typing import List
from .base import SensorSource, SensorReading
from ..utils.helpers import read_sysfs_text

class NvmeTempSource(SensorSource):
    def name(self) -> str:
        return "NVMe drives"

    def read(self) -> List[SensorReading]:
        readings = []
        base = Path('/sys/class/nvme')
        for nvme_dir in base.glob('nvme*'):
            # Temperature is in millikelvin? Actually many expose in Celsius
            temp_path = nvme_dir / 'hwmon' / 'hwmon*' / 'temp1_input'
            # Find actual hwmon subdir
            hwmon_dirs = list(nvme_dir.glob('hwmon/hwmon*'))
            if hwmon_dirs:
                temp_file = hwmon_dirs[0] / 'temp1_input'
                if temp_file.is_file():
                    raw = read_sysfs_text(temp_file)
                    if raw:
                        try:
                            # Usually millidegrees Celsius
                            temp_c = int(raw) / 1000.0
                            if -10 < temp_c < 125:
                                readings.append(SensorReading(
                                    chip=nvme_dir.name,
                                    name='nvme_temp',
                                    value=temp_c,
                                    unit='°C',
                                    category='temperature'
                                ))
                        except:
                            pass
            # Fallback: try nvme command if available
            if not readings:
                import subprocess
                try:
                    result = subprocess.run(
                        ['nvme', 'smart-log', nvme_dir.name],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        for line in result.stdout.splitlines():
                            if 'temperature' in line.lower():
                                # Example: "temperature          : 35 °C"
                                parts = line.split(':')
                                if len(parts) >= 2:
                                    temp_str = parts[1].strip().split()[0]
                                    try:
                                        temp_c = float(temp_str)
                                        readings.append(SensorReading(
                                            chip=nvme_dir.name,
                                            name='nvme_temp',
                                            value=temp_c,
                                            unit='°C',
                                            category='temperature'
                                        ))
                                    except:
                                        pass
                except:
                    pass
        return readings