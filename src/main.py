#!/usr/bin/env python3
"""
Acoustic Analysis Tool - Main Application Entry Point
Desktop application for LEED acoustic certification analysis
"""

import sys
import os
from PySide6.QtWidgets import QApplication, QStyleFactory
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QScreen

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.splash_screen import SplashScreen


def get_dpi_scale_factor(app: QApplication) -> float:
    """Get the DPI scale factor for the primary screen.

    Returns:
        float: Scale factor relative to 96 DPI (standard Windows DPI)
    """
    screen = app.primaryScreen()
    if screen:
        # Use logical DPI to get scale factor
        logical_dpi = screen.logicalDotsPerInch()
        return logical_dpi / 96.0  # 96 is standard DPI
    return 1.0


class AcousticAnalysisApp(QApplication):
    """Main application class"""

    # Standard DPI scale factor (set after app initialization)
    dpi_scale: float = 1.0

    def __init__(self, argv):
        # Enable high DPI scaling before creating QApplication
        # This allows Qt to handle DPI scaling automatically
        try:
            # Qt 6 / PySide6 approach
            self.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
        except AttributeError:
            pass  # Not available in older Qt versions

        super().__init__(argv)
        self.setApplicationName("Acoustic Analysis Tool")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("Acoustic Solutions")

        # Calculate and store DPI scale factor
        AcousticAnalysisApp.dpi_scale = get_dpi_scale_factor(self)

        # Set application style
        self.setStyle(QStyleFactory.create('Fusion'))

        # Initialize main window
        self.splash_screen = None

    @classmethod
    def scale(cls, value: int) -> int:
        """Scale a pixel value based on DPI.

        Use this for sizing widgets that need DPI awareness.

        Args:
            value: Pixel value at 96 DPI

        Returns:
            Scaled pixel value for current DPI
        """
        return int(value * cls.dpi_scale)

    def start(self):
        """Start the application"""
        # Create and show splash screen
        self.splash_screen = SplashScreen()
        self.splash_screen.show()

        return self.exec()


def main():
    """Application entry point"""
    app = AcousticAnalysisApp(sys.argv)
    return app.start()


if __name__ == '__main__':
    sys.exit(main())