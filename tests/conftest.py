# Sensor Monitor - Hardware sensor monitoring for Bitfocus Companion
# Created by Tech127x (https://github.com/tech127x)
# Repository: https://github.com/tech127x/sensor-monitor-ds

import sys
from pathlib import Path
import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture
def sample_config():
    return {
        'companion': {'host': 'localhost', 'port': 8000, 'use_ssl': False},
        'monitoring': {'update_interval': 1, 'max_errors': 5,
                       'variable_prefix': '', 'variable_suffix': ''},
        'logging': {'level': 'INFO', 'file': 'test_monitor.log'},
        'sensors': [],
        'alerts': [],
        'enable_lmsensors': True,
        'enable_nvidia': False,
        'use_libsensors': False,
    }