"""
Language Detector - Detects the language of text using langdetect.
"""

import logging

from langdetect import detect, DetectorFactory

# Make langdetect deterministic
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

# Language name mapping for display
LANG_NAMES = {
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
}


class LanguageDetector:
    """Detects the language of text content."""

    def detect(self, text: str) -> str:
        """
        Detect the language of the given text.

        Args:
            text: Text to detect language for.

        Returns:
            Language code (e.g., "en", "de", "fr").
            Returns "en" if detection fails or text is too short.
        """
        # Need minimum text length for reliable detection
        clean_text = text.strip()
        if len(clean_text) < 20:
            return "en"

        try:
            lang = detect(clean_text)
            logger.debug(f"Detected language: {lang} ({LANG_NAMES.get(lang, 'Unknown')})")
            return lang
        except Exception as e:
            logger.warning(f"Language detection failed: {e}. Defaulting to 'en'.")
            return "en"

    def needs_translation(self, lang_code: str, target_lang: str = "en") -> bool:
        """
        Check if the detected language needs translation.

        Args:
            lang_code: Detected language code.
            target_lang: Target language code.

        Returns:
            True if translation is needed.
        """
        return lang_code != target_lang

    def get_language_name(self, lang_code: str) -> str:
        """Get human-readable language name."""
        return LANG_NAMES.get(lang_code, f"Unknown ({lang_code})")
