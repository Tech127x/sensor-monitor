import subprocess
import time
from typing import List, Optional
from .base import SensorSource, SensorReading

class NvidiaSmiSource(SensorSource):
    def __init__(self, cache_seconds: float = 2.0):
        self.cache_seconds = cache_seconds
        self._cache: Optional[List[SensorReading]] = None
        self._last_update: float = 0

    def name(self) -> str:
        return "nvidia-smi"

    def read(self) -> List[SensorReading]:
        now = time.monotonic()
        if self._cache is not None and (now - self._last_update) < self.cache_seconds:
            return self._cache
        self._cache = self._query()
        self._last_update = now
        return self._cache

    def _query(self) -> List[SensorReading]:
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=index,uuid,temperature.gpu,utilization.gpu,power.draw,fan.speed,memory.used,memory.total',
                 '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=10
            )
        except:
            return []
        if result.returncode != 0:
            return []
        readings = []
        for line in result.stdout.splitlines():
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 8:
                continue
            idx, uuid, temp_gpu, util_gpu, power, fan, mem_used, mem_total = parts
            chip = f"nvidia-{uuid}" if uuid else f"nvidia-gpu-{idx}"
            if temp_gpu and temp_gpu != 'N/A':
                readings.append(SensorReading(chip, 'gpu_temp', float(temp_gpu), '°C', 'temperature'))
            if util_gpu and util_gpu != 'N/A':
                readings.append(SensorReading(chip, 'gpu_util', float(util_gpu), '%', 'utilization'))
            if power and power != 'N/A':
                readings.append(SensorReading(chip, 'power_draw', float(power), 'W', 'power'))
            if fan and fan != 'N/A':
                readings.append(SensorReading(chip, 'fan_speed', float(fan), '%', 'fan'))
            if mem_used and mem_used != 'N/A':
                readings.append(SensorReading(chip, 'memory_used_mib', float(mem_used), 'MiB', 'memory'))
            if mem_total and mem_total != 'N/A':
                readings.append(SensorReading(chip, 'memory_total_mib', float(mem_total), 'MiB', 'memory'))
        return readings