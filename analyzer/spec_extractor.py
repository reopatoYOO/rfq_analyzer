"""
Spec Extractor - Uses Gemini to extract display specifications from parsed documents.
Maps extracted specs to template fields and normalizes terminology.
"""

import json
import logging

from analyzer.gemini_client import GeminiClient
from models import (
    ExtractedSpec,
    MappingResult,
    ParsedDocument,
    SpecReference,
    TemplateField,
)

logger = logging.getLogger(__name__)


class SpecExtractor:
    """Extracts display specifications from documents using Gemini LLM."""

    def __init__(self, client: GeminiClient):
        self.client = client

    def extract_specs_from_page(
        self,
        page_text: str,
        original_text: str,
        page_label: str,
        file_name: str,
        template_fields: list[TemplateField],
    ) -> list[ExtractedSpec]:
        """
        Extract specs from a single page's text using Gemini.

        Args:
            page_text: Page text (translated to English if needed).
            original_text: Original text before translation.
            page_label: Page/slide/sheet label for reference.
            file_name: Source file name.
            template_fields: Template fields to match against.

        Returns:
            List of ExtractedSpec objects found on this page.
        """
        if not page_text.strip():
            return []

        # Build the list of spec names from template
        spec_names = [f.spec_name for f in template_fields]
        spec_names_str = "\n".join(f"  - {name}" for name in spec_names)

        prompt = f"""You are an automotive display and cover glass specification analyst.
You must extract specification values from the following document text.

TARGET SPECIFICATIONS (extract values for these items):
{spec_names_str}

IMPORTANT RULES:
1. Extract ONLY specs that match or closely relate to the target specifications above.
2. Different manufacturers may use different terminology for the same specification.
   Map them correctly. Examples:
   - "Leuchtdichte" (DE) = "Luminosité" (FR) = "Luminance" = "Brightness"
   - "Kontrastverhältnis" = "Rapport de contraste" = "Contrast Ratio"
   - "Oberflächenhärte" = "Dureté de surface" = "Surface hardness"
   - "Glasdicke" = "Épaisseur du verre" = "Glass thickness" = "Thickness & tolerance"
   - "Druckspannung" = "Contrainte de compression" = "Compressive Stress"
   - "Transmission" = "Transmittance" = "Cover Glass Transmittance"
   - "Blendschutz" = "Anti-éblouissement" = "Anti-Glare"
   - "Entspiegelung" = "Antireflet" = "Anti-Reflection"
   - "Kontaktwinkel" = "Angle de contact" = "Water Contact Angle"
3. Preserve exact numeric values and units from the source text.
4. Include the EXACT source text where each spec was found.
5. Assign a confidence score (0.0 to 1.0) based on match certainty.

DOCUMENT TEXT:
{page_text[:12000]}

Respond with ONLY a JSON array (no markdown, no code blocks). Each element:
{{
  "spec_name": "exact name from TARGET SPECIFICATIONS list",
  "value": "extracted value with units",
  "unit": "measurement unit",
  "condition": "test condition if any",
  "confidence": 0.95,
  "source_text": "exact original text snippet where this was found"
}}

If no matching specs are found, return an empty array: []"""

        try:
            response = self.client.generate(prompt)

            # Clean response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1]
                response = response.rsplit("```", 1)[0]
            response = response.strip()

            specs_data = json.loads(response)

            if not isinstance(specs_data, list):
                logger.warning(f"Unexpected response format from Gemini for {page_label}")
                return []

            extracted_specs = []
            for item in specs_data:
                ref = SpecReference(
                    source_file=file_name,
                    page_label=page_label,
                    original_text=item.get("source_text", ""),
                    translated_text=item.get("source_text", ""),
                    confidence=item.get("confidence", 0.0),
                )

                # If we have original (non-English) text, store it
                if original_text and original_text != page_text:
                    ref.original_text = self._find_original_snippet(
                        original_text, item.get("source_text", "")
                    )

                spec = ExtractedSpec(
                    spec_name=item.get("spec_name", ""),
                    value=item.get("value", ""),
                    unit=item.get("unit", ""),
                    condition=item.get("condition", ""),
                    confidence=item.get("confidence", 0.0),
                    reference=ref,
                )
                extracted_specs.append(spec)

            logger.info(
                f"Extracted {len(extracted_specs)} specs from {file_name} - {page_label}"
            )
            return extracted_specs

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Spec extraction failed for {page_label}: {e}")
            return []

    def _find_original_snippet(self, original_text: str, translated_snippet: str) -> str:
        """
        Try to find the approximate original text that corresponds
        to the translated snippet. Uses simple heuristic matching.
        """
        # If the translated snippet appears in original, use it directly
        if translated_snippet in original_text:
            return translated_snippet

        # Otherwise return a note that the original needs manual lookup
        return f"[See original document for source text]"

    def extract_from_document(
        self,
        doc: ParsedDocument,
        template_fields: list[TemplateField],
    ) -> list[ExtractedSpec]:
        """
        Extract all specs from a document.

        Args:
            doc: ParsedDocument to extract from.
            template_fields: Template fields to match against.

        Returns:
            List of all ExtractedSpec objects from the document.
        """
        all_specs = []

        for page in doc.pages:
            specs = self.extract_specs_from_page(
                page_text=page.text,
                original_text=page.original_text,
                page_label=page.page_label,
                file_name=doc.file_name,
                template_fields=template_fields,
            )
            all_specs.extend(specs)

        logger.info(f"Total specs extracted from {doc.file_name}: {len(all_specs)}")
        return all_specs

    def map_specs_to_template(
        self,
        extracted_specs: list[ExtractedSpec],
        template_fields: list[TemplateField],
    ) -> list[MappingResult]:
        """
        Map extracted specs to template fields using LLM for fuzzy matching.

        Args:
            extracted_specs: List of extracted specs.
            template_fields: List of template fields.

        Returns:
            List of MappingResult objects.
        """
        if not extracted_specs:
            return []

        # Build mapping using exact and fuzzy name matching
        mappings = []
        used_fields = set()

        for spec in extracted_specs:
            best_match = None
            best_confidence = 0.0

            for field in template_fields:
                if field.row in used_fields:
                    continue

                # Exact match
                if spec.spec_name.lower().strip() == field.spec_name.lower().strip():
                    best_match = field
                    best_confidence = 1.0
                    break

                # Partial match
                if (
                    spec.spec_name.lower() in field.spec_name.lower()
                    or field.spec_name.lower() in spec.spec_name.lower()
                ):
                    if spec.confidence > best_confidence:
                        best_match = field
                        best_confidence = spec.confidence * 0.9

            if best_match and best_confidence > 0.3:
                mapping = MappingResult(
                    template_field=best_match,
                    extracted_spec=spec,
                    match_confidence=best_confidence,
                )
                mappings.append(mapping)
                # Don't mark as used - multiple sources may provide same spec
                # We'll pick the best one later

        # Deduplicate: keep highest confidence mapping per template field
        best_mappings: dict[int, MappingResult] = {}
        for m in mappings:
            row = m.template_field.row
            if row not in best_mappings or m.match_confidence > best_mappings[row].match_confidence:
                best_mappings[row] = m

        result = list(best_mappings.values())
        logger.info(
            f"Mapped {len(result)} specs to template fields "
            f"(out of {len(extracted_specs)} extracted)"
        )
        return result

    def get_unmatched_specs(
        self,
        extracted_specs: list[ExtractedSpec],
        mappings: list[MappingResult],
    ) -> list[ExtractedSpec]:
        """
        Find specs that were extracted but not mapped to any template field.

        Args:
            extracted_specs: All extracted specs.
            mappings: Successful mappings.

        Returns:
            List of unmatched ExtractedSpec objects.
        """
        mapped_spec_names = {m.extracted_spec.spec_name.lower() for m in mappings}
        return [
            s for s in extracted_specs
            if s.spec_name.lower() not in mapped_spec_names
        ]
