"""Interface manager module for creating and managing virtual interfaces."""
import subprocess
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class InterfaceManager:
    """Manages WiFi interfaces and their virtual counterparts."""

    def __init__(self, interface_name: str):
        """Initialize the interface manager.
        
        Args:
            interface_name: Name of the physical interface to manage
        """
        self.physical_interface = interface_name
        self.virtual_interface: Optional[str] = None

    def create_virtual_interface(self, name_suffix: str = "ap0") -> Tuple[bool, str]:
        """Create a virtual interface for AP mode.
        
        Args:
            name_suffix: Suffix for the virtual interface name
            
        Returns:
            Tuple of (success, message)
        """
        if self.virtual_interface:
            return False, f"Virtual interface {self.virtual_interface} already exists"

        try:
            # Create virtual interface
            virtual_name = f"{self.physical_interface}_{name_suffix}"
            cmd = ["iw", "dev", self.physical_interface, "interface", "add", 
                  virtual_name, "type", "__ap"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if result.returncode == 0:
                self.virtual_interface = virtual_name
                logger.info(f"Created virtual interface: {virtual_name}")
                return True, f"Successfully created virtual interface {virtual_name}"
            
            return False, f"Failed to create virtual interface: {result.stderr}"

        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating virtual interface: {e}")
            return False, str(e)

    def delete_virtual_interface(self) -> Tuple[bool, str]:
        """Delete the virtual interface.
        
        Returns:
            Tuple of (success, message)
        """
        if not self.virtual_interface:
            return False, "No virtual interface exists"

        try:
            cmd = ["iw", "dev", self.virtual_interface, "del"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if result.returncode == 0:
                logger.info(f"Deleted virtual interface: {self.virtual_interface}")
                self.virtual_interface = None
                return True, "Successfully deleted virtual interface"
            
            return False, f"Failed to delete virtual interface: {result.stderr}"

        except subprocess.CalledProcessError as e:
            logger.error(f"Error deleting virtual interface: {e}")
            return False, str(e)

    def set_interface_up(self, interface: str) -> Tuple[bool, str]:
        """Set an interface to UP state.
        
        Args:
            interface: Name of the interface to bring up
            
        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = ["ip", "link", "set", interface, "up"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if result.returncode == 0:
                logger.info(f"Set interface {interface} UP")
                return True, f"Successfully set {interface} UP"
            
            return False, f"Failed to set interface UP: {result.stderr}"

        except subprocess.CalledProcessError as e:
            logger.error(f"Error setting interface UP: {e}")
            return False, str(e)

    def set_interface_down(self, interface: str) -> Tuple[bool, str]:
        """Set an interface to DOWN state.
        
        Args:
            interface: Name of the interface to bring down
            
        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = ["ip", "link", "set", interface, "down"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if result.returncode == 0:
                logger.info(f"Set interface {interface} DOWN")
                return True, f"Successfully set {interface} DOWN"
            
            return False, f"Failed to set interface DOWN: {result.stderr}"

        except subprocess.CalledProcessError as e:
            logger.error(f"Error setting interface DOWN: {e}")
            return False, str(e)

    def set_interface_mode(self, interface: str, mode: str) -> Tuple[bool, str]:
        """Set the mode of an interface.
        
        Args:
            interface: Name of the interface
            mode: Mode to set (managed, ap, monitor)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # First set interface down
            down_success, down_msg = self.set_interface_down(interface)
            if not down_success:
                return False, f"Failed to set interface DOWN: {down_msg}"

            # Set the mode
            cmd = ["iwconfig", interface, "mode", mode]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if result.returncode != 0:
                return False, f"Failed to set mode: {result.stderr}"

            # Bring interface back up
            up_success, up_msg = self.set_interface_up(interface)
            if not up_success:
                return False, f"Failed to set interface UP: {up_msg}"

            logger.info(f"Set interface {interface} to mode {mode}")
            return True, f"Successfully set {interface} to mode {mode}"

        except subprocess.CalledProcessError as e:
            logger.error(f"Error setting interface mode: {e}")
            return False, str(e)