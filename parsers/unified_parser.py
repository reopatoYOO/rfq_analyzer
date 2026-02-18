"""
Unified Parser - Automatically selects the right parser based on file extension.
Scans a folder and parses all supported documents.
"""

import logging
from pathlib import Path

from models import ParsedDocument
from parsers.pdf_parser import PdfParser
from parsers.ppt_parser import PptParser
from parsers.excel_parser import ExcelParser

logger = logging.getLogger(__name__)

# Map extensions to parser classes
PARSER_MAP = {
    ".pdf": PdfParser,
    ".pptx": PptParser,
    ".ppt": PptParser,  # python-pptx may not support old .ppt; warn user
    ".xlsx": ExcelParser,
    ".xls": ExcelParser,  # openpyxl only supports .xlsx; warn user
}


class UnifiedParser:
    """Scans a folder for supported files and parses them all."""

    def __init__(self, supported_extensions: list[str] | None = None):
        self.supported_extensions = supported_extensions or list(PARSER_MAP.keys())

    def scan_folder(self, folder_path: str) -> list[str]:
        """
        Scan a folder for supported document files.

        Args:
            folder_path: Path to the folder to scan.

        Returns:
            List of file paths found.
        """
        folder = Path(folder_path)
        if not folder.exists():
            logger.error(f"Input folder not found: {folder_path}")
            return []

        files = []
        for ext in self.supported_extensions:
            files.extend(folder.glob(f"*{ext}"))
            files.extend(folder.glob(f"**/*{ext}"))  # Recursive search

        # Deduplicate and sort
        unique_files = sorted(set(str(f.resolve()) for f in files))
        logger.info(f"Found {len(unique_files)} supported files in {folder_path}")
        return unique_files

    def parse_file(self, file_path: str) -> ParsedDocument | None:
        """
        Parse a single file using the appropriate parser.

        Args:
            file_path: Path to the file.

        Returns:
            ParsedDocument or None if parsing fails.
        """
        ext = Path(file_path).suffix.lower()

        if ext not in PARSER_MAP:
            logger.warning(f"Unsupported file type: {ext} ({file_path})")
            return None

        # Warn about potentially unsupported formats
        if ext == ".ppt":
            logger.warning(
                f"Old .ppt format may not be fully supported. "
                f"Consider converting to .pptx: {file_path}"
            )
        if ext == ".xls":
            logger.warning(
                f"Old .xls format may not be fully supported. "
                f"Consider converting to .xlsx: {file_path}"
            )

        parser = PARSER_MAP[ext]()
        try:
            return parser.parse(file_path)
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return None

    def parse_folder(self, folder_path: str) -> list[ParsedDocument]:
        """
        Scan and parse all supported files in a folder.

        Args:
            folder_path: Path to the folder.

        Returns:
            List of ParsedDocument objects.
        """
        files = self.scan_folder(folder_path)
        documents = []

        for file_path in files:
            doc = self.parse_file(file_path)
            if doc is not None:
                documents.append(doc)

        logger.info(
            f"Successfully parsed {len(documents)}/{len(files)} files"
        )
        return documents
