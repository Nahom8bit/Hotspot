"""Tests for the AP service module."""
import os
import pytest
from unittest.mock import patch, mock_open, MagicMock
from wifi_extender.core.ap_service import APService


@pytest.fixture
def ap_service():
    """Create an APService instance."""
    return APService("wlo1")


def test_configure_ap(ap_service):
    """Test AP configuration."""
    mock_file = mock_open()
    with patch('builtins.open', mock_file):
        success, message = ap_service.configure_ap(
            ssid="TestAP",
            password="testpass123"
        )
        
        assert success is True
        assert "successfully" in message
        mock_file.assert_called_once_with("/tmp/hostapd.conf", "w")
        
        # Check configuration content
        written_data = mock_file().write.call_args[0][0]
        assert "interface=wlo1" in written_data
        assert "ssid=TestAP" in written_data
        assert "wpa=2" in written_data
        assert "wpa_passphrase=testpass123" in written_data


def test_configure_dhcp(ap_service):
    """Test DHCP configuration."""
    mock_file = mock_open()
    with patch('builtins.open', mock_file):
        success, message = ap_service.configure_dhcp()
        
        assert success is True
        assert "successfully" in message
        mock_file.assert_called_once_with("/tmp/dnsmasq.conf", "w")
        
        # Check configuration content
        written_data = mock_file().write.call_args[0][0]
        assert "interface=wlo1" in written_data
        assert "dhcp-range=192.168.4.2,192.168.4.20,12h" in written_data


def test_start_ap(ap_service):
    """Test starting the AP."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        success, message = ap_service.start()
        
        assert success is True
        assert "started successfully" in message
        assert ap_service.is_running is True
        
        # Verify all necessary commands were called
        assert mock_run.call_count >= 5  # IP config, hostapd, and dnsmasq


def test_stop_ap(ap_service):
    """Test stopping the AP."""
    with patch('subprocess.run') as mock_run:
        with patch('os.path.exists', return_value=True):
            with patch('os.remove') as mock_remove:
                mock_run.return_value = MagicMock(returncode=0)
                
                success, message = ap_service.stop()
                
                assert success is True
                assert "stopped successfully" in message
                assert ap_service.is_running is False
                
                # Verify cleanup
                assert mock_remove.call_count == 2  # Both config files


def test_get_connected_clients(ap_service):
    """Test getting connected client information."""
    mock_leases = """1645000000 00:11:22:33:44:55 192.168.4.2 android-phone 01:23:45:67:89:ab
1645000001 aa:bb:cc:dd:ee:ff 192.168.4.3 laptop *"""
    
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=mock_leases)):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="""Station 00:11:22:33:44:55 (on wlo1)
                    signal: -50 dBm
                    Station aa:bb:cc:dd:ee:ff (on wlo1)
                    signal: -65 dBm"""
                )
                
                clients = ap_service.get_connected_clients()
                
                assert len(clients) == 2
                assert clients[0]["mac_address"] == "00:11:22:33:44:55"
                assert clients[0]["ip_address"] == "192.168.4.2"
                assert clients[0]["hostname"] == "android-phone"
                assert clients[0]["signal_strength"] == "-50 dBm" 