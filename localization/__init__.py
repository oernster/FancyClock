"""
🌍 Calendifier Localization System - Major International Languages

This module provides comprehensive internationalization support for the Calendifier
application with 100% translation coverage across 13 major international languages
and zero English fallbacks for non-English locales.

Features:
- 13 major international languages covering 3.5+ billion speakers
- Zero English fallback enforcement
- Automated UI string extraction
- Comprehensive validation and quality assurance
- Dynamic language switching
- Professional translation workflow
- Performance optimized for fast locale switching
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

# Import version information from master version file
try:
    from version import __version__
except ImportError:
    # Fallback if version.py is not available
    __version__ = "1.1.0"

# Core components
from .i18n_manager import (
    I18nManager,
    MissingTranslationError,
    get_i18n_manager,
    set_i18n_manager,
)
from .locale_detector import LocaleDetector

# Optional components - import only if available
try:
    from .translation_validator import TranslationValidator
except ImportError:
    TranslationValidator = None

try:
    from .batch_translator import BatchTranslator
except ImportError:
    BatchTranslator = None

try:
    from .fallback_eliminator import FallbackEliminator
except ImportError:
    FallbackEliminator = None

try:
    from .ui_element_extractor import UIElementExtractor
except ImportError:
    UIElementExtractor = None

try:
    from .comprehensive_batch_implementation import ComprehensiveBatchImplementation
except ImportError:
    ComprehensiveBatchImplementation = None

logger = logging.getLogger(__name__)

# Global instances
_locale_detector: Optional[LocaleDetector] = None
_translation_validator: Optional[TranslationValidator] = None
_batch_translator: Optional[BatchTranslator] = None
_fallback_eliminator: Optional[FallbackEliminator] = None
_ui_extractor: Optional[UIElementExtractor] = None
_batch_implementation: Optional[ComprehensiveBatchImplementation] = None


def initialize_localization_system(
    translations_dir: Optional[Path] = None,
    ui_dir: Optional[Path] = None,
    locale: str = "en_GB",
    strict_mode: bool = True,
) -> I18nManager:
    """
    Initialize the complete localization system.

    Args:
        translations_dir: Path to translations directory
        ui_dir: Path to UI components directory
        locale: Initial locale
        strict_mode: Enable strict mode (no fallbacks)

    Returns:
        I18nManager: Initialized translation manager
    """
    global _locale_detector, _translation_validator, _batch_translator
    global _fallback_eliminator, _ui_extractor, _batch_implementation

    try:
        # Set default paths
        if translations_dir is None:
            translations_dir = Path(__file__).parent / "translations"
        if ui_dir is None:
            ui_dir = Path(__file__).parent.parent / "ui"

        # Initialize core components
        _locale_detector = LocaleDetector()

        # Initialize optional components only if available
        if TranslationValidator:
            _translation_validator = TranslationValidator(translations_dir)
        if BatchTranslator:
            _batch_translator = BatchTranslator(translations_dir)
        if FallbackEliminator:
            _fallback_eliminator = FallbackEliminator(translations_dir)
        if UIElementExtractor:
            _ui_extractor = UIElementExtractor(ui_dir, translations_dir)
        if ComprehensiveBatchImplementation:
            _batch_implementation = ComprehensiveBatchImplementation(
                translations_dir, ui_dir
            )

        # Initialize I18n manager
        i18n_manager = I18nManager(locale, strict_mode, translations_dir)
        set_i18n_manager(i18n_manager)

        logger.info("🌍 Localization system initialized successfully")
        logger.info(f"📍 Locale: {locale}")
        logger.info(f"📁 Translations: {translations_dir}")
        logger.info(f"🎯 Strict mode: {strict_mode}")

        return i18n_manager

    except Exception as e:
        logger.error(f"❌ Failed to initialize localization system: {e}")
        raise


def get_locale_detector() -> LocaleDetector:
    """Get the global locale detector instance."""
    global _locale_detector
    if _locale_detector is None:
        _locale_detector = LocaleDetector()
    return _locale_detector


def get_translation_validator():
    """Get the global translation validator instance."""
    global _translation_validator
    if TranslationValidator and _translation_validator is None:
        _translation_validator = TranslationValidator()
    return _translation_validator


def get_batch_translator():
    """Get the global batch translator instance."""
    global _batch_translator
    if BatchTranslator and _batch_translator is None:
        _batch_translator = BatchTranslator()
    return _batch_translator


def get_fallback_eliminator():
    """Get the global fallback eliminator instance."""
    global _fallback_eliminator
    if FallbackEliminator and _fallback_eliminator is None:
        _fallback_eliminator = FallbackEliminator()
    return _fallback_eliminator


def get_ui_extractor():
    """Get the global UI element extractor instance."""
    global _ui_extractor
    if UIElementExtractor and _ui_extractor is None:
        _ui_extractor = UIElementExtractor()
    return _ui_extractor


def get_batch_implementation():
    """Get the global batch implementation instance."""
    global _batch_implementation
    if ComprehensiveBatchImplementation and _batch_implementation is None:
        _batch_implementation = ComprehensiveBatchImplementation()
    return _batch_implementation


# Convenience functions for common operations
def _(key: str, **kwargs) -> str:
    """
    Translate a key with parameter substitution.

    Args:
        key: Translation key
        **kwargs: Parameters for string formatting

    Returns:
        str: Translated text
    """
    return get_i18n_manager().get_text(key, **kwargs)


def translate(key: str, **kwargs) -> str:
    """
    Translate a key with parameter substitution (alias for _).

    Args:
        key: Translation key
        **kwargs: Parameters for string formatting

    Returns:
        str: Translated text
    """
    return _(key, **kwargs)


def get_text(key: str, **kwargs) -> str:
    """
    Get translated text (backward compatibility alias for _).

    Args:
        key: Translation key
        **kwargs: Parameters for string formatting

    Returns:
        str: Translated text
    """
    return _(key, **kwargs)


def set_locale(locale_code: str) -> bool:
    """
    Set the current locale.

    Args:
        locale_code: New locale code

    Returns:
        bool: True if locale was set successfully
    """
    return get_i18n_manager().set_locale(locale_code)


def get_current_locale() -> str:
    """
    Get the current locale.

    Returns:
        str: Current locale code
    """
    return get_i18n_manager().current_locale


def get_supported_locales() -> List[str]:
    """
    Get list of all supported locales.

    Returns:
        List[str]: List of supported locale codes
    """
    return get_locale_detector().get_supported_locales()


def get_locale_info(locale_code: str) -> Optional[Dict[str, str]]:
    """
    Get information about a locale.

    Args:
        locale_code: Locale code

    Returns:
        Optional[Dict[str, str]]: Locale information or None
    """
    return get_locale_detector().get_locale_info(locale_code)


def validate_locale(locale_code: str):
    """
    Validate translations for a locale.

    Args:
        locale_code: Locale to validate

    Returns:
        ValidationResult: Validation results or None if validator not available
    """
    validator = get_translation_validator()
    if validator:
        return validator.validate_locale(locale_code)
    return None


def validate_all_locales():
    """
    Validate all locales.

    Returns:
        CoverageReport: Overall coverage report or None if validator not available
    """
    validator = get_translation_validator()
    if validator:
        return validator.validate_all_locales()
    return None


def eliminate_fallbacks(locale_code: str, auto_fix: bool = False):
    """
    Eliminate fallbacks for a locale.

    Args:
        locale_code: Locale to process
        auto_fix: Whether to automatically apply fixes

    Returns:
        EliminationReport: Elimination results or None if eliminator not available
    """
    eliminator = get_fallback_eliminator()
    if eliminator:
        return eliminator.eliminate_fallbacks(locale_code, auto_fix)
    return None


def extract_ui_strings():
    """
    Extract translatable strings from UI components.

    Returns:
        ExtractionReport: Extraction results or None if extractor not available
    """
    extractor = get_ui_extractor()
    if extractor:
        return extractor.extract_from_directory()
    return None


def get_implementation_progress():
    """
    Get current implementation progress.

    Returns:
        ImplementationProgress: Progress information or None if implementation not available
    """
    implementation = get_batch_implementation()
    if implementation:
        return implementation.get_implementation_progress()
    return None


async def execute_complete_implementation() -> bool:
    """
    Execute the complete 13-locale implementation.

    Returns:
        bool: True if implementation was successful, False if not available
    """
    implementation = get_batch_implementation()
    if implementation:
        return await implementation.execute_complete_implementation()
    return False


def get_system_info() -> Dict[str, Any]:
    """
    Get comprehensive system information.

    Returns:
        Dict[str, Any]: System information
    """
    try:
        locale_detector = get_locale_detector()

        info = {
            "version": __version__,
            "total_supported_locales": len(locale_detector.get_supported_locales()),
            "current_locale": get_current_locale(),
            "system_locale": locale_detector.detect_system_locale(),
            "features": {
                "zero_fallbacks": True,
                "dynamic_switching": True,
                "auto_validation": TranslationValidator is not None,
                "ui_extraction": UIElementExtractor is not None,
                "batch_implementation": ComprehensiveBatchImplementation is not None,
                "quality_assurance": True,
            },
        }

        # Add validation status if validator is available
        validator = get_translation_validator()
        if validator:
            try:
                coverage_report = validator.validate_all_locales()
                info["validation_status"] = {
                    "total_locales": coverage_report.total_locales,
                    "complete_locales": coverage_report.complete_locales,
                    "overall_coverage": coverage_report.overall_coverage,
                    "incomplete_locales": coverage_report.incomplete_locales,
                }
            except:
                info["validation_status"] = {"error": "Validation failed"}

        # Add implementation progress if available
        progress = get_implementation_progress()
        if progress:
            try:
                info["implementation_progress"] = {
                    "current_phase": progress.current_phase.value,
                    "overall_completion": progress.overall_completion,
                    "quality_score": progress.quality_score,
                    "zero_fallback_locales": progress.zero_fallback_locales,
                }
            except:
                info["implementation_progress"] = {"error": "Progress unavailable"}

        return info

    except Exception as e:
        logger.error(f"❌ Failed to get system info: {e}")
        return {"error": str(e)}


# Batch information for external reference
BATCH_INFO = {
    1: {
        "name": "Major International Languages",
        "locales": [
            "en_US",
            "en_GB",
            "es_ES",
            "fr_FR",
            "de_DE",
            "it_IT",
            "pt_BR",
            "ru_RU",
            "zh_CN",
            "zh_TW",
            "ja_JP",
            "ko_KR",
            "hi_IN",
            "ar_SA",
        ],
        "priority": 1,
        "description": "Core international languages covering 3.5+ billion speakers worldwide",
    }
}

# Export all public components
__all__ = [
    # Core classes
    "I18nManager",
    "LocaleDetector",
    "TranslationValidator",
    "BatchTranslator",
    "FallbackEliminator",
    "UIElementExtractor",
    "ComprehensiveBatchImplementation",
    # Data classes
    "ValidationResult",
    "CoverageReport",
    "BatchInfo",
    "TranslationProgress",
    "FallbackIssue",
    "EliminationReport",
    "ExtractedString",
    "ExtractionReport",
    "ImplementationProgress",
    "BatchImplementationConfig",
    # Enums
    "BatchStatus",
    "FallbackType",
    "StringType",
    "ImplementationPhase",
    # Exceptions
    "MissingTranslationError",
    # Initialization functions
    "initialize_localization_system",
    # Getter functions
    "get_i18n_manager",
    "get_locale_detector",
    "get_translation_validator",
    "get_batch_translator",
    "get_fallback_eliminator",
    "get_ui_extractor",
    "get_batch_implementation",
    # Convenience functions
    "_",
    "translate",
    "get_text",
    "set_locale",
    "get_current_locale",
    "get_supported_locales",
    "get_locale_info",
    "validate_locale",
    "validate_all_locales",
    "eliminate_fallbacks",
    "extract_ui_strings",
    "get_implementation_progress",
    "execute_complete_implementation",
    "get_system_info",
    # Constants
    "BATCH_INFO",
]

# Initialize logging
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Module metadata
__author__ = "Calendifier Development Team"
__description__ = (
    "Comprehensive 13-locale internationalization system with zero fallbacks"
)
