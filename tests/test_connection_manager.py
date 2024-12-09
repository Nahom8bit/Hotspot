"""Tests for the connection manager module."""
import pytest
from unittest.mock import patch, MagicMock
from wifi_extender.core.connection_manager import ConnectionManager


@pytest.fixture
def connection_manager():
    """Create a ConnectionManager instance."""
    return ConnectionManager("wlo1")


def test_scan_networks(connection_manager):
    """Test scanning for available networks."""
    mock_output = """
    Cell 01 - Address: 00:11:22:33:44:55
              ESSID:"TestNetwork1"
              Protocol:IEEE 802.11
              Mode:Master
              Frequency:2.412 GHz
              Encryption key:on
              Quality=70/70
              IE: IEEE 802.11i/WPA2 Version 1
    Cell 02 - Address: AA:BB:CC:DD:EE:FF
              ESSID:"TestNetwork2"
              Protocol:IEEE 802.11
              Mode:Master
              Frequency:2.437 GHz
              Encryption key:off
              Quality=50/70
    """
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_output
        )
        
        networks = connection_manager.scan_networks()
        assert len(networks) == 2
        assert networks[0]["ssid"] == "TestNetwork1"
        assert networks[0]["encrypted"] is True
        assert networks[0]["security"] == "WPA2"
        assert networks[1]["ssid"] == "TestNetwork2"
        assert networks[1]["encrypted"] is False


def test_connect_to_network(connection_manager):
    """Test connecting to a network."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        with patch('builtins.open', create=True) as mock_open:
            with patch.object(connection_manager, 'get_connection_status') as mock_status:
                mock_status.return_value = {
                    "connected": True,
                    "ssid": "TestNetwork",
                    "ip_address": "192.168.1.100"
                }
                
                success, message = connection_manager.connect_to_network(
                    "TestNetwork", "password123"
                )
                
                assert success is True
                assert "Successfully connected" in message
                mock_open.assert_called_once()


def test_disconnect(connection_manager):
    """Test disconnecting from a network."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        success, message = connection_manager.disconnect()
        assert success is True
        assert "Successfully disconnected" in message
        assert connection_manager.current_connection is None


def test_get_connection_status(connection_manager):
    """Test getting connection status."""
    with patch.object(connection_manager.wifi_detector, 'get_interface_status') as mock_status:
        mock_status.return_value = {
            "active": True,
            "connected": True,
            "ssid": "TestNetwork",
            "ip_address": "192.168.1.100",
            "mode": "managed"
        }
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='Quality=70/70  Signal level=-30 dBm  Bit Rate=130 Mb/s'
            )
            
            status = connection_manager.get_connection_status()
            assert status["connected"] is True
            assert status["ssid"] == "TestNetwork"
            assert status["ip_address"] == "192.168.1.100"
            assert "signal_quality" in status
            assert "bit_rate" in status


def test_is_connected(connection_manager):
    """Test checking connection status."""
    with patch.object(connection_manager, 'get_connection_status') as mock_status:
        mock_status.return_value = {"connected": True}
        assert connection_manager.is_connected() is True
        
        mock_status.return_value = {"connected": False}
        assert connection_manager.is_connected() is False 