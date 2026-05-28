import re
from typing import Tuple

def sanitize_variable_name(name: str) -> str:
    name = re.sub(r'^\$\(custom:\)?', '', name)
    name = re.sub(r'\)$', '', name)
    name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    if name and name[0].isdigit():
        name = '_' + name
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    if not name:
        name = 'variable'
    return name.lower()

def get_unit(sensor_name: str, chip: str = '') -> str:
    name_lower = sensor_name.lower()
    
    # Voltage - check BEFORE fan since "Fan 1 voltage" contains both
    if any(x in name_lower for x in [
        'voltage', 'vcore', 'vdd', 'volt', 'avcc', 'avsb', 'vbat',
        'dram', 'chipset', 'cpu soc', 'cpu sa', 'cpu 1p8', 'cpu vddp',
        '+12v', '+5v', '+3.3v'
    ]):
        return 'V'
    
    # Temperature
    if any(x in name_lower for x in ['temp', 'tctl', 'tdie', 'tccd', 'coolant', 'composite']):
        return '°C'
    
    if name_lower.startswith('sensor ') and name_lower[7:].isdigit():
        if 'nvme' in chip.lower() or 'pci' in chip.lower():
            return '°C'
    
    # Fan speed
    if any(x in name_lower for x in ['fan', 'rpm', 'pump']):
        return 'RPM'
    
    # Flow rate
    if 'flow' in name_lower:
        return 'dL/h'
    
    # Current
    if any(x in name_lower for x in ['current', 'curr', 'amp', 'ma']):
        return 'A'
    
    # Power
    if any(x in name_lower for x in ['power', 'watt', 'dissipated']):
        return 'W'
    
    # PWM/percentage
    if 'pwm' in name_lower:
        return '%'
    
    # Conductivity
    if 'conductivity' in name_lower:
        return 'nS/cm'
    
    # Water quality
    if 'quality' in name_lower:
        return '%'
    
    return ''

def get_category(unit: str) -> str:
    mapping = {
        '°C': 'temperature', 'RPM': 'fan', 'V': 'voltage',
        'A': 'current', 'W': 'power', '%': 'utilization',
        'MHz': 'other', 'MiB': 'memory', 'dL/h': 'other',
        'nS/cm': 'other', 'kW': 'power',
    }
    return mapping.get(unit, 'other')

def normalize_hardware_key(chip: str, sensor: str) -> Tuple[str, str]:
    return (str(chip).strip().casefold(), str(sensor).strip().casefold())

def repair_misindented_yaml(raw: str) -> str:
    lines = raw.splitlines()
    out = []
    in_sensors = False
    for line in lines:
        if line.strip().startswith('sensors:'):
            in_sensors = True
            out.append(line)
            continue
        if in_sensors and line.strip().startswith('- variable:') and not line.startswith('  '):
            out.append('  ' + line.lstrip())
        else:
            out.append(line)
    return '\n'.join(out)

def read_sysfs_text(path, limit=256) -> str:
    try:
        with open(path, 'r') as f:
            return f.read(limit).strip()
    except:
        return ''