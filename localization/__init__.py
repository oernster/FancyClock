"""Localization package for FancyClock.

This package currently exposes only the `LocalizationManager` class,
which loads translations from the `translations` directory.
"""

from .i18n_manager import LocalizationManager

__all__ = ["LocalizationManager"]
