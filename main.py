#!/usr/bin/env python3.12
"""
Arbitrage Scanner - Professional Cryptocurrency Arbitrage Finder for macOS
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging before anything else
from app.config.logger import setup_logger
logger = setup_logger(__name__)

def main():
    """Main application entry point."""
    try:
        from app.ui.main_window import MainWindow
        from PySide6.QtWidgets import QApplication
        
        logger.info("🚀 Starting Arbitrage Scanner...")
        
        # Create Qt application
        app = QApplication(sys.argv)
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        logger.info("✅ Application started successfully")
        
        # Run application
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
