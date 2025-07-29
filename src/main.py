#!/usr/bin/env python3
"""
Acoustic Analysis Tool - Main Application Entry Point
Desktop application for LEED acoustic certification analysis
"""

import sys
import os
from PySide6.QtWidgets import QApplication, QStyleFactory
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.splash_screen import SplashScreen


class AcousticAnalysisApp(QApplication):
    """Main application class"""
    
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("Acoustic Analysis Tool")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("Acoustic Solutions")
        
        # Set application style
        self.setStyle(QStyleFactory.create('Fusion'))
        
        # Initialize main window
        self.splash_screen = None
        
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