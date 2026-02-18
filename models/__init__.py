"""
Data models for RFQ Spec Analyzer.
Defines dataclasses for parsed documents, extracted specs, and references.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedPage:
    """Represents a single page/slide/sheet from a parsed document."""
    page_number: int  # 1-based page/slide/sheet index
    page_label: str  # e.g., "Page 3", "Slide 5", "Sheet: Optical"
    text: str  # Full text content of the page
    tables: list[list[list[str]]] = field(default_factory=list)  # List of tables (each table is list of rows)
    language: str = "en"  # Detected language code (en, de, fr, etc.)
    text_translated: str = ""  # English translation (empty if already English)
    original_text: str = ""  # Original text before translation


@dataclass
class ParsedDocument:
    """Represents a fully parsed document with all its pages."""
    file_path: str  # Full path to the source file
    file_name: str  # File name only
    file_type: str  # "pdf", "pptx", "xlsx"
    pages: list[ParsedPage] = field(default_factory=list)
    is_relevant: bool = True  # Whether this document is display-related
    relevance_reason: str = ""  # Reason for relevance decision


@dataclass
class SpecReference:
    """Tracks the source reference for an extracted spec value."""
    source_file: str  # Source file name
    page_label: str  # Page/Slide/Sheet location
    original_text: str  # Original text in source language
    translated_text: str  # English translation
    confidence: float = 0.0  # Extraction confidence (0.0 ~ 1.0)


@dataclass
class ExtractedSpec:
    """Represents a single extracted specification value."""
    spec_name: str  # Standardized English spec name
    value: str  # Extracted value (as string to preserve formatting like "±0.2")
    unit: str = ""  # Measurement unit
    condition: str = ""  # Test condition (if any)
    confidence: float = 0.0  # Extraction confidence (0.0 ~ 1.0)
    reference: Optional[SpecReference] = None  # Source reference


@dataclass
class TemplateField:
    """Represents a field in the Excel template."""
    row: int  # Row number in template (1-based)
    col_spec_name: int  # Column for spec name (A=1)
    col_oem_value: int  # Column for OEM requirement (B=2)
    col_lge_value: int  # Column for LGE requirement (C=3)
    spec_name: str  # Spec name from template
    oem_value: str = ""  # Current OEM value in template
    lge_value: str = ""  # Current LGE value in template


@dataclass
class MappingResult:
    """Result of mapping an extracted spec to a template field."""
    template_field: TemplateField  # Target template field
    extracted_spec: ExtractedSpec  # Source extracted spec
    match_confidence: float = 0.0  # How confident the mapping is
