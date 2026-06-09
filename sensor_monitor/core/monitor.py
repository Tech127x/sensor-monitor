# Sensor Monitor - Hardware sensor monitoring for Bitfocus Companion
# Created by Tech127x (https://github.com/tech127x)
# Repository: https://github.com/tech127x/sensor-monitor-ds

import logging
import time
from typing import List, Optional

from ..companion.client import CompanionClient
from ..sources.amd import AmdGpuSource
from ..sources.base import SensorReading
from ..sources.cpu_sysfs import CpuSysfsSource
from ..sources.disk import DiskTempSource
from ..sources.lmsensors import LmSensorsSource
from ..sources.nvidia import NvidiaSmiSource
from ..sources.nvme import NvmeTempSource
from ..sources.procstat import ProcStatSource
from ..utils.alerts import AlertChecker
from ..utils.helpers import normalize_hardware_key
from .config import Config


class SensorMonitor:
    def __init__(self, config_file: str):
        self.config = Config(config_file)
        self.logger = logging.getLogger(__name__)

        # Force subprocess if libsensors not available (to avoid naming mismatch)
        try:
            import sensors  # noqa  # type: ignore[import]

            self._has_libsensors = True
        except ImportError:
            self._has_libsensors = False
            # Override config setting to use subprocess
            if self.config.config.get("use_libsensors", True):
                self.config.config["use_libsensors"] = False
                self.logger.info(
                    "libsensors not installed – forcing subprocess mode (use_libsensors=false)"
                )

        self.sources = self._init_sources()
        self.companion = CompanionClient(**self.config.companion_config)
        self.alert_checker = AlertChecker(self.config.alerts, self.companion)
        self.mappings = self.config.sensor_mappings
        self.prefix = self.config.monitoring.get("variable_prefix", "")
        self.suffix = self.config.monitoring.get("variable_suffix", "")
        self.update_interval = self.config.monitoring.get("update_interval", 1)
        self.max_errors = self.config.monitoring.get("max_errors", 5)
        self.running = False
        self.error_count = 0

        # Validate and repair sensor mappings against current readings
        initial_readings = self.read_all()
        self.config.repair_sensor_mappings(initial_readings)
        # Refresh mappings in case repair changed them
        self.mappings = self.config.sensor_mappings

        self.logger.info(f"Loaded {len(self.mappings)} sensor mappings")
        self.logger.info(f"Companion URL: {self.companion.base_url}")

    def _init_sources(self):
        sources = []
        if self.config.enable_lmsensors:
            sources.append(LmSensorsSource(use_lib=self.config.use_libsensors))
        if self.config.enable_nvidia:
            sources.append(NvidiaSmiSource(cache_seconds=2.0))
        if self.config.enable_amd:
            sources.append(AmdGpuSource())
        if self.config.enable_disk_temp:
            sources.append(DiskTempSource())
        if self.config.enable_cpu_sysfs:
            sources.append(CpuSysfsSource())
        if self.config.enable_cpu_usage:
            sources.append(ProcStatSource())
        if self.config.enable_nvme:
            sources.append(NvmeTempSource())
        return sources

    def read_all(self) -> List[SensorReading]:
        readings = []
        for src in self.sources:
            try:
                readings.extend(src.read())
            except Exception as e:
                self.logger.error(f"Source {src.name()} failed: {e}")
        return readings

    def _find_reading(
        self, readings: List[SensorReading], chip: str, sensor: str
    ) -> Optional[SensorReading]:
        key = normalize_hardware_key(chip, sensor)
        for r in readings:
            if normalize_hardware_key(r.chip, r.name) == key:
                return r
        # Fuzzy match: the chip name may have changed (common after reboot for USB HID devices).
        # Only match when the chip prefix is the same (e.g. highflownext-hid-3-a -> highflownext-hid-2-a)
        # to avoid matching generic sensor names (temp1, fan1) across different chips.
        chip_prefix = (
            chip.split("-")[0].strip().lower() if "-" in chip else chip.strip().lower()
        )
        sensor_name = sensor.strip().lower()
        matches = [
            r
            for r in readings
            if r.name.strip().lower() == sensor_name
            and (
                r.chip.strip().lower().startswith(chip_prefix)
                or chip_prefix.startswith(r.chip.strip().lower())
            )
        ]
        if len(matches) == 1:
            return matches[0]
        return None

    def update_variables(self) -> int:
        readings = self.read_all()
        if not readings:
            self.logger.warning("No sensor readings")
            return 0

        success = 0
        for mapping in self.mappings:
            if not mapping.get("enabled", True):
                continue
            reading = self._find_reading(readings, mapping["chip"], mapping["sensor"])
            if reading is None:
                self.logger.warning(
                    f"Sensor not found: {mapping['chip']}/{mapping['sensor']}"
                )
                continue
            # Auto-repair chip name if it changed (common for USB HID devices after reboot)
            if mapping["chip"] != reading.chip or mapping["sensor"] != reading.name:
                old_key = normalize_hardware_key(mapping["chip"], mapping["sensor"])
                self.logger.info(
                    f"Auto-repaired mapping: {mapping['chip']}/{mapping['sensor']} -> {reading.chip}/{reading.name}"
                )
                mapping["chip"] = reading.chip
                mapping["sensor"] = reading.name
                # Persist the repair to disk so the TUI picks it up too
                import yaml

                try:
                    with open(self.config.config_file, "r") as f:
                        raw = yaml.safe_load(f) or {}
                    if "sensors" in raw:
                        for sensor_entry in raw["sensors"]:
                            if isinstance(sensor_entry, dict):
                                ks = normalize_hardware_key(
                                    sensor_entry.get("chip", ""),
                                    sensor_entry.get("sensor", ""),
                                )
                                if ks[0] and ks[1] and ks == old_key:
                                    sensor_entry["chip"] = reading.chip
                                    sensor_entry["sensor"] = reading.name
                                    break
                        with open(self.config.config_file, "w") as f:
                            yaml.dump(
                                raw,
                                f,
                                default_flow_style=False,
                                sort_keys=False,
                                allow_unicode=True,
                            )
                except Exception as e:
                    self.logger.error(f"Failed to persist auto-repaired config: {e}")

            value = reading.value
            if "divide_by" in mapping and mapping["divide_by"]:
                value = value / mapping["divide_by"]

            fmt = mapping.get("format", "{value}")
            try:
                value_str = fmt.format(value=value)
            except Exception:
                value_str = str(value)

            var_name = mapping["variable"]
            if self.prefix and not var_name.startswith(self.prefix):
                var_name = self.prefix + var_name
            if self.suffix and not var_name.endswith(self.suffix):
                var_name = var_name + self.suffix

            self.logger.info(
                f"Setting {var_name} = {value_str} (from {reading.chip}/{reading.name})"
            )

            if self.companion.set_variable(var_name, value_str):
                success += 1
            else:
                self.logger.error(f"Failed to set {var_name}")

            if "alert" in mapping:
                self.alert_checker.check(mapping["alert"], reading, value_str)

        return success

    def reload_config(self):
        self.logger.info("Reloading configuration")
        self.config = Config(self.config.config_file)
        self.mappings = self.config.sensor_mappings
        self.prefix = self.config.monitoring.get("variable_prefix", "")
        self.suffix = self.config.monitoring.get("variable_suffix", "")
        self.update_interval = self.config.monitoring.get("update_interval", 1)
        self.max_errors = self.config.monitoring.get("max_errors", 5)
        self.alert_checker = AlertChecker(self.config.alerts, self.companion)
        # Re-validate sensor mappings after reload
        readings = self.read_all()
        self.config.repair_sensor_mappings(readings)
        self.mappings = self.config.sensor_mappings  # refresh after potential repair
        self.logger.info(f"Reloaded: {len(self.mappings)} sensor mappings")

    def run(self):
        self.running = True
        self.logger.info("Monitor starting")

        if self.companion.ensure_connected():
            self.logger.info("Connected to Companion")
        else:
            self.logger.warning("Could not connect to Companion")

        self.logger.info(f"Monitoring {len(self.mappings)} sensors")

        while self.running:
            try:
                updated = self.update_variables()
                if updated > 0:
                    self.error_count = 0
                else:
                    self.error_count += 1
                    if self.error_count >= self.max_errors:
                        self.logger.error("Too many errors, stopping")
                        break
                time.sleep(self.update_interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.exception(f"Unhandled error: {e}")
                self.error_count += 1
                if self.error_count >= self.max_errors:
                    break
                time.sleep(self.update_interval)
        self.logger.info("Monitor stopped")
