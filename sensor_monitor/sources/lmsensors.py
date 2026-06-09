# Sensor Monitor - Hardware sensor monitoring for Bitfocus Companion
# Created by Tech127x (https://github.com/tech127x)
# Repository: https://github.com/tech127x/sensor-monitor-ds

import json
import subprocess
import logging
from typing import List, Dict, Optional
from .base import SensorSource, SensorReading
from ..utils.helpers import get_unit, get_category

logger = logging.getLogger(__name__)

class LmSensorsSource(SensorSource):
    def __init__(self, use_lib: bool = True):
        self.use_lib = use_lib
        self._available = self._check()
        if self._available:
            logger.info(f"lm-sensors available (using {'libsensors' if use_lib else 'subprocess'})")
        else:
            logger.warning("lm-sensors not available")

    def _check(self) -> bool:
        if self.use_lib:
            try:
                import sensors
                sensors.init()
                chips = sensors.get_detected_chips()
                chip_count = len(list(chips))
                sensors.cleanup()
                logger.info(f"libsensors detected {chip_count} chips")
                return True
            except ImportError:
                logger.info("libsensors not available, falling back to subprocess")
            except Exception as e:
                logger.warning(f"libsensors check failed: {e}")
        
        try:
            result = subprocess.run(['sensors', '-j'], capture_output=True, check=True, timeout=30)
            logger.info("sensors -j command available")
            return True
        except FileNotFoundError:
            logger.error("'sensors' command not found")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"'sensors -j' failed with code {e.returncode}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("'sensors -j' timed out (30s)")
            return False
        except Exception as e:
            logger.error(f"lm-sensors check failed: {e}")
            return False

    def name(self) -> str:
        return "lm-sensors"

    def read(self) -> List[SensorReading]:
        if not self._available:
            return []
        
        if self.use_lib:
            try:
                return self._read_lib()
            except Exception as e:
                logger.error(f"libsensors read failed: {e}, falling back to subprocess")
                return self._read_subprocess()
        else:
            return self._read_subprocess()

    def _read_lib(self) -> List[SensorReading]:
        import sensors
        sensors.init()
        readings = []
        try:
            for chip in sensors.get_detected_chips():
                for feature in chip:
                    if feature.label:
                        try:
                            value = feature.get_value()
                            if value is not None:
                                unit = get_unit(feature.label, chip.prefix)
                                category = get_category(unit)
                                readings.append(SensorReading(
                                    chip=chip.prefix,
                                    name=feature.label,
                                    value=float(value),
                                    unit=unit,
                                    category=category
                                ))
                        except Exception:
                            pass
        finally:
            sensors.cleanup()
        return readings

    def _read_subprocess(self) -> List[SensorReading]:
        try:
            result = subprocess.run(['sensors', '-j'], capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return []
        except subprocess.TimeoutExpired:
            logger.error("'sensors -j' timed out (30s)")
            return []
        except Exception as e:
            logger.error(f"Failed to run sensors -j: {e}")
            return []
        
        if result.returncode != 0:
            if result.stderr:
                stderr_lines = result.stderr.strip().split('\n')
                for line in stderr_lines[:5]:
                    logger.warning(f"sensors stderr: {line}")
        
        if not result.stdout.strip():
            return []
        
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse sensors JSON: {e}")
            return []
        
        readings = []
        for adapter, adata in data.items():
            if not isinstance(adata, dict):
                continue
            chip = adapter
            for group_name, gdata in adata.items():
                if group_name == 'Adapter' or not isinstance(gdata, dict):
                    continue
                if not gdata:
                    continue
                
                for key, val in gdata.items():
                    if key.startswith('_'):
                        continue
                    
                    # Use the feature key as the sensor name (e.g., "temp1", "fan1")
                    # Strip _input suffix to get the base feature name
                    feature_name = key
                    if key.endswith('_input'):
                        feature_name = key[:-6]  # remove '_input'
                    
                    is_reading = False
                    if '_input' in key or key.endswith('_input'):
                        is_reading = True
                    elif key.startswith('pwm') and not key.endswith('_enable') and not key.endswith('_mode'):
                        is_reading = True
                    elif key.endswith('_pulses'):
                        continue
                    
                    if not is_reading:
                        continue
                    
                    try:
                        if isinstance(val, (int, float)):
                            value = float(val)
                        elif isinstance(val, dict):
                            if key in val:
                                value = float(val[key])
                            elif '_input' in val:
                                value = float(val['_input'])
                            else:
                                found = False
                                for v in val.values():
                                    if isinstance(v, (int, float)):
                                        value = float(v)
                                        found = True
                                        break
                                if not found:
                                    continue
                        elif isinstance(val, str):
                            try:
                                value = float(val)
                            except ValueError:
                                if val.strip().upper() in ('N/A', 'NA', 'NAN', 'NONE', ''):
                                    continue
                                continue
                        else:
                            continue
                        
                        unit = get_unit(feature_name, chip)
                        category = get_category(unit)
                        readings.append(SensorReading(
                            chip=chip, name=feature_name, value=value, unit=unit, category=category
                        ))
                    except (ValueError, TypeError):
                        continue
        
        logger.info(f"subprocess: processed {len(data)} adapters, found {len(readings)} readings")
        return readings
