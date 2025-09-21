# ABOUTME: Cross-cutting utilities and shared infrastructure
# ABOUTME: Supporting services: logging, configuration, common helpers

"""
Utils Layer: Shared infrastructure and cross-cutting concerns

This layer provides:
- Logging configuration and progress tracking
- Configuration management
- Common utility functions
- Shared types and helpers used across layers

Data Flow: Supporting services for all other layers
"""

from . import logging

__all__ = [
    "logging",
]
