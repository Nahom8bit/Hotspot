"""Tests for the WiFi Extender daemon service."""
import os
import json
import pytest
from unittest.mock import patch, mock_open, MagicMock, PropertyMock
from wifi_extender.service.daemon import WiFiExtenderDaemon


@pytest.fixture
def daemon_service():
    """Create a WiFiExtenderDaemon instance with mocked paths."""
    with patch('os.makedirs'), patch('logging.basicConfig'):
        with patch('wifi_extender.service.daemon.WiFiDetector') as mock_detector:
            service = WiFiExtenderDaemon()
            # Override paths for testing
            service.config_dir = "/tmp/test/etc/wifi-extender"
            service.run_dir = "/tmp/test/var/run/wifi-extender"
            service.log_dir = "/tmp/test/var/log/wifi-extender"
            service.config_file = os.path.join(service.config_dir, "config.json")
            service.pid_file = os.path.join(service.run_dir, "wifi-extender.pid")
            service.log_file = os.path.join(service.log_dir, "wifi-extender.log")
            return service


def test_load_config(daemon_service):
    """Test configuration loading."""
    mock_config = {
        "upstream": {
            "ssid": "TestNetwork",
            "password": "testpass123"
        },
        "ap": {
            "ssid": "TestAP",
            "password": "appass123",
            "channel": 6
        }
    }
    
    mock_file = mock_open(read_data=json.dumps(mock_config))
    with patch('builtins.open', mock_file):
        with patch('os.path.exists', return_value=True):
            daemon_service.load_config()
            
            assert daemon_service.config == mock_config
            assert daemon_service.config["upstream"]["ssid"] == "TestNetwork"
            assert daemon_service.config["ap"]["ssid"] == "TestAP"


def test_save_config(daemon_service):
    """Test configuration saving."""
    test_config = {
        "upstream": {"ssid": "TestNetwork"},
        "ap": {"ssid": "TestAP"}
    }
    daemon_service.config = test_config.copy()
    
    # Create a mock that captures the written data
    written_data = None
    def mock_write(data):
        nonlocal written_data
        written_data = data
        return len(data)
    
    mock_file = mock_open()
    mock_file.return_value.write.side_effect = mock_write
    
    with patch('builtins.open', mock_file):
        daemon_service.save_config()
        
        mock_file.assert_called_once_with(daemon_service.config_file, 'w')
        assert written_data is not None
        parsed_data = json.loads(written_data)
        assert parsed_data == test_config


def test_initialize_services(daemon_service):
    """Test service initialization."""
    with patch('wifi_extender.service.daemon.WiFiDetector') as MockDetector:
        detector_instance = MockDetector.return_value
        detector_instance.get_suitable_interfaces.return_value = ["wlo1"]
        daemon_service.wifi_detector = detector_instance
        
        # Mock interface manager creation
        with patch('wifi_extender.service.daemon.InterfaceManager') as MockManager:
            manager_instance = MockManager.return_value
            manager_instance.create_virtual_interface.return_value = (True, "Success")
            
            # Mock other service creations
            with patch('wifi_extender.service.daemon.ConnectionManager'), \
                 patch('wifi_extender.service.daemon.APService'), \
                 patch('wifi_extender.service.daemon.BridgeService'):
                
                success = daemon_service.initialize_services()
                
                assert success is True
                assert daemon_service.interface == "wlo1"
                MockManager.assert_called_once_with("wlo1")


def test_start_services(daemon_service):
    """Test starting services."""
    daemon_service.config = {
        "upstream": {
            "ssid": "TestNetwork",
            "password": "testpass123"
        },
        "ap": {
            "ssid": "TestAP",
            "password": "appass123",
            "channel": 6
        }
    }
    
    # Mock all required services
    daemon_service.connection_manager = MagicMock()
    daemon_service.ap_service = MagicMock()
    daemon_service.bridge_service = MagicMock()
    
    # Set success returns
    daemon_service.connection_manager.connect_to_network.return_value = (True, "Success")
    daemon_service.ap_service.configure_ap.return_value = (True, "Success")
    daemon_service.ap_service.configure_dhcp.return_value = (True, "Success")
    daemon_service.ap_service.start.return_value = (True, "Success")
    daemon_service.bridge_service.start.return_value = (True, "Success")
    
    success = daemon_service.start_services()
    
    assert success is True
    daemon_service.connection_manager.connect_to_network.assert_called_once()
    daemon_service.ap_service.configure_ap.assert_called_once()
    daemon_service.ap_service.start.assert_called_once()
    daemon_service.bridge_service.start.assert_called_once()


def test_stop_services(daemon_service):
    """Test stopping services."""
    daemon_service.bridge_service = MagicMock()
    daemon_service.ap_service = MagicMock()
    daemon_service.connection_manager = MagicMock()
    daemon_service.interface_manager = MagicMock()
    
    daemon_service.stop_services()
    
    daemon_service.bridge_service.stop.assert_called_once()
    daemon_service.ap_service.stop.assert_called_once()
    daemon_service.connection_manager.disconnect.assert_called_once()
    daemon_service.interface_manager.delete_virtual_interface.assert_called_once()


def test_handle_signal(daemon_service):
    """Test signal handling."""
    daemon_service.running = True
    daemon_service.handle_signal(15, None)  # SIGTERM
    assert daemon_service.running is False


def test_run_service_loop(daemon_service):
    """Test the main service loop."""
    # Mock service initialization
    with patch.object(daemon_service, 'initialize_services', return_value=True):
        with patch.object(daemon_service, 'start_services', return_value=True):
            with patch.object(daemon_service, 'stop_services') as mock_stop:
                # Mock connection status check
                daemon_service.connection_manager = MagicMock()
                daemon_service.connection_manager.get_connection_status.return_value = {
                    "connected": True
                }
                
                # Mock AP client check
                daemon_service.ap_service = MagicMock()
                daemon_service.ap_service.get_connected_clients.return_value = []
                
                # Run for one iteration
                daemon_service.running = True
                with patch('time.sleep') as mock_sleep:
                    def stop_service(*args):
                        daemon_service.running = False
                    mock_sleep.side_effect = stop_service
                    
                    daemon_service.run()
                    
                    mock_stop.assert_called_once() 