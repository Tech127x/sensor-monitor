# Sensor Monitor - Hardware sensor monitoring for Bitfocus Companion
# Created by Tech127x (https://github.com/tech127x)
# Repository: https://github.com/tech127x/sensor-monitor-ds

import logging
import os
import sys
import yaml

def setup_logging(config_file: str, daemon: bool = False):
    try:
        with open(config_file, 'r') as f:
            cfg = yaml.safe_load(f) or {}
        log_cfg = cfg.get('logging', {})
        level = getattr(logging, log_cfg.get('level', 'INFO').upper())
        log_file = log_cfg.get('file', 'sensor_monitor.log')
        if not os.path.isabs(log_file):
            log_file = os.path.join(os.path.dirname(config_file), log_file)
    except:
        level = logging.INFO
        log_file = 'sensor_monitor.log'
    
    handlers = [logging.FileHandler(log_file)]
    if not daemon:
        handlers.append(logging.StreamHandler(sys.stdout))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )