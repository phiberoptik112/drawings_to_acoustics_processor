#!/usr/bin/env python3
"""
Simple Qt test script using PySide6 to match the application
"""

import os
import sys

# Use offscreen platform for headless test environments
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

def main():
    app = QApplication(sys.argv)
    
    # Create a simple window
    window = QWidget()
    window.setWindowTitle("PyQt5 Test")
    window.setGeometry(100, 100, 300, 200)
    
    # Create layout and label
    layout = QVBoxLayout()
    label = QLabel("PyQt5 is working!")
    label.setAlignment(Qt.AlignCenter)
    layout.addWidget(label)
    
    window.setLayout(layout)
    window.show()
    
    print("PyQt5 test window should appear...")
    return app.exec()

if __name__ == '__main__':
    sys.exit(main()) 