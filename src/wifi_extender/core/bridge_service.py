"""Bridge service for handling network routing between interfaces."""
import subprocess
import time
from typing import Dict, List, Optional, Tuple
import logging
import os

logger = logging.getLogger(__name__)


class BridgeService:
    """Manages network bridging and routing between interfaces."""

    def __init__(self, upstream_interface: str, ap_interface: str):
        """Initialize the bridge service.
        
        Args:
            upstream_interface: Interface connected to internet
            ap_interface: Interface running as access point
        """
        self.upstream_interface = upstream_interface
        self.ap_interface = ap_interface
        self.bridge_name = "br0"
        self.is_running = False
        self._iptables_rules = []

    def setup_bridge(self) -> Tuple[bool, str]:
        """Create and configure network bridge.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Create bridge interface
            subprocess.run(
                ["ip", "link", "add", "name", self.bridge_name, "type", "bridge"],
                check=True
            )
            
            # Add interfaces to bridge
            subprocess.run(
                ["ip", "link", "set", self.ap_interface, "master", self.bridge_name],
                check=True
            )
            
            # Set bridge interface up
            subprocess.run(
                ["ip", "link", "set", self.bridge_name, "up"],
                check=True
            )
            
            return True, "Bridge interface created successfully"

        except subprocess.CalledProcessError as e:
            logger.error(f"Error setting up bridge: {e}")
            return False, str(e)

    def setup_routing(self) -> Tuple[bool, str]:
        """Configure IP forwarding and routing rules.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Enable IP forwarding
            with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
                f.write("1")

            # Configure iptables rules
            rules = [
                # Enable NAT
                ["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", 
                 self.upstream_interface, "-j", "MASQUERADE"],
                
                # Allow forwarding between interfaces
                ["iptables", "-A", "FORWARD", "-i", self.ap_interface, "-o",
                 self.upstream_interface, "-j", "ACCEPT"],
                ["iptables", "-A", "FORWARD", "-i", self.upstream_interface, "-o",
                 self.ap_interface, "-m", "state", "--state",
                 "RELATED,ESTABLISHED", "-j", "ACCEPT"]
            ]

            for rule in rules:
                subprocess.run(rule, check=True)
                self._iptables_rules.append(rule)

            return True, "Routing rules configured successfully"

        except subprocess.CalledProcessError as e:
            logger.error(f"Error setting up routing: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Error configuring IP forwarding: {e}")
            return False, str(e)

    def start(self) -> Tuple[bool, str]:
        """Start the network bridge and routing.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Setup bridge
            bridge_success, bridge_message = self.setup_bridge()
            if not bridge_success:
                return False, f"Bridge setup failed: {bridge_message}"

            # Setup routing
            routing_success, routing_message = self.setup_routing()
            if not routing_success:
                self.cleanup_bridge()
                return False, f"Routing setup failed: {routing_message}"

            self.is_running = True
            return True, "Bridge and routing started successfully"

        except Exception as e:
            logger.error(f"Error starting bridge service: {e}")
            self.stop()
            return False, str(e)

    def stop(self) -> Tuple[bool, str]:
        """Stop the network bridge and routing.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Remove iptables rules
            for rule in reversed(self._iptables_rules):
                delete_rule = rule.copy()
                delete_rule[3] = "-D"  # Change -A to -D
                subprocess.run(delete_rule, capture_output=True)
            self._iptables_rules.clear()

            # Disable IP forwarding
            with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
                f.write("0")

            # Remove bridge interface
            self.cleanup_bridge()

            self.is_running = False
            return True, "Bridge and routing stopped successfully"

        except Exception as e:
            logger.error(f"Error stopping bridge service: {e}")
            return False, str(e)

    def cleanup_bridge(self) -> None:
        """Remove bridge interface and cleanup."""
        try:
            # Remove interface from bridge
            subprocess.run(
                ["ip", "link", "set", self.ap_interface, "nomaster"],
                capture_output=True
            )
            
            # Delete bridge interface
            subprocess.run(
                ["ip", "link", "delete", self.bridge_name, "type", "bridge"],
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Error cleaning up bridge: {e}")

    def get_bridge_status(self) -> Dict:
        """Get current bridge status.
        
        Returns:
            Dictionary containing bridge status information
        """
        status = {
            "running": self.is_running,
            "bridge_interface": self.bridge_name,
            "upstream_interface": self.upstream_interface,
            "ap_interface": self.ap_interface,
            "forwarding_enabled": False,
            "nat_enabled": False
        }

        try:
            # Check IP forwarding
            with open("/proc/sys/net/ipv4/ip_forward", "r") as f:
                status["forwarding_enabled"] = f.read().strip() == "1"

            # Check NAT rules
            result = subprocess.run(
                ["iptables", "-t", "nat", "-L", "POSTROUTING", "-n"],
                capture_output=True,
                text=True
            )
            status["nat_enabled"] = self.upstream_interface in result.stdout

            # Get bridge info
            result = subprocess.run(
                ["bridge", "link", "show", self.bridge_name],
                capture_output=True,
                text=True
            )
            status["bridge_active"] = result.returncode == 0

        except Exception as e:
            logger.error(f"Error getting bridge status: {e}")

        return status 