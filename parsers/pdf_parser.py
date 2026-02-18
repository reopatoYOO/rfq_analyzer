"""
PDF Parser - Extracts text and tables from PDF files using pdfplumber.
"""

import logging
from pathlib import Path

import pdfplumber

from models import ParsedDocument, ParsedPage

logger = logging.getLogger(__name__)


class PdfParser:
    """Parses PDF files and extracts text and tables per page."""

    def parse(self, file_path: str) -> ParsedDocument:
        """
        Parse a PDF file and return a ParsedDocument.

        Args:
            file_path: Path to the PDF file.

        Returns:
            ParsedDocument with pages containing text and tables.
        """
        path = Path(file_path)
        doc = ParsedDocument(
            file_path=str(path.resolve()),
            file_name=path.name,
            file_type="pdf",
        )

        try:
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    # Extract text
                    text = page.extract_text() or ""

                    # Extract tables
                    tables = []
                    raw_tables = page.extract_tables() or []
                    for table in raw_tables:
                        cleaned_table = [
                            [str(cell) if cell is not None else "" for cell in row]
                            for row in table
                        ]
                        tables.append(cleaned_table)

                    # Build table text representation for context
                    table_text_parts = []
                    for table in tables:
                        for row in table:
                            table_text_parts.append(" | ".join(row))

                    # Combine text and table text
                    full_text = text
                    if table_text_parts:
                        full_text += "\n\n[TABLE DATA]\n" + "\n".join(table_text_parts)

                    parsed_page = ParsedPage(
                        page_number=i,
                        page_label=f"Page {i}",
                        text=full_text,
                        tables=tables,
                    )
                    doc.pages.append(parsed_page)

                logger.info(f"Parsed PDF: {path.name} ({len(doc.pages)} pages)")

        except Exception as e:
            logger.error(f"Failed to parse PDF {path.name}: {e}")
            raise

        return doc
