#!/usr/bin/env python3
"""
Minimal test of main application
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QStyleFactory
from PyQt5.QtCore import Qt

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

def main():
    """Application entry point"""
    print("Creating QApplication...")
    app = QApplication(sys.argv)
    print("QApplication created successfully")
    
    app.setApplicationName("Acoustic Analysis Tool")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Acoustic Solutions")
    
    # Set application style
    app.setStyle(QStyleFactory.create('Fusion'))
    print("Application style set")
    
    # Try to import and create splash screen
    try:
        print("Importing SplashScreen...")
        from ui.splash_screen import SplashScreen
        print("SplashScreen imported successfully")
        
        print("Creating SplashScreen...")
        splash_screen = SplashScreen()
        print("SplashScreen created successfully")
        
        splash_screen.show()
        print("SplashScreen shown")
        
        return app.exec_()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main()) 