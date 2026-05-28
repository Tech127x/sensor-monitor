import subprocess
import re
from typing import List
from .base import SensorSource, SensorReading

class AmdGpuSource(SensorSource):
    def name(self) -> str:
        return "rocm-smi"

    def read(self) -> List[SensorReading]:
        try:
            result = subprocess.run(['rocm-smi', '--showtemp', '--showpower', '--showfan', '--showuse'],
                                    capture_output=True, text=True, timeout=10)
        except:
            return []
        if result.returncode != 0:
            return []
        readings = []
        for line in result.stdout.splitlines():
            if 'GPU[' in line and 'Temperature' in line:
                m = re.search(r'GPU\[(\d+)\].*Temperature:\s*(\d+\.?\d*)', line)
                if m:
                    idx, temp = m.group(1), float(m.group(2))
                    readings.append(SensorReading(f"amd-gpu-{idx}", 'gpu_temp', temp, '°C', 'temperature'))
            if 'GPU[' in line and 'Power' in line:
                m = re.search(r'Power:\s*(\d+\.?\d*)\s*W', line)
                if m:
                    power = float(m.group(1))
                    idx = re.search(r'GPU\[(\d+)\]', line).group(1)
                    readings.append(SensorReading(f"amd-gpu-{idx}", 'power_draw', power, 'W', 'power'))
        return readings