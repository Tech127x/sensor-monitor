"""Sensor Discovery Module - discovers sensors and manages config files."""

import os
import re
import sys
from typing import Dict, List, Set, Tuple

import yaml

from ..sources.amd import AmdGpuSource
from ..sources.base import SensorReading
from ..sources.cpu_sysfs import CpuSysfsSource
from ..sources.disk import DiskTempSource
from ..sources.lmsensors import LmSensorsSource
from ..sources.nvidia import NvidiaSmiSource
from ..sources.procstat import ProcStatSource
from ..utils.helpers import (
    normalize_hardware_key,
    repair_misindented_yaml,
    sanitize_variable_name,
)


class DiscoveredSensor:
    """A discovered sensor with human-friendly metadata."""

    def __init__(self, reading: SensorReading, description: str = ""):
        self.reading = reading
        self.description = description
        self.simple_name = self._make_simple_name()

    def _make_simple_name(self) -> str:
        name = self.reading.name.replace("_", " ").title()
        name = re.sub(r"\s+Temp$", "", name, flags=re.I)
        name = re.sub(r"\s+Sensor$", "", name, flags=re.I)
        return name

    @property
    def chip(self) -> str:
        return self.reading.chip

    @property
    def sensor_group(self) -> str:
        return self.reading.name

    @property
    def unit(self) -> str:
        return self.reading.unit

    @property
    def category(self) -> str:
        return self.reading.category

    @property
    def current_value(self) -> float:
        return self.reading.value


class SensorDiscovery:
    """Discovers and catalogs all available sensors."""

    SENSOR_NAME_MAP = {
        "tctl": (
            "CPU Temp (Tctl)",
            "temperature",
            "CPU die temperature control reading",
        ),
        "tdie": ("CPU Temp (Tdie)", "temperature", "CPU die actual temperature"),
        "tccd1": ("CPU CCD1 Temp", "temperature", "CPU Core Complex Die 1 temperature"),
        "tccd2": ("CPU CCD2 Temp", "temperature", "CPU Core Complex Die 2 temperature"),
        "tccd3": ("CPU CCD3 Temp", "temperature", "CPU Core Complex Die 3 temperature"),
        "tccd4": ("CPU CCD4 Temp", "temperature", "CPU Core Complex Die 4 temperature"),
        "gpu_temp": ("GPU Temp", "temperature", "Graphics card temperature"),
        "edge": ("GPU Edge Temp", "temperature", "GPU edge/hotspot temperature"),
        "junction": ("GPU Junction Temp", "temperature", "GPU junction/hottest point"),
        "mem": ("GPU Memory Temp", "temperature", "GPU memory temperature"),
        "hotspot": ("GPU Hotspot", "temperature", "GPU hotspot temperature"),
        "fan1": ("Fan 1 (CPU)", "fan", "CPU or primary system fan"),
        "fan2": ("Fan 2", "fan", "Secondary system fan"),
        "fan3": ("Fan 3", "fan", "Tertiary system fan"),
        "cpu_fan": ("CPU Fan", "fan", "CPU cooler fan speed"),
        "pump": ("Pump Speed", "fan", "Liquid cooling pump speed"),
        "vcore": ("CPU Core Voltage", "voltage", "CPU core supply voltage"),
        "power.draw": ("GPU Power Draw", "power", "Graphics card power consumption"),
        "utilization.gpu": ("GPU Utilization", "utilization", "GPU usage percentage"),
        "memory.used": ("GPU Memory Used", "memory", "Allocated GPU memory"),
        "memory.total": ("GPU Memory Total", "memory", "Total GPU memory"),
    }

    def __init__(self):
        self.sensors: List[DiscoveredSensor] = []

    def discover(self) -> List[DiscoveredSensor]:
        # Force use of subprocess (sensors -j) for consistent naming
        # We do this by setting use_lib=False in LmSensorsSource
        sources = [
            LmSensorsSource(use_lib=True),  # will be overridden below
            NvidiaSmiSource(cache_seconds=0),
            AmdGpuSource(),
            DiskTempSource(),
            CpuSysfsSource(),
            ProcStatSource(),
        ]
        # Override the LmSensorsSource to force subprocess (more reliable naming)
        for src in sources:
            if isinstance(src, LmSensorsSource):
                src.use_lib = False
                break

        all_readings: List[SensorReading] = []
        for src in sources:
            try:
                readings = src.read()
                all_readings.extend(readings)
            except Exception as e:
                print(f"Warning: source {src.name()} failed: {e}", file=sys.stderr)

        self.sensors = []
        for r in all_readings:
            ds = DiscoveredSensor(r)
            key = r.name.lower()
            if key in self.SENSOR_NAME_MAP:
                name, cat, desc = self.SENSOR_NAME_MAP[key]
                ds.simple_name = name
                ds.reading.category = cat
                ds.description = desc
            else:
                ds.description = f"{ds.category} sensor"
            self.sensors.append(ds)

        self.sensors.sort(key=lambda s: (s.category, s.simple_name))
        return self.sensors

    def sorted_sensors(self) -> List[DiscoveredSensor]:
        return sorted(self.sensors, key=lambda s: (s.category, s.simple_name))

    def assign_default_variables(self, sensors: List[DiscoveredSensor]) -> List[str]:
        used: Set[str] = set()
        out = []
        for s in sensors:
            base = sanitize_variable_name(s.simple_name)
            name = base
            if name not in used:
                used.add(name)
                out.append(name)
                continue
            alt = sanitize_variable_name(f"{base}_{s.chip.split('-')[0]}")
            if alt not in used:
                used.add(alt)
                out.append(alt)
                continue
            n = 2
            while True:
                cand = sanitize_variable_name(f"{base}_{n}")
                if cand not in used:
                    used.add(cand)
                    out.append(cand)
                    break
                n += 1
        return out

    @staticmethod
    def companion_format_yaml(sensor: DiscoveredSensor) -> str:
        if sensor.unit == "RPM":
            fmt = "{value:.0f}"
        elif sensor.unit == "%" and sensor.category == "utilization":
            fmt = "{value:.0f}"
        else:
            fmt = "{value:.1f}"
        suffix = "" if sensor.unit == "%" else sensor.unit
        return f"{fmt}{suffix}"

    def _load_config(self, config_file: str) -> Dict:
        if not os.path.exists(config_file):
            return {}
        with open(config_file, "r") as f:
            raw = f.read()
        try:
            return yaml.safe_load(raw) or {}
        except yaml.YAMLError:
            repaired = repair_misindented_yaml(raw)
            with open(config_file, "w") as f:
                f.write(repaired)
            return yaml.safe_load(repaired) or {}

    def load_config_hardware_keys(self, config_file: str) -> Set[Tuple[str, str]]:
        cfg = self._load_config(config_file)
        out = set()
        for entry in cfg.get("sensors", []):
            if isinstance(entry, dict):
                chip = entry.get("chip")
                sensor = entry.get("sensor")
                if chip and sensor:
                    out.add(normalize_hardware_key(chip, sensor))
        return out

    def load_config_divide_by(self, config_file: str) -> Dict[Tuple[str, str], int]:
        cfg = self._load_config(config_file)
        out = {}
        for entry in cfg.get("sensors", []):
            if not isinstance(entry, dict):
                continue
            chip = entry.get("chip")
            sensor = entry.get("sensor")
            div = entry.get("divide_by")
            if chip and sensor and div is not None:
                try:
                    div_int = int(div)
                    if div_int >= 2:
                        out[normalize_hardware_key(chip, sensor)] = div_int
                except (TypeError, ValueError):
                    pass
        return out

    def load_config_unit_overrides(
        self, config_file: str
    ) -> Dict[Tuple[str, str], str]:
        cfg = self._load_config(config_file)
        out = {}
        for entry in cfg.get("sensors", []):
            if not isinstance(entry, dict):
                continue
            chip = entry.get("chip")
            sensor = entry.get("sensor")
            unit = entry.get("unit")
            if chip and sensor and unit and isinstance(unit, str):
                out[normalize_hardware_key(chip, sensor)] = unit
        return out

    def load_config_variable_names(
        self, config_file: str
    ) -> Dict[Tuple[str, str], str]:
        """Load saved variable names from config.

        Returns a dict mapping (chip, sensor_group) -> saved variable name.
        """
        cfg = self._load_config(config_file)
        out = {}
        for entry in cfg.get("sensors", []):
            if not isinstance(entry, dict):
                continue
            chip = entry.get("chip")
            sensor = entry.get("sensor")
            variable = entry.get("variable")
            if chip and sensor and variable and isinstance(variable, str):
                out[normalize_hardware_key(chip, sensor)] = variable
        return out
