import os
import logging
import subprocess
import shlex
from typing import Dict, Union, List
from ..sources.base import SensorReading
from ..companion.client import CompanionClient

logger = logging.getLogger(__name__)

# Allowlist of safe alert commands (executable basenames only)
ALLOWED_ALERT_COMMANDS = {
    'notify-send',
    'systemctl',
    'loginctl',
    'pkexec',
    'zenity',
    'kdialog',
    'xmessage',
    'mail',
    'sendmail',
    'curl',
    'wget',
}

class AlertChecker:
    def __init__(self, alerts_config: list, companion: CompanionClient):
        self.alerts = alerts_config
        self.companion = companion
        self.logger = logging.getLogger(__name__)

    def _is_command_allowed(self, cmd: List[str]) -> bool:
        """Check if the command executable is in the allowlist."""
# Sensor Monitor - Hardware sensor monitoring for Bitfocus Companion
# Created by Tech127x (https://github.com/tech127x)
# Repository: https://github.com/tech127x/sensor-monitor-ds

        if not cmd:
            return False
        exe = os.path.basename(cmd[0])
        return exe in ALLOWED_ALERT_COMMANDS

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
                    cmd_raw = alert_cfg.get('command')
                    if cmd_raw:
                        if isinstance(cmd_raw, str):
                            # Split safely, no shell
                            cmd = shlex.split(cmd_raw)
                        elif isinstance(cmd_raw, list):
                            cmd = cmd_raw
                        else:
                            self.logger.error(f"Invalid command type: {type(cmd_raw)}")
                            return
                        if not self._is_command_allowed(cmd):
                            self.logger.warning(f"Alert command not in allowlist: {cmd[0] if cmd else '(empty)'}")
                            return
                        try:
                            subprocess.run(cmd, shell=False, check=False)
                        except Exception as e:
                            self.logger.error(f"Alert command failed: {e}")
                else:
                    self.logger.warning(f"Alert: {reading.chip}/{reading.name} = {value_str} {condition}")
        except Exception as e:
            self.logger.error(f"Alert check failed: {e}")
