import subprocess
import json
import re
import logging
from typing import List
from .base import SensorSource, SensorReading

logger = logging.getLogger(__name__)
_rocm_warned = False

class AmdGpuSource(SensorSource):
    def name(self) -> str:
        return "rocm-smi"

    def read(self) -> List[SensorReading]:
        global _rocm_warned
        # Try --json format first (more stable), fall back to text parsing
        try:
            result = subprocess.run(['rocm-smi', '--json'],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                return self._parse_json(result.stdout)
        except FileNotFoundError:
            pass
        except Exception:
            pass

        try:
            result = subprocess.run(['rocm-smi', '--showtemp', '--showpower', '--showfan', '--showuse'],
                                    capture_output=True, text=True, timeout=10)
        except FileNotFoundError:
            if not _rocm_warned:
                logger.warning("rocm-smi not found. AMD GPU monitoring disabled.")
                _rocm_warned = True
            return []
        except Exception:
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

    def _parse_json(self, stdout: str) -> List[SensorReading]:
        """Parse rocm-smi --json output."""
        readings = []
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return readings
        if not isinstance(data, dict):
            return readings
        for gpu_key, gpu_info in data.items():
            # Extract GPU index from key like 'card0' or 'GPU[0]'
            idx_match = re.search(r'(\d+)', str(gpu_key))
            idx = idx_match.group(1) if idx_match else '0'
            chip = f"amd-gpu-{idx}"

            if isinstance(gpu_info, dict):
                # Temperature
                temp = gpu_info.get('Temperature (Sensor edge) (C)') or \
                       gpu_info.get('Temperature (C)') or \
                       gpu_info.get('GPU Temperature (C)')
                if temp is not None:
                    try:
                        readings.append(SensorReading(chip, 'gpu_temp', float(temp), '°C', 'temperature'))
                    except (ValueError, TypeError):
                        pass

                # Power draw
                power = gpu_info.get('Average Graphics Package Power (W)') or \
                        gpu_info.get('Power (W)')
                if power is not None:
                    try:
                        readings.append(SensorReading(chip, 'power_draw', float(power), 'W', 'power'))
                    except (ValueError, TypeError):
                        pass

                # Fan speed
                fan = gpu_info.get('Fan Speed (%)') or \
                      gpu_info.get('Fan (RPM)')
                if fan is not None:
                    try:
                        unit = 'RPM' if 'RPM' in str(gpu_info.get('Fan (RPM)', '')) else '%'
                        readings.append(SensorReading(chip, 'fan_speed', float(fan), unit, 'fan'))
                    except (ValueError, TypeError):
                        pass

                # Utilization
                util = gpu_info.get('GPU Use (%)') or \
                       gpu_info.get('GPU Utilization (%)')
                if util is not None:
                    try:
                        readings.append(SensorReading(chip, 'gpu_util', float(util), '%', 'utilization'))
                    except (ValueError, TypeError):
                        pass
        return readings
