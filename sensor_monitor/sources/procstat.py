import time
from typing import List, Dict, Tuple, Optional
from .base import SensorSource, SensorReading

class ProcStatSource(SensorSource):
    def __init__(self):
        self._prev: Optional[Dict[str, Tuple[int, int]]] = None
        self._last_readings: List[SensorReading] = []

    def name(self) -> str:
        return "/proc/stat CPU usage"

    def read(self) -> List[SensorReading]:
        curr = self._parse()
        if not curr or 'cpu_total' not in curr:
            return self._last_readings
        if self._prev is None:
            self._prev = curr
            # Retry up to 5 times with increasing sleep to get a measurable delta
            for attempt in range(5):
                time.sleep(0.05 * (attempt + 1))
                curr = self._parse()
                if curr and self._compute_usage(self._prev, curr):
                    break
            if not curr:
                return self._last_readings
        pcts = self._compute_usage(self._prev, curr)
        self._prev = curr
        if not pcts:
            return self._last_readings
        readings = []
        for key, val in pcts.items():
            name = 'cpu_usage_total' if key == 'cpu_total' else f'cpu_usage_{key[3:]}'
            readings.append(SensorReading('linux-cpu-usage', name, val, '%', 'utilization'))
        self._last_readings = readings
        return readings

    def _parse(self) -> Dict[str, Tuple[int, int]]:
        out = {}
        try:
            with open('/proc/stat', 'r') as f:
                for line in f:
                    if not line.startswith('cpu'):
                        break
                    parts = line.split()
                    if len(parts) < 5:
                        continue
                    tag = parts[0]
                    if tag == 'cpu':
                        key = 'cpu_total'
                    elif tag.startswith('cpu') and tag[3:].isdigit():
                        key = tag
                    else:
                        continue
                    nums = []
                    for x in parts[1:]:
                        try:
                            nums.append(int(x))
                        except:
                            break
                    if len(nums) < 4:
                        continue
                    idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
                    total = sum(nums)
                    out[key] = (idle, total)
        except:
            pass
        return out

    def _compute_usage(self, prev: Dict, curr: Dict) -> Dict[str, float]:
        pcts = {}
        for key in curr:
            if key not in prev:
                continue
            i0, t0 = prev[key]
            i1, t1 = curr[key]
            di = i1 - i0
            dt = t1 - t0
            if dt <= 0:
                continue
            idle_frac = di / dt
            pcts[key] = max(0.0, min(100.0, 100.0 * (1.0 - idle_frac)))
        return pcts