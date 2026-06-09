"""Tests for the AlertChecker."""
# Sensor Monitor - Hardware sensor monitoring for Bitfocus Companion
# Created by Tech127x (https://github.com/tech127x)
# Repository: https://github.com/tech127x/sensor-monitor-ds

from unittest.mock import patch, MagicMock
from sensor_monitor.utils.alerts import AlertChecker, ALLOWED_ALERT_COMMANDS
from sensor_monitor.sources.base import SensorReading


class TestAlertChecker:
    def test_check_gt_triggered(self):
        checker = AlertChecker([], MagicMock())
        r = SensorReading("t", "s", 85.0, "\u00b0C", "temperature")
        with patch("sensor_monitor.utils.alerts.logger") as l:
            checker.check({"condition": "> 80", "action": "log"}, r, "85")
            l.warning.assert_called_once()

    def test_check_command_disallowed(self):
        checker = AlertChecker([], MagicMock())
        r = SensorReading("t", "s", 85.0, "\u00b0C", "temperature")
        with patch("subprocess.run") as m:
            checker.check({"condition": "> 80", "action": "command", "command": "rm -rf /"}, r, "85")
            m.assert_not_called()

    def test_check_command_allowed(self):
        checker = AlertChecker([], MagicMock())
        r = SensorReading("t", "s", 85.0, "\u00b0C", "temperature")
        with patch("subprocess.run") as m:
            checker.check({"condition": "> 80", "action": "command", "command": "notify-send test"}, r, "85")
            m.assert_called_once()

    def test_allowlist_safe_only(self):
        assert "rm" not in ALLOWED_ALERT_COMMANDS
        assert "notify-send" in ALLOWED_ALERT_COMMANDS
