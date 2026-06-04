import os
import yaml
import logging
from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..sources.base import SensorReading

from ..utils.helpers import repair_misindented_yaml, normalize_hardware_key

class Config:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config = self._load()

    def _load(self) -> Dict[str, Any]:
        config_dir = os.path.dirname(os.path.abspath(self.config_file))
        
        defaults = {
            'companion': {'host': 'localhost', 'port': 8000, 'use_ssl': False},
            'monitoring': {'update_interval': 1, 'max_errors': 5,
                           'variable_prefix': '', 'variable_suffix': ''},
            'logging': {'level': 'INFO', 'file': os.path.join(config_dir, 'sensor_monitor.log')},
            'sensors': [],
            'alerts': [],
            'enable_lmsensors': True,
            'enable_nvidia': True,
            'enable_amd': False,
            'enable_disk_temp': False,
            'enable_cpu_sysfs': True,
            'enable_cpu_usage': True,
            'enable_nvme': True,
            'use_libsensors': False,
        }
        
        if not os.path.exists(self.config_file):
            return defaults
        
        try:
            with open(self.config_file, 'r') as f:
                raw = f.read()
            try:
                cfg = yaml.safe_load(raw) or {}
            except yaml.YAMLError:
                repaired = repair_misindented_yaml(raw)
                cfg = yaml.safe_load(repaired) or {}
                with open(self.config_file, 'w') as f:
                    f.write(repaired)
            
            result = defaults.copy()
            for key, val in cfg.items():
                if key in result and isinstance(result[key], dict) and isinstance(val, dict):
                    result[key].update(val)
                else:
                    result[key] = val
            return result
        except Exception as e:
            logging.error(f"Failed to load config {self.config_file}: {e}")
            return defaults

    def repair_sensor_mappings(self, current_readings: List['SensorReading']) -> bool:
        """
        Attempt to fix sensor mappings where chip/sensor names don't match current readings.
        Returns True if config was modified and saved.
        """
        # Build lookup from normalized (chip, sensor) to the actual reading
        lookup = {normalize_hardware_key(r.chip, r.name): r for r in current_readings}
        repaired = False
        for entry in self.config.get('sensors', []):
            if not isinstance(entry, dict):
                continue
            chip = entry.get('chip', '')
            sensor = entry.get('sensor', '')
            if not chip or not sensor:
                continue
            key = normalize_hardware_key(chip, sensor)
            if key not in lookup:
                # Try to match by sensor name only (case-insensitive, stripped)
                sensor_name = sensor.strip().lower()
                matches = [r for r in current_readings if r.name.strip().lower() == sensor_name]
                if len(matches) == 1:
                    # Unique match – update chip and sensor
                    entry['chip'] = matches[0].chip
                    entry['sensor'] = matches[0].name
                    repaired = True
                    logging.info(f"Repaired sensor mapping: {key} -> {normalize_hardware_key(matches[0].chip, matches[0].name)}")
        if repaired:
            # Write back the repaired config
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            logging.info("Config file automatically repaired and saved.")
        return repaired

    @property
    def sensor_mappings(self) -> List[Dict]:
        return self.config.get('sensors', [])

    @property
    def companion_config(self) -> Dict:
        return self.config['companion']

    @property
    def monitoring(self) -> Dict:
        return self.config['monitoring']

    @property
    def alerts(self) -> List[Dict]:
        return self.config.get('alerts', [])

    @property
    def enable_lmsensors(self) -> bool:
        return self.config.get('enable_lmsensors', True)

    @property
    def use_libsensors(self) -> bool:
        return self.config.get('use_libsensors', False)

    @property
    def enable_nvidia(self) -> bool:
        return self.config.get('enable_nvidia', True)

    @property
    def enable_amd(self) -> bool:
        return self.config.get('enable_amd', False)

    @property
    def enable_disk_temp(self) -> bool:
        return self.config.get('enable_disk_temp', False)

    @property
    def enable_cpu_sysfs(self) -> bool:
        return self.config.get('enable_cpu_sysfs', True)

    @property
    def enable_cpu_usage(self) -> bool:
        return self.config.get('enable_cpu_usage', True)

    @property
    def enable_nvme(self) -> bool:
        return self.config.get('enable_nvme', True)