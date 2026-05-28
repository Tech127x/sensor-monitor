import pytest
from unittest.mock import patch, MagicMock
from sensor_monitor.sources.nvidia import NvidiaSmiSource

class TestNvidiaSmiSource:
    @pytest.fixture
    def source(self):
        return NvidiaSmiSource(cache_seconds=0)
    
    def test_csv_line_parsing(self, source):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "0,GPU-abc123,45,78,120.5,65,1024,8192\n"
        mock_result.stderr = ""
        with patch('subprocess.run', return_value=mock_result):
            readings = source.read()
        assert len(readings) == 6
        temp = [r for r in readings if r.name == 'gpu_temp'][0]
        assert temp.value == 45.0
        assert temp.unit == '°C'
    
    def test_empty_output(self, source):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch('subprocess.run', return_value=mock_result):
            readings = source.read()
        assert len(readings) == 0
    
    def test_n_a_values(self, source):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "0,GPU-abc123,45,N/A,N/A,N/A,N/A,N/A\n"
        with patch('subprocess.run', return_value=mock_result):
            readings = source.read()
        assert len(readings) == 1
        assert readings[0].name == 'gpu_temp'