"""WiFi interface detection and capability checking module."""
import subprocess
from typing import Dict, List, Optional
import netifaces
import psutil


class WiFiDetector:
    """Class for detecting and analyzing WiFi interfaces."""

    def __init__(self):
        """Initialize the WiFi detector."""
        self.interfaces: Dict[str, Dict] = {}
        self.refresh_interfaces()

    def refresh_interfaces(self) -> None:
        """Refresh the list of wireless interfaces."""
        self.interfaces.clear()
        for interface in netifaces.interfaces():
            if self._is_wireless(interface):
                self.interfaces[interface] = self._get_interface_info(interface)

    def _is_wireless(self, interface: str) -> bool:
        """Check if the given interface is a wireless interface."""
        try:
            # Check if the interface has wireless extensions
            cmd = ["iwconfig", interface]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return "no wireless extensions" not in result.stderr
        except subprocess.SubprocessError:
            return False

    def _get_interface_info(self, interface: str) -> Dict:
        """Get detailed information about a wireless interface."""
        info = {
            "name": interface,
            "supports_ap": False,
            "supports_managed": False,
            "current_mode": None,
            "mac_address": self._get_mac_address(interface),
            "driver": self._get_driver_info(interface),
            "capabilities": self._get_capabilities(interface)
        }
        return info

    def _get_mac_address(self, interface: str) -> Optional[str]:
        """Get the MAC address of the interface."""
        try:
            addrs = netifaces.ifaddresses(interface)
            mac = addrs[netifaces.AF_LINK][0]["addr"]
            return mac
        except (KeyError, IndexError):
            return None

    def _get_driver_info(self, interface: str) -> Optional[str]:
        """Get the driver information for the interface."""
        try:
            cmd = ["ethtool", "-i", interface]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.startswith("driver:"):
                        return line.split(":")[1].strip()
        except subprocess.SubprocessError:
            pass
        return None

    def _get_capabilities(self, interface: str) -> Dict:
        """Get the capabilities of the wireless interface."""
        capabilities = {
            "modes": [],
            "supported_bands": [],
            "current_band": None,
            "max_speed": None
        }

        try:
            # Get interface modes
            cmd = ["iw", interface, "info"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "Supported interface modes" in line:
                        # Parse supported modes from following lines
                        modes = []
                        for mode_line in result.stdout.splitlines():
                            if "*" in mode_line and ":" not in mode_line:
                                mode = mode_line.strip().replace("*", "").strip()
                                modes.append(mode)
                                if mode == "AP":
                                    self.interfaces[interface]["supports_ap"] = True
                                elif mode == "managed":
                                    self.interfaces[interface]["supports_managed"] = True
                        capabilities["modes"] = modes
        except subprocess.SubprocessError:
            pass

        return capabilities

    def get_suitable_interfaces(self) -> List[str]:
        """Get list of interfaces that support both AP and managed modes."""
        return [
            name for name, info in self.interfaces.items()
            if info["supports_ap"] and info["supports_managed"]
        ]

    def get_interface_status(self, interface: str) -> Dict:
        """Get the current status of a wireless interface."""
        if interface not in self.interfaces:
            return {}

        status = {
            "active": False,
            "connected": False,
            "ssid": None,
            "ip_address": None,
            "mode": None
        }

        try:
            # Check if interface is up
            addrs = netifaces.ifaddresses(interface)
            status["active"] = netifaces.AF_INET in addrs

            if status["active"]:
                status["ip_address"] = addrs[netifaces.AF_INET][0]["addr"]

                # Get current wireless info
                cmd = ["iwconfig", interface]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    output = result.stdout
                    if "ESSID:" in output:
                        ssid = output.split('ESSID:"')[1].split('"')[0]
                        status["ssid"] = ssid if ssid != "off/any" else None
                    if "Mode:" in output:
                        mode = output.split("Mode:")[1].split()[0]
                        status["mode"] = mode
                    status["connected"] = status["ssid"] is not None

        except (subprocess.SubprocessError, KeyError, IndexError):
            pass

        return status 