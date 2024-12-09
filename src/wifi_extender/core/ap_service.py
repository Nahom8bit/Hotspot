"""Access Point service for managing hostapd and DHCP functionality."""
import subprocess
import os
import tempfile
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class APService:
    """Manages the WiFi Access Point functionality."""

    def __init__(self, interface: str):
        """Initialize the AP Service.
        
        Args:
            interface: Name of the interface to use for AP
        """
        self.interface = interface
        self.hostapd_conf_path = "/tmp/hostapd.conf"
        self.dnsmasq_conf_path = "/tmp/dnsmasq.conf"
        self.is_running = False

    def configure_ap(
        self,
        ssid: str,
        password: Optional[str] = None,
        channel: int = 6,
        hw_mode: str = "g"
    ) -> Tuple[bool, str]:
        """Configure the access point settings.
        
        Args:
            ssid: Name of the WiFi network to create
            password: Optional WPA2 password (None for open network)
            channel: WiFi channel (1-11 for 2.4GHz)
            hw_mode: Hardware mode (g for 2.4GHz)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            config_lines = [
                f"interface={self.interface}",
                f"driver=nl80211",
                f"ssid={ssid}",
                f"hw_mode={hw_mode}",
                f"channel={channel}",
                "ctrl_interface=/var/run/hostapd",
                "ctrl_interface_group=0",
                "ignore_broadcast_ssid=0"
            ]

            if password:
                # Add WPA2 configuration
                config_lines.extend([
                    "wpa=2",
                    "wpa_key_mgmt=WPA-PSK",
                    "rsn_pairwise=CCMP",
                    f"wpa_passphrase={password}"
                ])

            config = '\n'.join(config_lines)
            with open(self.hostapd_conf_path, 'w') as f:
                f.write(config)

            return True, "AP configuration created successfully"

        except Exception as e:
            logger.error(f"Error configuring AP: {e}")
            return False, str(e)

    def configure_dhcp(
        self,
        ip_range_start: str = "192.168.4.2",
        ip_range_end: str = "192.168.4.20",
        lease_time: str = "12h"
    ) -> Tuple[bool, str]:
        """Configure the DHCP server.
        
        Args:
            ip_range_start: Start of IP range
            ip_range_end: End of IP range
            lease_time: DHCP lease time
            
        Returns:
            Tuple of (success, message)
        """
        try:
            config_lines = [
                f"interface={self.interface}",
                "bind-interfaces",
                "server=8.8.8.8",  # Use Google DNS
                "domain-needed",
                "bogus-priv",
                "dhcp-range=" + 
                f"{ip_range_start},{ip_range_end},{lease_time}"
            ]

            config = '\n'.join(config_lines)
            with open(self.dnsmasq_conf_path, 'w') as f:
                f.write(config)

            return True, "DHCP configuration created successfully"

        except Exception as e:
            logger.error(f"Error configuring DHCP: {e}")
            return False, str(e)

    def start(self) -> Tuple[bool, str]:
        """Start the access point and DHCP server.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Configure interface
            subprocess.run(
                ["ip", "addr", "flush", "dev", self.interface],
                check=True
            )
            subprocess.run(
                ["ip", "addr", "add", "192.168.4.1/24", "dev", self.interface],
                check=True
            )
            subprocess.run(
                ["ip", "link", "set", self.interface, "up"],
                check=True
            )

            # Start hostapd
            subprocess.run(
                ["hostapd", "-B", self.hostapd_conf_path],
                check=True
            )

            # Start dnsmasq
            subprocess.run(
                ["dnsmasq", "-C", self.dnsmasq_conf_path],
                check=True
            )

            self.is_running = True
            return True, "Access point started successfully"

        except subprocess.CalledProcessError as e:
            logger.error(f"Error starting AP: {e}")
            self.stop()  # Cleanup on failure
            return False, str(e)

    def stop(self) -> Tuple[bool, str]:
        """Stop the access point and DHCP server.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Stop services
            subprocess.run(["killall", "hostapd"], capture_output=True)
            subprocess.run(["killall", "dnsmasq"], capture_output=True)

            # Clean up interface
            subprocess.run(
                ["ip", "addr", "flush", "dev", self.interface],
                check=True
            )

            # Remove temporary files
            if os.path.exists(self.hostapd_conf_path):
                os.remove(self.hostapd_conf_path)
            if os.path.exists(self.dnsmasq_conf_path):
                os.remove(self.dnsmasq_conf_path)

            self.is_running = False
            return True, "Access point stopped successfully"

        except Exception as e:
            logger.error(f"Error stopping AP: {e}")
            return False, str(e)

    def get_connected_clients(self) -> List[Dict]:
        """Get list of connected clients.
        
        Returns:
            List of dictionaries containing client information
        """
        clients = []
        try:
            # Read DHCP leases
            if os.path.exists("/var/lib/misc/dnsmasq.leases"):
                with open("/var/lib/misc/dnsmasq.leases", 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            clients.append({
                                "mac_address": parts[1],
                                "ip_address": parts[2],
                                "hostname": parts[3]
                            })

            # Add signal strength information
            result = subprocess.run(
                ["iw", "dev", self.interface, "station", "dump"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                current_mac = None
                for line in result.stdout.splitlines():
                    if "Station" in line:
                        current_mac = line.split()[1]
                    elif "signal:" in line and current_mac:
                        signal = line.split(":")[1].strip()
                        for client in clients:
                            if client["mac_address"] == current_mac:
                                client["signal_strength"] = signal
                                break

        except Exception as e:
            logger.error(f"Error getting client list: {e}")

        return clients 