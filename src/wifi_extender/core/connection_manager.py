"""Connection manager for handling upstream WiFi connections."""
import subprocess
import time
from typing import Dict, Optional, Tuple, List
import logging
import netifaces
from .wifi_detector import WiFiDetector

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages upstream WiFi connections."""

    def __init__(self, interface: str):
        """Initialize the connection manager.
        
        Args:
            interface: Name of the interface to manage
        """
        self.interface = interface
        self.wifi_detector = WiFiDetector()
        self.current_connection: Optional[Dict] = None

    def scan_networks(self) -> List[Dict]:
        """Scan for available WiFi networks.
        
        Returns:
            List of dictionaries containing network information
        """
        try:
            cmd = ["iwlist", self.interface, "scan"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            networks = []
            current_network = {}
            
            for line in result.stdout.splitlines():
                line = line.strip()
                
                if "Cell" in line:
                    if current_network:
                        networks.append(current_network.copy())
                    current_network = {}
                elif "ESSID:" in line:
                    essid = line.split('"')[1]
                    current_network["ssid"] = essid
                elif "Quality=" in line:
                    quality = line.split("=")[1].split()[0]
                    current_network["quality"] = quality
                elif "Encryption key:" in line:
                    encrypted = "on" in line.lower()
                    current_network["encrypted"] = encrypted
                elif "IE: IEEE 802.11i/WPA2" in line:
                    current_network["security"] = "WPA2"
                elif "IE: WPA Version" in line:
                    current_network["security"] = "WPA"
            
            if current_network:
                networks.append(current_network)
            
            return networks

        except subprocess.CalledProcessError as e:
            logger.error(f"Error scanning networks: {e}")
            return []

    def connect_to_network(self, ssid: str, password: Optional[str] = None) -> Tuple[bool, str]:
        """Connect to a WiFi network.
        
        Args:
            ssid: Network SSID to connect to
            password: Network password (if required)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Generate wpa_supplicant configuration
            config_lines = [
                'ctrl_interface=/run/wpa_supplicant',
                'update_config=1',
                'network={',
                f'    ssid="{ssid}"'
            ]
            
            if password:
                config_lines.extend([
                    '    key_mgmt=WPA-PSK',
                    f'    psk="{password}"'
                ])
            else:
                config_lines.append('    key_mgmt=NONE')
            
            config_lines.append('}')
            config = '\n'.join(config_lines)
            
            # Write temporary configuration
            with open('/tmp/wpa_supplicant.conf', 'w') as f:
                f.write(config)
            
            # Stop any existing wpa_supplicant
            subprocess.run(["killall", "wpa_supplicant"], capture_output=True)
            time.sleep(1)
            
            # Start wpa_supplicant
            cmd = [
                "wpa_supplicant",
                "-B",  # Background
                "-i", self.interface,
                "-c", "/tmp/wpa_supplicant.conf"
            ]
            subprocess.run(cmd, check=True)
            
            # Wait for connection
            time.sleep(2)
            
            # Get DHCP address
            dhcp_cmd = ["dhclient", "-v", self.interface]
            subprocess.run(dhcp_cmd, check=True)
            
            # Verify connection
            status = self.get_connection_status()
            if status["connected"] and status["ssid"] == ssid:
                self.current_connection = status
                return True, f"Successfully connected to {ssid}"
            
            return False, f"Failed to connect to {ssid}"

        except subprocess.CalledProcessError as e:
            logger.error(f"Error connecting to network: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False, str(e)

    def disconnect(self) -> Tuple[bool, str]:
        """Disconnect from the current network.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Kill wpa_supplicant
            subprocess.run(["killall", "wpa_supplicant"], check=True)
            time.sleep(1)
            
            # Release DHCP
            subprocess.run(["dhclient", "-r", self.interface], check=True)
            
            self.current_connection = None
            return True, "Successfully disconnected"

        except subprocess.CalledProcessError as e:
            logger.error(f"Error disconnecting: {e}")
            return False, str(e)

    def get_connection_status(self) -> Dict:
        """Get the current connection status.
        
        Returns:
            Dictionary containing connection status information
        """
        status = self.wifi_detector.get_interface_status(self.interface)
        
        # Add signal strength if connected
        if status["connected"]:
            try:
                cmd = ["iwconfig", self.interface]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                if "Link Quality=" in result.stdout:
                    quality = result.stdout.split("Link Quality=")[1].split()[0]
                    status["signal_quality"] = quality
                
                if "Bit Rate=" in result.stdout:
                    rate = result.stdout.split("Bit Rate=")[1].split()[0]
                    status["bit_rate"] = rate
            
            except subprocess.CalledProcessError:
                pass
        
        return status

    def is_connected(self) -> bool:
        """Check if currently connected to a network.
        
        Returns:
            True if connected, False otherwise
        """
        status = self.get_connection_status()
        return status.get("connected", False) 