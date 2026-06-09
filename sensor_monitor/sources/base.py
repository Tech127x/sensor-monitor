# Sensor Monitor - Hardware sensor monitoring for Bitfocus Companion
# Created by Tech127x (https://github.com/tech127x)
# Repository: https://github.com/tech127x/sensor-monitor-ds

from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass

@dataclass
class SensorReading:
    chip: str
    name: str
    value: float
    unit: str
    category: str

class SensorSource(ABC):
    @abstractmethod
    def read(self) -> List[SensorReading]:
        pass

    @abstractmethod
    def name(self) -> str:
        pass