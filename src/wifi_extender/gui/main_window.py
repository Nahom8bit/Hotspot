"""Main window for the WiFi Extender application."""
import sys
from typing import Optional, Dict, List
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QTabWidget, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QProgressBar, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer
from ..core.wifi_detector import WiFiDetector
from ..core.connection_manager import ConnectionManager
from ..core.interface_manager import InterfaceManager
from ..core.ap_service import APService
from ..core.bridge_service import BridgeService


class MainWindow(QMainWindow):
    """Main window of the WiFi Extender application."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("WiFi Extender")
        self.setMinimumSize(800, 600)

        # Initialize core components
        self.wifi_detector = WiFiDetector()
        self.interface: Optional[str] = None
        self.connection_manager: Optional[ConnectionManager] = None
        self.interface_manager: Optional[InterfaceManager] = None
        self.ap_service: Optional[APService] = None
        self.bridge_service: Optional[BridgeService] = None

        # Setup UI
        self.setup_ui()
        
        # Setup refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_status)
        self.refresh_timer.start(5000)  # Update every 5 seconds

    def setup_ui(self):
        """Setup the user interface."""
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # Create tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Add tabs
        tabs.addTab(self.create_setup_tab(), "Setup")
        tabs.addTab(self.create_connection_tab(), "Connection")
        tabs.addTab(self.create_ap_tab(), "Access Point")
        tabs.addTab(self.create_clients_tab(), "Clients")
        tabs.addTab(self.create_status_tab(), "Status")

    def create_setup_tab(self) -> QWidget:
        """Create the setup tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Interface selection
        group = QGroupBox("Interface Selection")
        group_layout = QVBoxLayout(group)

        self.interface_combo = QComboBox()
        self.refresh_interfaces_button = QPushButton("Refresh Interfaces")
        self.refresh_interfaces_button.clicked.connect(self.refresh_interfaces)

        group_layout.addWidget(QLabel("Select WiFi Interface:"))
        group_layout.addWidget(self.interface_combo)
        group_layout.addWidget(self.refresh_interfaces_button)

        layout.addWidget(group)

        # Initialize button
        self.init_button = QPushButton("Initialize Services")
        self.init_button.clicked.connect(self.initialize_services)
        layout.addWidget(self.init_button)

        # Refresh interfaces on start
        self.refresh_interfaces()

        layout.addStretch()
        return tab

    def create_connection_tab(self) -> QWidget:
        """Create the connection tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Network scan group
        scan_group = QGroupBox("Available Networks")
        scan_layout = QVBoxLayout(scan_group)

        self.networks_table = QTableWidget()
        self.networks_table.setColumnCount(4)
        self.networks_table.setHorizontalHeaderLabels(
            ["SSID", "Signal", "Security", "Connected"]
        )

        scan_button = QPushButton("Scan Networks")
        scan_button.clicked.connect(self.scan_networks)

        scan_layout.addWidget(self.networks_table)
        scan_layout.addWidget(scan_button)
        layout.addWidget(scan_group)

        # Connection group
        conn_group = QGroupBox("Connect to Network")
        conn_layout = QVBoxLayout(conn_group)

        self.ssid_input = QLineEdit()
        self.ssid_input.setPlaceholderText("Network SSID")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        connect_button = QPushButton("Connect")
        connect_button.clicked.connect(self.connect_to_network)
        disconnect_button = QPushButton("Disconnect")
        disconnect_button.clicked.connect(self.disconnect_network)

        conn_layout.addWidget(QLabel("SSID:"))
        conn_layout.addWidget(self.ssid_input)
        conn_layout.addWidget(QLabel("Password:"))
        conn_layout.addWidget(self.password_input)
        conn_layout.addWidget(connect_button)
        conn_layout.addWidget(disconnect_button)

        layout.addWidget(conn_group)
        return tab

    def create_ap_tab(self) -> QWidget:
        """Create the access point tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # AP Configuration
        config_group = QGroupBox("Access Point Configuration")
        config_layout = QVBoxLayout(config_group)

        self.ap_ssid_input = QLineEdit()
        self.ap_ssid_input.setPlaceholderText("Hotspot Name")
        self.ap_password_input = QLineEdit()
        self.ap_password_input.setPlaceholderText("Password (optional)")
        self.ap_password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.channel_combo = QComboBox()
        for i in range(1, 12):
            self.channel_combo.addItem(f"Channel {i}")

        config_layout.addWidget(QLabel("Hotspot Name:"))
        config_layout.addWidget(self.ap_ssid_input)
        config_layout.addWidget(QLabel("Password:"))
        config_layout.addWidget(self.ap_password_input)
        config_layout.addWidget(QLabel("Channel:"))
        config_layout.addWidget(self.channel_combo)

        layout.addWidget(config_group)

        # AP Controls
        control_group = QGroupBox("Controls")
        control_layout = QHBoxLayout(control_group)

        self.start_ap_button = QPushButton("Start Hotspot")
        self.start_ap_button.clicked.connect(self.start_ap)
        self.stop_ap_button = QPushButton("Stop Hotspot")
        self.stop_ap_button.clicked.connect(self.stop_ap)

        control_layout.addWidget(self.start_ap_button)
        control_layout.addWidget(self.stop_ap_button)

        layout.addWidget(control_group)
        layout.addStretch()
        return tab

    def create_clients_tab(self) -> QWidget:
        """Create the clients tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.clients_table = QTableWidget()
        self.clients_table.setColumnCount(4)
        self.clients_table.setHorizontalHeaderLabels(
            ["Hostname", "IP Address", "MAC Address", "Signal"]
        )

        refresh_button = QPushButton("Refresh Clients")
        refresh_button.clicked.connect(self.refresh_clients)

        layout.addWidget(self.clients_table)
        layout.addWidget(refresh_button)
        return tab

    def create_status_tab(self) -> QWidget:
        """Create the status tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Connection Status
        conn_group = QGroupBox("Connection Status")
        conn_layout = QVBoxLayout(conn_group)
        self.conn_status_label = QLabel("Not connected")
        self.conn_signal_bar = QProgressBar()
        self.conn_signal_bar.setRange(0, 100)
        conn_layout.addWidget(self.conn_status_label)
        conn_layout.addWidget(self.conn_signal_bar)
        layout.addWidget(conn_group)

        # AP Status
        ap_group = QGroupBox("Access Point Status")
        ap_layout = QVBoxLayout(ap_group)
        self.ap_status_label = QLabel("Not running")
        self.client_count_label = QLabel("Connected clients: 0")
        ap_layout.addWidget(self.ap_status_label)
        ap_layout.addWidget(self.client_count_label)
        layout.addWidget(ap_group)

        # Bridge Status
        bridge_group = QGroupBox("Bridge Status")
        bridge_layout = QVBoxLayout(bridge_group)
        self.bridge_status_label = QLabel("Not running")
        self.forwarding_status_label = QLabel("IP Forwarding: Disabled")
        bridge_layout.addWidget(self.bridge_status_label)
        bridge_layout.addWidget(self.forwarding_status_label)
        layout.addWidget(bridge_group)

        layout.addStretch()
        return tab

    def refresh_interfaces(self):
        """Refresh the list of available interfaces."""
        self.interface_combo.clear()
        interfaces = self.wifi_detector.get_suitable_interfaces()
        self.interface_combo.addItems(interfaces)

    def initialize_services(self):
        """Initialize all services with selected interface."""
        interface = self.interface_combo.currentText()
        if not interface:
            QMessageBox.warning(self, "Error", "Please select an interface")
            return

        self.interface = interface
        self.connection_manager = ConnectionManager(interface)
        self.interface_manager = InterfaceManager(interface)
        
        # Create virtual interface for AP
        success, message = self.interface_manager.create_virtual_interface()
        if not success:
            QMessageBox.warning(self, "Error", f"Failed to create virtual interface: {message}")
            return

        virtual_interface = f"{interface}_ap0"
        self.ap_service = APService(virtual_interface)
        self.bridge_service = BridgeService(interface, virtual_interface)

        QMessageBox.information(self, "Success", "Services initialized successfully")
        self.status_bar.showMessage("Services initialized")

    def scan_networks(self):
        """Scan for available networks."""
        if not self.connection_manager:
            QMessageBox.warning(self, "Error", "Please initialize services first")
            return

        self.networks_table.setRowCount(0)
        networks = self.connection_manager.scan_networks()
        
        self.networks_table.setRowCount(len(networks))
        for i, network in enumerate(networks):
            self.networks_table.setItem(i, 0, QTableWidgetItem(network["ssid"]))
            self.networks_table.setItem(i, 1, QTableWidgetItem(network["quality"]))
            self.networks_table.setItem(
                i, 2, 
                QTableWidgetItem(network.get("security", "Open"))
            )
            self.networks_table.setItem(
                i, 3,
                QTableWidgetItem("No")
            )

    def connect_to_network(self):
        """Connect to the specified network."""
        if not self.connection_manager:
            QMessageBox.warning(self, "Error", "Please initialize services first")
            return

        ssid = self.ssid_input.text()
        password = self.password_input.text()

        if not ssid:
            QMessageBox.warning(self, "Error", "Please enter network SSID")
            return

        success, message = self.connection_manager.connect_to_network(ssid, password)
        if success:
            QMessageBox.information(self, "Success", "Connected successfully")
            self.status_bar.showMessage(f"Connected to {ssid}")
        else:
            QMessageBox.warning(self, "Error", f"Connection failed: {message}")

    def disconnect_network(self):
        """Disconnect from the current network."""
        if not self.connection_manager:
            return

        success, message = self.connection_manager.disconnect()
        if success:
            self.status_bar.showMessage("Disconnected from network")

    def start_ap(self):
        """Start the access point."""
        if not self.ap_service or not self.bridge_service:
            QMessageBox.warning(self, "Error", "Please initialize services first")
            return

        ssid = self.ap_ssid_input.text()
        password = self.ap_password_input.text() or None
        channel = int(self.channel_combo.currentText().split()[1])

        # Configure and start AP
        success, message = self.ap_service.configure_ap(
            ssid=ssid,
            password=password,
            channel=channel
        )
        if not success:
            QMessageBox.warning(self, "Error", f"AP configuration failed: {message}")
            return

        success, message = self.ap_service.configure_dhcp()
        if not success:
            QMessageBox.warning(self, "Error", f"DHCP configuration failed: {message}")
            return

        success, message = self.ap_service.start()
        if not success:
            QMessageBox.warning(self, "Error", f"AP start failed: {message}")
            return

        # Start bridge
        success, message = self.bridge_service.start()
        if not success:
            self.ap_service.stop()
            QMessageBox.warning(self, "Error", f"Bridge start failed: {message}")
            return

        QMessageBox.information(self, "Success", "Hotspot started successfully")
        self.status_bar.showMessage("Hotspot is running")

    def stop_ap(self):
        """Stop the access point."""
        if not self.ap_service or not self.bridge_service:
            return

        self.bridge_service.stop()
        self.ap_service.stop()
        self.status_bar.showMessage("Hotspot stopped")

    def refresh_clients(self):
        """Refresh the list of connected clients."""
        if not self.ap_service:
            return

        self.clients_table.setRowCount(0)
        clients = self.ap_service.get_connected_clients()
        
        self.clients_table.setRowCount(len(clients))
        for i, client in enumerate(clients):
            self.clients_table.setItem(
                i, 0, QTableWidgetItem(client["hostname"])
            )
            self.clients_table.setItem(
                i, 1, QTableWidgetItem(client["ip_address"])
            )
            self.clients_table.setItem(
                i, 2, QTableWidgetItem(client["mac_address"])
            )
            self.clients_table.setItem(
                i, 3, QTableWidgetItem(client.get("signal_strength", "N/A"))
            )

    def update_status(self):
        """Update all status displays."""
        if not all([self.connection_manager, self.ap_service, self.bridge_service]):
            return

        # Update connection status
        conn_status = self.connection_manager.get_connection_status()
        if conn_status["connected"]:
            self.conn_status_label.setText(
                f"Connected to: {conn_status['ssid']}\n"
                f"IP: {conn_status['ip_address']}"
            )
            if "signal_quality" in conn_status:
                quality = int(conn_status["signal_quality"].split("/")[0])
                self.conn_signal_bar.setValue(quality)
        else:
            self.conn_status_label.setText("Not connected")
            self.conn_signal_bar.setValue(0)

        # Update AP status
        if self.ap_service.is_running:
            clients = self.ap_service.get_connected_clients()
            self.ap_status_label.setText("Running")
            self.client_count_label.setText(f"Connected clients: {len(clients)}")
        else:
            self.ap_status_label.setText("Not running")
            self.client_count_label.setText("Connected clients: 0")

        # Update bridge status
        bridge_status = self.bridge_service.get_bridge_status()
        if bridge_status["running"]:
            self.bridge_status_label.setText("Running")
            self.forwarding_status_label.setText(
                "IP Forwarding: " + 
                ("Enabled" if bridge_status["forwarding_enabled"] else "Disabled")
            )
        else:
            self.bridge_status_label.setText("Not running")
            self.forwarding_status_label.setText("IP Forwarding: Disabled") 