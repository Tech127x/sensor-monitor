import logging
import subprocess
from typing import Dict
from ..sources.base import SensorReading
from ..companion.client import CompanionClient

class AlertChecker:
    def __init__(self, alerts_config: list, companion: CompanionClient):
        self.alerts = alerts_config
        self.companion = companion
        self.logger = logging.getLogger(__name__)

    def check(self, alert_cfg: Dict, reading: SensorReading, value_str: str):
        condition = alert_cfg.get('condition')
        if not condition:
            return
        try:
            operator = None
            threshold = None
            if '>' in condition:
                operator = 'gt'
                threshold = float(condition.split('>')[1].strip())
            elif '<' in condition:
                operator = 'lt'
                threshold = float(condition.split('<')[1].strip())
            else:
                return
            triggered = (operator == 'gt' and reading.value > threshold) or \
                       (operator == 'lt' and reading.value < threshold)
            if triggered:
                action = alert_cfg.get('action', 'log')
                if action == 'companion_variable':
                    var = alert_cfg.get('variable')
                    val = alert_cfg.get('value', '1')
                    self.companion.set_variable(var, str(val))
                elif action == 'command':
                    cmd = alert_cfg.get('command')
                    if cmd:
                        subprocess.Popen(cmd, shell=True)
                else:
                    self.logger.warning(f"Alert: {reading.chip}/{reading.name} = {value_str} {condition}")
        except Exception as e:
            self.logger.error(f"Alert check failed: {e}")