#!/usr/bin/env python3
"""
Populate Silencer Product Database

This script populates the silencer product database with initial manufacturer data.
Run this script to add silencer products to the database for the first time.

Usage:
    python populate_silencer_database.py
"""

import sys
import os

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.database import initialize_database
from data.silencer_database import populate_silencer_database


def main():
    """Main function to populate the silencer database"""
    print("Silencer Product Database Population Tool")
    print("=" * 50)
    
    try:
        # Initialize the database first
        print("Initializing database...")
        db_path = initialize_database()
        print(f"Database initialized at: {db_path}")
        
        # Populate the silencer products
        print("Populating silencer product database...")
        populate_silencer_database()
        print("Silencer product database populated successfully!")
        
        print("\nDatabase population completed.")
        print("You can now use the silencer optimization features in the application.")
        
    except Exception as e:
        print(f"Error populating database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()