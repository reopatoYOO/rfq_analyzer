"""
Gemini Translator - Translates technical documents to English using Gemini API.
Preserves original text for reference tracking.
"""

import hashlib
import json
import logging
from pathlib import Path

from google import genai

from models import ParsedDocument, ParsedPage
from translator.language_detector import LanguageDetector

logger = logging.getLogger(__name__)


class GeminiTranslator:
    """Translates document text to English using Google Gemini API."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash",
        cache_enabled: bool = True,
        cache_folder: str = "./.cache/translations",
    ):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.detector = LanguageDetector()
        self.cache_enabled = cache_enabled
        self.cache_folder = Path(cache_folder)

        if cache_enabled:
            self.cache_folder.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, text: str) -> str:
        """Generate a cache key from text content."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _load_from_cache(self, cache_key: str) -> str | None:
        """Load cached translation if available."""
        if not self.cache_enabled:
            return None
        cache_file = self.cache_folder / f"{cache_key}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                return data.get("translated_text")
            except Exception:
                return None
        return None

    def _save_to_cache(self, cache_key: str, original: str, translated: str):
        """Save translation to cache."""
        if not self.cache_enabled:
            return
        cache_file = self.cache_folder / f"{cache_key}.json"
        try:
            data = {
                "original_text": original[:200],  # Save first 200 chars for reference
                "translated_text": translated,
            }
            cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save translation cache: {e}")

    def translate_text(self, text: str, source_lang: str) -> str:
        """
        Translate text to English using Gemini API.

        Args:
            text: Text to translate.
            source_lang: Source language code (e.g., "de", "fr").

        Returns:
            Translated English text.
        """
        if not text.strip():
            return text

        # Check cache first
        cache_key = self._get_cache_key(text)
        cached = self._load_from_cache(cache_key)
        if cached:
            logger.debug("Using cached translation")
            return cached

        lang_name = self.detector.get_language_name(source_lang)

        prompt = f"""You are a technical document translator specializing in automotive display specifications.

Translate the following {lang_name} text to English.

IMPORTANT RULES:
- Preserve all numeric values, units, and technical terms exactly
- Maintain the original formatting and structure
- Keep measurement units unchanged (mm, cd/m², %, °C, MPa, etc.)
- Translate technical terms accurately in the automotive display context
- If a term is already in English, keep it as is
- Do NOT add explanations or notes, just translate

TEXT TO TRANSLATE:
{text}

ENGLISH TRANSLATION:"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name, contents=prompt
            )
            translated = response.text.strip()

            # Save to cache
            self._save_to_cache(cache_key, text, translated)

            return translated
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text  # Return original text on failure

    def translate_page(self, page: ParsedPage) -> ParsedPage:
        """
        Detect language and translate a page if needed.

        The original text is preserved in page.original_text.

        Args:
            page: ParsedPage to translate.

        Returns:
            Updated ParsedPage with translation applied.
        """
        # Detect language
        lang = self.detector.detect(page.text)
        page.language = lang

        if self.detector.needs_translation(lang):
            lang_name = self.detector.get_language_name(lang)
            logger.info(f"Translating {page.page_label} from {lang_name} to English")

            page.original_text = page.text
            page.text_translated = self.translate_text(page.text, lang)
            # Keep original in original_text, use translated as primary text
            page.text = page.text_translated
        else:
            page.original_text = page.text
            page.text_translated = page.text

        return page

    def translate_document(self, doc: ParsedDocument) -> ParsedDocument:
        """
        Translate all pages in a document that need translation.

        Args:
            doc: ParsedDocument to translate.

        Returns:
            Updated ParsedDocument with translated pages.
        """
        logger.info(f"Processing translations for: {doc.file_name}")

        for page in doc.pages:
            self.translate_page(page)

        return doc
