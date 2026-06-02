"""
log_config.py — Centralized logging for the Agentic SonarQube Pipeline.

Uses a dedicated named logger ("pipeline") with propagate=False so that
no matter how many handlers Uvicorn, Streamlit, or third-party libraries
install on the root logger, our app messages are emitted exactly once.
"""

import sys
import logging

# Dedicated application logger — completely isolated from root
_app_logger = logging.getLogger("pipeline")
_app_logger.propagate = False          # ← key: never bubble up to root
_app_logger.setLevel(logging.INFO)

# Exactly one handler, attached at import time (module is a singleton)
if not _app_logger.handlers:
    _handler = logging.StreamHandler(sys.__stdout__)   # original stdout
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _app_logger.addHandler(_handler)


def get_logger() -> logging.Logger:
    """Return the single application-wide logger."""
    return _app_logger
