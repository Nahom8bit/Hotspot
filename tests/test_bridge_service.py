"""Tests for the bridge service module."""
import pytest
from unittest.mock import patch, mock_open, MagicMock
from wifi_extender.core.bridge_service import BridgeService


@pytest.fixture
def bridge_service():
    """Create a BridgeService instance."""
    return BridgeService("wlo1", "wlo1_ap0")


def test_setup_bridge(bridge_service):
    """Test bridge interface setup."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        success, message = bridge_service.setup_bridge()
        
        assert success is True
        assert "successfully" in message
        assert mock_run.call_count == 3  # Create bridge, add interface, set up


def test_setup_routing(bridge_service):
    """Test routing configuration."""
    mock_file = mock_open()
    with patch('builtins.open', mock_file):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            success, message = bridge_service.setup_routing()
            
            assert success is True
            assert "successfully" in message
            assert mock_run.call_count == 3  # Three iptables rules
            mock_file().write.assert_called_once_with("1")


def test_start_bridge_service(bridge_service):
    """Test starting the bridge service."""
    with patch.object(bridge_service, 'setup_bridge') as mock_bridge:
        with patch.object(bridge_service, 'setup_routing') as mock_routing:
            mock_bridge.return_value = (True, "Bridge setup success")
            mock_routing.return_value = (True, "Routing setup success")
            
            success, message = bridge_service.start()
            
            assert success is True
            assert "started successfully" in message
            assert bridge_service.is_running is True
            mock_bridge.assert_called_once()
            mock_routing.assert_called_once()


def test_stop_bridge_service(bridge_service):
    """Test stopping the bridge service."""
    bridge_service._iptables_rules = [
        ["iptables", "-t", "nat", "-A", "POSTROUTING", "-j", "MASQUERADE"]
    ]
    
    mock_file = mock_open()
    with patch('builtins.open', mock_file):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            success, message = bridge_service.stop()
            
            assert success is True
            assert "stopped successfully" in message
            assert bridge_service.is_running is False
            mock_file().write.assert_called_once_with("0")


def test_get_bridge_status(bridge_service):
    """Test getting bridge status."""
    mock_file = mock_open(read_data="1")
    with patch('builtins.open', mock_file):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="MASQUERADE  all  --  0.0.0.0/0  wlo1"),
                MagicMock(returncode=0, stdout="bridge info")
            ]
            
            status = bridge_service.get_bridge_status()
            
            assert isinstance(status, dict)
            assert status["forwarding_enabled"] is True
            assert status["nat_enabled"] is True
            assert status["bridge_active"] is True


def test_cleanup_bridge(bridge_service):
    """Test bridge cleanup."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        bridge_service.cleanup_bridge()
        
        assert mock_run.call_count == 2  # Remove interface and delete bridge 