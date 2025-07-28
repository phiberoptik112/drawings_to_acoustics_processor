#!/usr/bin/env python3
"""
Development installation script for Acoustic Analysis Tool
"""

import subprocess
import sys
import os

def install_requirements():
    """Install required packages"""
    print("Installing required packages...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False

def test_installation():
    """Test that PyQt5 is properly installed"""
    print("Testing PyQt5 installation...")
    
    try:
        import PyQt5.QtWidgets
        print("✅ PyQt5 imported successfully")
        return True
    except ImportError as e:
        print(f"❌ PyQt5 import failed: {e}")
        return False

def main():
    """Main installation process"""
    print("🚀 Setting up Acoustic Analysis Tool Development Environment\n")
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        return False
    
    print(f"✅ Python {sys.version}")
    
    # Install requirements
    if not install_requirements():
        return False
    
    # Test installation
    if not test_installation():
        print("\n⚠️  Installation may have issues. Try:")
        print("   pip install --upgrade PyQt5")
        print("   or use conda: conda install pyqt")
        return False
    
    print("\n🎉 Development environment ready!")
    print("\n📝 To run the application:")
    print("   cd src")
    print("   python main.py")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)