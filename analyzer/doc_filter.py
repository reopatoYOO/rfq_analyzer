"""
Document Filter - Uses Gemini to determine if a document is relevant
to automotive display specifications.
"""

import logging

from analyzer.gemini_client import GeminiClient
from models import ParsedDocument

logger = logging.getLogger(__name__)


class DocumentFilter:
    """Filters documents for display-related relevance using LLM."""

    def __init__(self, client: GeminiClient, filter_keywords: list[str] | None = None):
        self.client = client
        self.filter_keywords = filter_keywords or []

    def _keyword_prefilter(self, doc: ParsedDocument) -> bool:
        """Quick keyword-based pre-filter before calling LLM."""
        if not self.filter_keywords:
            return True  # No keywords = accept all

        all_text = " ".join(page.text.lower() for page in doc.pages)

        for keyword in self.filter_keywords:
            if keyword.lower() in all_text:
                return True
        return False

    def is_relevant(self, doc: ParsedDocument) -> tuple[bool, str]:
        """
        Determine if a document is relevant to automotive display specifications.

        Uses keyword pre-filtering first, then LLM for borderline cases.

        Args:
            doc: ParsedDocument to evaluate.

        Returns:
            Tuple of (is_relevant, reason).
        """
        # Quick keyword check
        if not self._keyword_prefilter(doc):
            reason = "No display-related keywords found in document"
            logger.info(f"Filtered out (keywords): {doc.file_name} - {reason}")
            return False, reason

        # For documents with keywords, use LLM for deeper analysis
        # Take first few pages for efficiency
        sample_text = ""
        for page in doc.pages[:5]:  # Analyze first 5 pages max
            sample_text += f"\n--- {page.page_label} ---\n{page.text[:2000]}\n"

        if len(sample_text.strip()) < 50:
            return False, "Document has insufficient text content"

        prompt = f"""You are an automotive display specification analyst.

Analyze the following document content and determine if it contains specifications
related to automotive display or cover glass products.

Look for any of these topics:
- Display specifications (size, resolution, luminance, contrast, etc.)
- Cover glass specifications (thickness, hardness, transmittance, etc.)
- Optical properties (reflectance, haze, color, anti-glare, anti-reflection, etc.)
- Mechanical properties (dimensions, stress, surface profile, etc.)
- Environmental conditions (temperature, humidity, vibration, etc.)
- Touch panel specifications
- Electrical specifications (voltage, power, interface, etc.)

DOCUMENT CONTENT:
{sample_text[:8000]}

Respond with EXACTLY this JSON format (no markdown, no code blocks):
{{"is_relevant": true/false, "reason": "brief explanation", "confidence": 0.0-1.0}}"""

        try:
            response = self.client.generate(prompt)
            # Clean response - remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1]
                response = response.rsplit("```", 1)[0]
            response = response.strip()

            import json
            result = json.loads(response)
            is_relevant = result.get("is_relevant", True)
            reason = result.get("reason", "")

            logger.info(
                f"Document relevance: {doc.file_name} -> "
                f"{'RELEVANT' if is_relevant else 'NOT RELEVANT'} ({reason})"
            )
            return is_relevant, reason

        except Exception as e:
            logger.warning(
                f"LLM filtering failed for {doc.file_name}: {e}. "
                f"Defaulting to relevant (keyword match exists)."
            )
            return True, "Keyword match found (LLM filtering failed)"
