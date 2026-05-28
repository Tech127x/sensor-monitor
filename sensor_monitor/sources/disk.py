import subprocess
from typing import List
from .base import SensorSource, SensorReading

class DiskTempSource(SensorSource):
    def name(self) -> str:
        return "smartctl"

    def read(self) -> List[SensorReading]:
        try:
            result = subprocess.run(['lsblk', '-d', '-o', 'NAME,TYPE'], capture_output=True, text=True)
            drives = []
            for line in result.stdout.splitlines():
                if 'disk' in line:
                    name = line.split()[0]
                    drives.append(f'/dev/{name}')
        except:
            return []
        
        readings = []
        for dev in drives:
            try:
                res = subprocess.run(['smartctl', '-A', dev], capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        if 'Temperature_Celsius' in line:
                            parts = line.split()
                            for i, p in enumerate(parts):
                                if p == 'Temperature_Celsius' and i+9 < len(parts):
                                    temp = parts[i+9]
                                    try:
                                        readings.append(SensorReading(dev, 'temperature', float(temp), '°C', 'temperature'))
                                    except:
                                        pass
            except:
                continue
        return readings