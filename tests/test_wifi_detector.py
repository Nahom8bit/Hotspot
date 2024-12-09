"""Tests for the WiFi detector module."""
import pytest
import netifaces
from unittest.mock import patch, MagicMock
from wifi_extender.core.wifi_detector import WiFiDetector


@pytest.fixture
def mock_wifi_interface():
    """Mock WiFi interface data."""
    return {
        "wlo1": {
            "name": "wlo1",
            "supports_ap": True,
            "supports_managed": True,
            "current_mode": None,
            "mac_address": "00:11:22:33:44:55",
            "driver": "mt7921",
            "capabilities": {
                "modes": ["managed", "AP", "monitor"],
                "supported_bands": ["2.4GHz", "5GHz"],
                "current_band": "2.4GHz",
                "max_speed": None
            }
        }
    }


@pytest.fixture
def wifi_detector():
    """Create a WiFiDetector instance with mocked data."""
    with patch('netifaces.interfaces') as mock_interfaces:
        mock_interfaces.return_value = ["wlo1", "eth0"]
        detector = WiFiDetector()
        detector.interfaces = mock_wifi_interface()
        return detector


def test_get_suitable_interfaces(wifi_detector, mock_wifi_interface):
    """Test getting suitable interfaces that support both AP and managed modes."""
    suitable = wifi_detector.get_suitable_interfaces()
    assert suitable == ["wlo1"]


def test_get_interface_status(wifi_detector):
    """Test getting interface status."""
    with patch('netifaces.ifaddresses') as mock_addrs:
        mock_addrs.return_value = {
            netifaces.AF_INET: [{"addr": "192.168.1.100"}],
            netifaces.AF_LINK: [{"addr": "00:11:22:33:44:55"}]
        }
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='wlo1     IEEE 802.11  ESSID:"TestNetwork"  Mode:Managed'
            )
            
            status = wifi_detector.get_interface_status("wlo1")
            assert status["active"] is True
            assert status["connected"] is True
            assert status["ssid"] == "TestNetwork"
            assert status["ip_address"] == "192.168.1.100"
            assert status["mode"] == "Managed"


def test_refresh_interfaces(wifi_detector):
    """Test refreshing interface list."""
    with patch('netifaces.interfaces') as mock_interfaces:
        mock_interfaces.return_value = ["wlo1"]
        with patch.object(wifi_detector, '_is_wireless', return_value=True):
            with patch.object(wifi_detector, '_get_interface_info') as mock_info:
                mock_info.return_value = mock_wifi_interface()["wlo1"]
                wifi_detector.refresh_interfaces()
                assert "wlo1" in wifi_detector.interfaces
                assert wifi_detector.interfaces["wlo1"]["supports_ap"] is True 