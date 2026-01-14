"""Pytest configuration for AI tests."""

import sys
from pathlib import Path

# Add apps/ folder to path for config imports
AI_ROOT = Path(__file__).resolve().parents[1]
APPS_ROOT = AI_ROOT.parent  # apps/ folder containing both ai/ and config/

if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))
if str(APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(APPS_ROOT))

# Pre-load settings with AI app's .env so all tests use consistent config
from config.settings import get_settings
get_settings("ai")
