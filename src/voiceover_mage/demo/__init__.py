# ABOUTME: Demo package - organized Gradio web interface for voice generation demo

"""
Demo package containing the Gradio web interface organized following React-like patterns.

Structure:
- app.py: Main application entry point
- components/: UI component definitions (like React components)
- services/: Data fetching and business logic (like React hooks/services)
- utils/: Utility functions for data transformation and processing
- constants/: Static content and configuration
"""

from voiceover_mage.demo.app import main

__all__ = ["main"]
