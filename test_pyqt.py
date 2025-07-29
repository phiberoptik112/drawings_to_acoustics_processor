#!/usr/bin/env python3
"""
Simple PyQt5 test script
"""

import sys
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

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
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main()) 