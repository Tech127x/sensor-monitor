"""Configuration utilities for sensor monitor."""
# Sensor Monitor - Hardware sensor monitoring for Bitfocus Companion
# Created by Tech127x (https://github.com/tech127x)
# Repository: https://github.com/tech127x/sensor-monitor-ds

import os
import yaml
from typing import Dict, Any
from .helpers import repair_misindented_yaml

class ConfigManager:
    @staticmethod
    def load_config(config_file: str) -> Dict[str, Any]:
        defaults = {
            'companion': {'host': 'localhost', 'port': 8000, 'use_ssl': False},
            'monitoring': {'update_interval': 1, 'max_errors': 5,
                           'variable_prefix': '', 'variable_suffix': ''},
            'logging': {'level': 'INFO', 'file': 'sensor_monitor.log'},
            'sensors': [],
            'alerts': [],
        }
        if not os.path.exists(config_file):
            return defaults
        try:
            with open(config_file, 'r') as f:
                raw = f.read()
            try:
                cfg = yaml.safe_load(raw) or {}
            except yaml.YAMLError:
                repaired = repair_misindented_yaml(raw)
                cfg = yaml.safe_load(repaired) or {}
                with open(config_file, 'w') as f:
                    f.write(repaired)
            for key, val in defaults.items():
                if key not in cfg:
                    cfg[key] = val
                elif isinstance(val, dict) and isinstance(cfg.get(key), dict):
                    for subk, subv in val.items():
                        if subk not in cfg[key]:
                            cfg[key][subk] = subv
            return cfg
        except Exception:
            return defaults