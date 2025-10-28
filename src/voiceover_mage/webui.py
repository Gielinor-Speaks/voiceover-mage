# ABOUTME: Gradio web interface - compatibility wrapper for organized demo package
# ABOUTME: For the actual implementation, see src/voiceover_mage/demo/

"""
Compatibility wrapper for the Gradio web interface.

The web interface has been reorganized into a clean, modular structure
under src/voiceover_mage/demo/ following React-like patterns.

This file maintains backward compatibility while delegating to the new structure.
"""

from __future__ import annotations

# Import and re-export the main entry point
from voiceover_mage.demo.app import main

# For backward compatibility, allow direct execution
if __name__ == "__main__":
    main()
