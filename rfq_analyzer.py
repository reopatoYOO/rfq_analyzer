"""
RFQ Spec Analyzer - Main Entry Point
=====================================
Analyzes automotive RFQ specification documents (PDF, PPT, Excel)
and extracts display/cover glass specs into an Excel template.

Usage:
    python rfq_analyzer.py
    python rfq_analyzer.py --input ./input_docs --template ./rfq_template.xlsx --output ./output
    python rfq_analyzer.py --config config.yaml
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

from analyzer.gemini_client import GeminiClient
from analyzer.doc_filter import DocumentFilter
from analyzer.spec_extractor import SpecExtractor
from exporter.template_mapper import TemplateMapper
from exporter.excel_writer import ExcelWriter
from models import ExtractedSpec, MappingResult
from parsers.unified_parser import UnifiedParser
from translator.translator import GeminiTranslator


def setup_logging(log_level: str = "INFO", log_file: str | None = None):
    """Configure logging for the application."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        logging.warning(f"Config file not found: {config_path}. Using defaults.")
        return {}

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="RFQ Spec Analyzer - Extract display specs from RFQ documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "--input", "-i",
        default=None,
        help="Input folder containing RFQ documents",
    )
    parser.add_argument(
        "--template", "-t",
        default=None,
        help="Path to Excel template file",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output folder for results",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Google Gemini API key (overrides config)",
    )
    return parser.parse_args()


def main():
    """Main execution flow."""
    args = parse_args()

    # Load configuration
    config = load_config(args.config)

    # Resolve paths (CLI args override config)
    gemini_config = config.get("gemini", {})
    paths_config = config.get("paths", {})
    logging_config = config.get("logging", {})
    translation_config = config.get("translation", {})

    api_key = args.api_key or gemini_config.get("api_key", "")
    input_folder = args.input or paths_config.get("input_folder", "./input_docs")
    template_file = args.template or paths_config.get("template_file", "./rfq_template.xlsx")
    output_folder = args.output or paths_config.get("output_folder", "./output")
    log_level = logging_config.get("level", "INFO")
    log_file = logging_config.get("log_file")

    # Setup logging
    setup_logging(log_level, log_file)
    logger = logging.getLogger(__name__)

    # Print banner
    logger.info("=" * 60)
    logger.info("  RFQ Spec Analyzer")
    logger.info("  Automotive Display Specification Extraction Tool")
    logger.info("=" * 60)

    # Validate API key
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        logger.error(
            "Gemini API key is not set. Please set it in config.yaml or "
            "use --api-key argument."
        )
        sys.exit(1)

    # Validate input folder
    if not Path(input_folder).exists():
        logger.error(f"Input folder not found: {input_folder}")
        logger.info("Please create the folder and add RFQ documents.")
        Path(input_folder).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created empty input folder: {input_folder}")
        sys.exit(1)

    # Validate template
    if not Path(template_file).exists():
        logger.error(f"Template file not found: {template_file}")
        sys.exit(1)

    # ===== PHASE 1: Parse Documents =====
    logger.info("")
    logger.info("=" * 40)
    logger.info("  PHASE 1: Parsing Documents")
    logger.info("=" * 40)

    parser = UnifiedParser(
        supported_extensions=config.get("supported_extensions")
    )
    documents = parser.parse_folder(input_folder)

    if not documents:
        logger.warning("No documents found in input folder. Exiting.")
        sys.exit(0)

    logger.info(f"Parsed {len(documents)} documents successfully")

    # ===== PHASE 2: Language Detection & Translation =====
    logger.info("")
    logger.info("=" * 40)
    logger.info("  PHASE 2: Language Detection & Translation")
    logger.info("=" * 40)

    translator = GeminiTranslator(
        api_key=api_key,
        model_name=gemini_config.get("model", "gemini-2.0-flash"),
        cache_enabled=translation_config.get("cache_enabled", True),
        cache_folder=translation_config.get("cache_folder", "./.cache/translations"),
    )

    for doc in documents:
        translator.translate_document(doc)

    # ===== PHASE 3: Document Filtering & Spec Extraction =====
    logger.info("")
    logger.info("=" * 40)
    logger.info("  PHASE 3: LLM Analysis (Gemini)")
    logger.info("=" * 40)

    gemini_client = GeminiClient(
        api_key=api_key,
        model_name=gemini_config.get("model", "gemini-2.0-flash"),
        max_retries=gemini_config.get("max_retries", 3),
        retry_delay=gemini_config.get("retry_delay_seconds", 2.0),
        temperature=gemini_config.get("temperature", 0.1),
    )

    # Filter documents
    doc_filter = DocumentFilter(
        client=gemini_client,
        filter_keywords=config.get("filter_keywords", []),
    )

    relevant_docs = []
    for doc in documents:
        is_relevant, reason = doc_filter.is_relevant(doc)
        doc.is_relevant = is_relevant
        doc.relevance_reason = reason
        if is_relevant:
            relevant_docs.append(doc)

    logger.info(
        f"Relevant documents: {len(relevant_docs)}/{len(documents)}"
    )

    if not relevant_docs:
        logger.warning("No relevant documents found. Exiting.")
        sys.exit(0)

    # Read template fields
    template_mapper = TemplateMapper(template_file)
    template_fields = template_mapper.read_template()

    logger.info(f"Template has {len(template_fields)} spec fields:")
    for f in template_fields:
        logger.debug(f"  - {f.spec_name}")

    # Extract specs from all relevant documents
    spec_extractor = SpecExtractor(client=gemini_client)
    all_extracted_specs: list[ExtractedSpec] = []

    for doc in relevant_docs:
        specs = spec_extractor.extract_from_document(doc, template_fields)
        all_extracted_specs.extend(specs)

    logger.info(f"Total extracted specs: {len(all_extracted_specs)}")

    # Map specs to template
    mappings = spec_extractor.map_specs_to_template(
        all_extracted_specs, template_fields
    )
    unmatched = spec_extractor.get_unmatched_specs(all_extracted_specs, mappings)

    logger.info(f"Mapped to template: {len(mappings)}")
    logger.info(f"Unmatched specs: {len(unmatched)}")

    # ===== PHASE 4: Excel Output =====
    logger.info("")
    logger.info("=" * 40)
    logger.info("  PHASE 4: Excel Output")
    logger.info("=" * 40)

    excel_writer = ExcelWriter(
        template_path=template_file,
        output_folder=output_folder,
    )

    output_path = excel_writer.write_results(
        mappings=mappings,
        unmatched_specs=unmatched,
    )

    # ===== Summary =====
    logger.info("")
    logger.info("=" * 60)
    logger.info("  ANALYSIS COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Documents processed:  {len(documents)}")
    logger.info(f"  Relevant documents:   {len(relevant_docs)}")
    logger.info(f"  Specs extracted:      {len(all_extracted_specs)}")
    logger.info(f"  Specs mapped:         {len(mappings)}")
    logger.info(f"  Unmatched specs:      {len(unmatched)}")
    logger.info(f"  Output file:          {output_path}")
    logger.info("=" * 60)

    # Print mapping details
    if mappings:
        logger.info("")
        logger.info("Mapped Specifications:")
        for m in mappings:
            conf = m.match_confidence
            icon = "✓" if conf >= 0.8 else "?" if conf >= 0.5 else "✗"
            logger.info(
                f"  {icon} {m.template_field.spec_name}: "
                f"{m.extracted_spec.value} "
                f"(confidence: {conf:.0%})"
            )

    if unmatched:
        logger.info("")
        logger.info("Unmatched Specifications (review manually):")
        for s in unmatched:
            logger.info(f"  - {s.spec_name}: {s.value} [{s.reference.source_file if s.reference else 'unknown'}]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
