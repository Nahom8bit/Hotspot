"""Tests for the main window."""
import pytest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication
from wifi_extender.gui.main_window import MainWindow


@pytest.fixture
def app(qapp):
    """Create a Qt application instance."""
    return qapp


@pytest.fixture
def main_window(app):
    """Create a MainWindow instance."""
    with patch('wifi_extender.gui.main_window.WiFiDetector') as mock_detector:
        mock_detector.return_value.get_suitable_interfaces.return_value = ["wlo1"]
        window = MainWindow()
        return window


def test_window_title(main_window):
    """Test window title."""
    assert main_window.windowTitle() == "WiFi Extender"


def test_interface_selection(main_window):
    """Test interface selection combo box."""
    assert main_window.interface_combo.count() == 1
    assert main_window.interface_combo.currentText() == "wlo1"


def test_initialize_services(main_window):
    """Test service initialization."""
    with patch.object(main_window, 'interface_manager') as mock_manager:
        mock_manager.create_virtual_interface.return_value = (True, "Success")
        
        main_window.initialize_services()
        
        assert main_window.interface == "wlo1"
        assert main_window.connection_manager is not None
        assert main_window.ap_service is not None
        assert main_window.bridge_service is not None


def test_scan_networks(main_window):
    """Test network scanning."""
    mock_networks = [
        {
            "ssid": "Test Network",
            "quality": "70/70",
            "security": "WPA2"
        }
    ]
    
    main_window.connection_manager = MagicMock()
    main_window.connection_manager.scan_networks.return_value = mock_networks
    
    main_window.scan_networks()
    
    assert main_window.networks_table.rowCount() == 1
    assert main_window.networks_table.item(0, 0).text() == "Test Network"
    assert main_window.networks_table.item(0, 1).text() == "70/70"
    assert main_window.networks_table.item(0, 2).text() == "WPA2"


def test_start_ap(main_window):
    """Test starting the access point."""
    main_window.ap_service = MagicMock()
    main_window.bridge_service = MagicMock()
    
    main_window.ap_ssid_input.setText("Test AP")
    main_window.ap_password_input.setText("password123")
    
    main_window.ap_service.configure_ap.return_value = (True, "Success")
    main_window.ap_service.configure_dhcp.return_value = (True, "Success")
    main_window.ap_service.start.return_value = (True, "Success")
    main_window.bridge_service.start.return_value = (True, "Success")
    
    main_window.start_ap()
    
    main_window.ap_service.configure_ap.assert_called_once()
    main_window.ap_service.configure_dhcp.assert_called_once()
    main_window.ap_service.start.assert_called_once()
    main_window.bridge_service.start.assert_called_once() 