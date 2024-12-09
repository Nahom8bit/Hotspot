"""Main entry point for the WiFi Extender application."""
import sys
from PyQt6.QtWidgets import QApplication
from .main_window import MainWindow


def main():
    """Start the WiFi Extender application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 