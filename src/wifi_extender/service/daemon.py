"""System service daemon for the WiFi Extender."""
import os
import sys
import time
import json
import signal
import logging
import daemon
import lockfile
from typing import Dict, Optional
from ..core.wifi_detector import WiFiDetector
from ..core.connection_manager import ConnectionManager
from ..core.interface_manager import InterfaceManager
from ..core.ap_service import APService
from ..core.bridge_service import BridgeService


class WiFiExtenderDaemon:
    """Daemon service for managing WiFi Extender functionality."""

    def __init__(self):
        """Initialize the daemon service."""
        self.config_dir = "/etc/wifi-extender"
        self.run_dir = "/var/run/wifi-extender"
        self.log_dir = "/var/log/wifi-extender"
        self.pid_file = os.path.join(self.run_dir, "wifi-extender.pid")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.log_file = os.path.join(self.log_dir, "wifi-extender.log")

        # Ensure directories exist
        for directory in [self.config_dir, self.run_dir, self.log_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        # Setup logging
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("WiFiExtenderDaemon")

        # Initialize components
        self.wifi_detector = WiFiDetector()
        self.interface: Optional[str] = None
        self.connection_manager: Optional[ConnectionManager] = None
        self.interface_manager: Optional[InterfaceManager] = None
        self.ap_service: Optional[APService] = None
        self.bridge_service: Optional[BridgeService] = None

        # Service state
        self.running = False
        self.config: Dict = {}

    def load_config(self) -> None:
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                self.logger.info("Configuration loaded successfully")
            else:
                self.logger.warning("No configuration file found")
                self.config = {}
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            self.config = {}

    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            config_str = json.dumps(self.config, indent=4, sort_keys=True)
            with open(self.config_file, 'w') as f:
                f.write(config_str)
            self.logger.info("Configuration saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")

    def initialize_services(self) -> bool:
        """Initialize all required services.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Get suitable interfaces
            interfaces = self.wifi_detector.get_suitable_interfaces()
            if not interfaces:
                self.logger.error("No suitable WiFi interfaces found")
                return False

            # Use the first suitable interface
            self.interface = interfaces[0]
            self.logger.info(f"Using interface: {self.interface}")

            # Initialize services
            self.connection_manager = ConnectionManager(self.interface)
            self.interface_manager = InterfaceManager(self.interface)

            # Create virtual interface
            success, message = self.interface_manager.create_virtual_interface()
            if not success:
                self.logger.error(f"Failed to create virtual interface: {message}")
                return False

            virtual_interface = f"{self.interface}_ap0"
            self.ap_service = APService(virtual_interface)
            self.bridge_service = BridgeService(self.interface, virtual_interface)

            self.logger.info("Services initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing services: {e}")
            return False

    def start_services(self) -> bool:
        """Start WiFi extender services.
        
        Returns:
            bool: True if services started successfully, False otherwise
        """
        try:
            if not all([self.connection_manager, self.ap_service, self.bridge_service]):
                self.logger.error("Services not initialized")
                return False

            # Connect to upstream network
            if "upstream" in self.config:
                success, message = self.connection_manager.connect_to_network(
                    self.config["upstream"]["ssid"],
                    self.config["upstream"].get("password")
                )
                if not success:
                    self.logger.error(f"Failed to connect to upstream network: {message}")
                    return False

            # Configure and start AP
            if "ap" in self.config:
                success, message = self.ap_service.configure_ap(
                    ssid=self.config["ap"]["ssid"],
                    password=self.config["ap"].get("password"),
                    channel=self.config["ap"].get("channel", 6)
                )
                if not success:
                    self.logger.error(f"Failed to configure AP: {message}")
                    return False

                success, message = self.ap_service.configure_dhcp()
                if not success:
                    self.logger.error(f"Failed to configure DHCP: {message}")
                    return False

                success, message = self.ap_service.start()
                if not success:
                    self.logger.error(f"Failed to start AP: {message}")
                    return False

            # Start bridge
            success, message = self.bridge_service.start()
            if not success:
                self.logger.error(f"Failed to start bridge: {message}")
                self.ap_service.stop()
                return False

            self.logger.info("All services started successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error starting services: {e}")
            return False

    def stop_services(self) -> None:
        """Stop all services."""
        try:
            if self.bridge_service:
                self.bridge_service.stop()
            if self.ap_service:
                self.ap_service.stop()
            if self.connection_manager:
                self.connection_manager.disconnect()
            if self.interface_manager:
                self.interface_manager.delete_virtual_interface()
            
            self.logger.info("All services stopped successfully")

        except Exception as e:
            self.logger.error(f"Error stopping services: {e}")

    def run(self) -> None:
        """Main service loop."""
        self.running = True
        self.logger.info("WiFi Extender service starting")

        try:
            # Load configuration
            self.load_config()

            # Initialize services
            if not self.initialize_services():
                self.logger.error("Service initialization failed")
                return

            # Start services
            if not self.start_services():
                self.logger.error("Failed to start services")
                return

            # Main service loop
            while self.running:
                try:
                    # Check connection status
                    if self.connection_manager:
                        status = self.connection_manager.get_connection_status()
                        if not status.get("connected", False):
                            self.logger.warning("Upstream connection lost, reconnecting...")
                            self.start_services()

                    # Monitor AP status
                    if self.ap_service:
                        clients = self.ap_service.get_connected_clients()
                        self.logger.info(f"Connected clients: {len(clients)}")

                    time.sleep(30)  # Check every 30 seconds

                except Exception as e:
                    self.logger.error(f"Error in service loop: {e}")
                    time.sleep(5)  # Wait before retry

        except Exception as e:
            self.logger.error(f"Critical error in service: {e}")
        finally:
            self.stop_services()
            self.logger.info("WiFi Extender service stopped")

    def handle_signal(self, signum: int, frame) -> None:
        """Handle system signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        self.logger.info(f"Received signal {signum}")
        self.running = False

    def start(self) -> None:
        """Start the daemon service."""
        context = daemon.DaemonContext(
            working_directory='/var/run/wifi-extender',
            umask=0o002,
            pidfile=lockfile.FileLock(self.pid_file),
            signal_map={
                signal.SIGTERM: self.handle_signal,
                signal.SIGINT: self.handle_signal
            }
        )

        with context:
            self.run()


def main():
    """Main entry point for the system service."""
    service = WiFiExtenderDaemon()
    service.start() 