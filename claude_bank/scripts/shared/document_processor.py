"""
Document processor for parsing DOCX files.
Extracts text content from Word documents.
"""

import logging
from pathlib import Path
from typing import List, Optional
from docx import Document as DocxDocument
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph

from text_splitter import Page

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Processes DOCX files and extracts text content."""

    def __init__(self):
        """Initialize document processor."""
        pass

    def parse_docx(self, file_path: str) -> List[Page]:
        """
        Parse a DOCX file and extract pages.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            List of Page objects with extracted text
        """
        logger.info(f"Parsing DOCX file: {file_path}")
        
        try:
            doc = DocxDocument(file_path)
        except Exception as e:
            logger.error(f"Error opening DOCX file {file_path}: {e}")
            raise

        pages = []
        current_page_text = []
        page_num = 0
        
        # Extract all content (paragraphs and tables)
        for element in self._iter_block_items(doc):
            if isinstance(element, Paragraph):
                text = element.text.strip()
                if text:
                    current_page_text.append(text)
                    
                    # Simple heuristic: treat each section/chapter as a page
                    # You can adjust this based on your needs
                    if self._is_section_break(element):
                        if current_page_text:
                            page_text = "\n".join(current_page_text)
                            pages.append(Page(
                                page_num=page_num,
                                text=page_text,
                                offset=0
                            ))
                            current_page_text = []
                            page_num += 1
            
            elif isinstance(element, Table):
                table_text = self._extract_table_text(element)
                if table_text:
                    current_page_text.append(table_text)

        # Add remaining content as last page
        if current_page_text:
            page_text = "\n".join(current_page_text)
            pages.append(Page(
                page_num=page_num,
                text=page_text,
                offset=0
            ))

        logger.info(f"Extracted {len(pages)} pages from {file_path}")
        return pages

    def parse_docx_as_single_document(self, file_path: str) -> str:
        """
        Parse a DOCX file and return all text as a single string.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            Extracted text content
        """
        logger.info(f"Parsing DOCX file (single doc): {file_path}")
        
        try:
            doc = DocxDocument(file_path)
        except Exception as e:
            logger.error(f"Error opening DOCX file {file_path}: {e}")
            raise

        all_text = []
        
        for element in self._iter_block_items(doc):
            if isinstance(element, Paragraph):
                text = element.text.strip()
                if text:
                    all_text.append(text)
            elif isinstance(element, Table):
                table_text = self._extract_table_text(element)
                if table_text:
                    all_text.append(table_text)

        result = "\n\n".join(all_text)
        logger.info(f"Extracted {len(result)} characters from {file_path}")
        return result

    def _iter_block_items(self, parent):
        """
        Yield each paragraph and table in document order.
        Preserves the order of content as it appears in the document.
        """
        from docx.document import Document as DocumentType
        
        if isinstance(parent, DocumentType):
            parent_elm = parent.element.body
        else:
            parent_elm = parent._element

        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)

    def _is_section_break(self, paragraph: Paragraph) -> bool:
        """
        Determine if paragraph represents a section break.
        Heuristics:
        - Heading styles (Heading 1, Heading 2)
        - Short text with title case
        - All caps short text
        """
        if not paragraph.text:
            return False

        # Check if it's a heading style
        style_name = paragraph.style.name.lower() if paragraph.style else ""
        if 'heading' in style_name:
            return True

        text = paragraph.text.strip()
        
        # Short title-case or all-caps might be a heading
        if len(text) < 100:
            if text.isupper() or text.istitle():
                return True

        return False

    def _extract_table_text(self, table: Table) -> str:
        """
        Extract text from a table.
        Formats as tab-separated values.
        """
        rows_text = []
        for row in table.rows:
            cells_text = [cell.text.strip() for cell in row.cells]
            rows_text.append("\t".join(cells_text))
        return "\n".join(rows_text)

    def detect_chapters(self, text: str) -> List[tuple[int, str, int]]:
        """
        Detect chapter boundaries in text.
        
        Returns:
            List of tuples: (chapter_number, chapter_title, start_position)
        """
        import re
        
        chapters = []
        
        # Pattern to match chapter headings
        # Examples: "Chapter 1:", "CHAPTER 1:", "Chapter One", etc.
        patterns = [
            r'(?:^|\n)\s*(Chapter\s+(\d+)[:\-\s]+([^\n]+))',
            r'(?:^|\n)\s*(CHAPTER\s+(\d+)[:\-\s]+([^\n]+))',
            r'(?:^|\n)\s*(\d+\.\s+([^\n]{10,80}))',  # "1. Title of Chapter"
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    if len(match.groups()) >= 3:
                        full_match = match.group(1)
                        chapter_num = int(match.group(2))
                        chapter_title = match.group(3).strip()
                    else:
                        continue
                    
                    chapters.append((
                        chapter_num,
                        chapter_title,
                        match.start()
                    ))
                except (ValueError, IndexError):
                    continue

        # Sort by position in text
        chapters.sort(key=lambda x: x[2])
        
        logger.info(f"Detected {len(chapters)} chapters")
        return chapters
