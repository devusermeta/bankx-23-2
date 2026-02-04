"""
Text splitter for semantic chunking of documents.
Based on Azure Search OpenAI Demo's SentenceTextSplitter pattern.
"""

import re
import tiktoken
from dataclasses import dataclass, field
from typing import Generator, List, Optional

# Encoding model for token counting
ENCODING_MODEL = "text-embedding-3-large"
bpe = tiktoken.encoding_for_model("gpt-4")  # Use GPT-4 encoding as proxy

# Sentence endings
STANDARD_SENTENCE_ENDINGS = [".", "!", "?"]
CJK_SENTENCE_ENDINGS = ["。", "！", "？", "‼", "⁇", "⁈", "⁉"]

# Word breaks
STANDARD_WORD_BREAKS = [" ", "\n", "\t", ",", ";", ":", "-", "(", ")", "[", "]", "{", "}", "/", "\\"]

# Default chunking parameters
DEFAULT_MAX_TOKENS = 500
DEFAULT_SECTION_LENGTH = 1000  # characters
DEFAULT_OVERLAP_PERCENT = 10


@dataclass
class Page:
    """Represents a page from a document."""
    page_num: int
    text: str
    offset: int = 0


@dataclass
class Chunk:
    """Represents a semantic chunk from text splitting."""
    page_num: int
    text: str
    token_count: Optional[int] = None


@dataclass
class _ChunkBuilder:
    """Helper to accumulate text spans until size limits are reached."""
    page_num: int
    max_chars: int
    max_tokens: int
    parts: List[str] = field(default_factory=list)
    token_len: int = 0

    def can_fit(self, text: str, token_count: int) -> bool:
        """Check if text can fit in current chunk."""
        if not self.parts:  # Always allow first span
            return token_count <= self.max_tokens and len(text) <= self.max_chars
        
        return (
            len("".join(self.parts)) + len(text) <= self.max_chars
            and self.token_len + token_count <= self.max_tokens
        )

    def add(self, text: str, token_count: int) -> bool:
        """Add text to chunk if it fits."""
        if not self.can_fit(text, token_count):
            return False
        self.parts.append(text)
        self.token_len += token_count
        return True

    def has_content(self) -> bool:
        """Check if builder has any content."""
        return bool(self.parts)

    def flush_into(self, out: List[Chunk]):
        """Flush accumulated content into output list."""
        if self.parts:
            chunk_text = "".join(self.parts)
            if chunk_text.strip():
                out.append(Chunk(
                    page_num=self.page_num,
                    text=chunk_text,
                    token_count=self.token_len
                ))
        self.parts.clear()
        self.token_len = 0


class SentenceTextSplitter:
    """
    Splits text into semantic chunks respecting sentence boundaries.
    
    Features:
    - Token-aware splitting (default 500 tokens max per chunk)
    - Sentence boundary preservation
    - Semantic overlap between chunks (10% by default)
    - Handles cross-page continuations
    """

    def __init__(
        self,
        max_tokens_per_section: int = DEFAULT_MAX_TOKENS,
        max_section_length: int = DEFAULT_SECTION_LENGTH,
        semantic_overlap_percent: int = DEFAULT_OVERLAP_PERCENT
    ):
        self.max_tokens_per_section = max_tokens_per_section
        self.max_section_length = max_section_length
        self.semantic_overlap_percent = semantic_overlap_percent
        
        self.sentence_endings = STANDARD_SENTENCE_ENDINGS + CJK_SENTENCE_ENDINGS
        self.word_breaks = STANDARD_WORD_BREAKS

    def split_pages(self, pages: List[Page]) -> Generator[Chunk, None, None]:
        """
        Split pages into semantic chunks.
        
        Args:
            pages: List of Page objects to split
            
        Yields:
            Chunk objects with semantic boundaries preserved
        """
        for page in pages:
            yield from self._split_page(page)

    def _split_page(self, page: Page) -> Generator[Chunk, None, None]:
        """Split a single page into chunks."""
        text = page.text or ""
        if not text.strip():
            return

        # Split into sentence-like spans
        spans = self._split_into_sentences(text)
        
        page_chunks: List[Chunk] = []
        builder = _ChunkBuilder(
            page_num=page.page_num,
            max_chars=self.max_section_length,
            max_tokens=self.max_tokens_per_section
        )

        for span in spans:
            span_tokens = len(bpe.encode(span))
            
            # If single span exceeds limit, split it recursively
            if span_tokens > self.max_tokens_per_section:
                builder.flush_into(page_chunks)
                for chunk in self._split_oversized_span(page.page_num, span):
                    page_chunks.append(chunk)
                continue

            # Try to add span to current chunk
            if not builder.add(span, span_tokens):
                # Flush current chunk and start new one
                builder.flush_into(page_chunks)
                if not builder.add(span, span_tokens):
                    # Should not happen as we checked span_tokens <= max
                    page_chunks.append(Chunk(
                        page_num=page.page_num,
                        text=span,
                        token_count=span_tokens
                    ))

        # Flush any remaining content
        builder.flush_into(page_chunks)

        # Apply semantic overlap
        if self.semantic_overlap_percent > 0 and len(page_chunks) > 1:
            page_chunks = self._apply_semantic_overlap(page_chunks)

        yield from page_chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentence-like spans."""
        spans: List[str] = []
        current_chars: List[str] = []
        
        for ch in text:
            current_chars.append(ch)
            if ch in self.sentence_endings:
                spans.append("".join(current_chars))
                current_chars = []
        
        # Add any remaining text
        if current_chars:
            spans.append("".join(current_chars))
        
        return [s for s in spans if s.strip()]

    def _split_oversized_span(self, page_num: int, text: str) -> Generator[Chunk, None, None]:
        """Recursively split oversized text at sentence or word boundaries."""
        tokens = bpe.encode(text)
        if len(tokens) <= self.max_tokens_per_section:
            yield Chunk(page_num=page_num, text=text, token_count=len(tokens))
            return

        # Try to find sentence ending near midpoint
        mid = len(text) // 2
        split_pos = self._find_sentence_boundary(text, mid)
        
        if split_pos > 0:
            # Split at sentence boundary
            first_half = text[:split_pos + 1]
            second_half = text[split_pos + 1:]
        else:
            # Split at word boundary or midpoint with overlap
            split_pos = self._find_word_boundary(text, mid)
            if split_pos > 0:
                first_half = text[:split_pos]
                second_half = text[split_pos:]
            else:
                # Last resort: midpoint split with overlap
                overlap = int(len(text) * (DEFAULT_OVERLAP_PERCENT / 100))
                first_half = text[:mid + overlap]
                second_half = text[mid - overlap:]

        # Recursively split each half
        yield from self._split_oversized_span(page_num, first_half)
        yield from self._split_oversized_span(page_num, second_half)

    def _find_sentence_boundary(self, text: str, target_pos: int) -> int:
        """Find nearest sentence ending to target position."""
        window = len(text) // 3
        for offset in range(min(window, len(text))):
            # Check positions around target
            for pos in [target_pos + offset, target_pos - offset]:
                if 0 <= pos < len(text) and text[pos] in self.sentence_endings:
                    return pos
        return -1

    def _find_word_boundary(self, text: str, target_pos: int) -> int:
        """Find nearest word break to target position."""
        window = len(text) // 4
        for offset in range(min(window, len(text))):
            for pos in [target_pos + offset, target_pos - offset]:
                if 0 <= pos < len(text) and text[pos] in self.word_breaks:
                    return pos
        return -1

    def _apply_semantic_overlap(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Apply semantic overlap by appending preview of next chunk to previous chunk.
        Next chunk stays unchanged to preserve clean sentence boundaries.
        """
        if len(chunks) < 2:
            return chunks

        result = []
        for i in range(len(chunks)):
            current = chunks[i]
            
            # For all chunks except the last, append overlap from next chunk
            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                overlap_size = int(self.max_section_length * self.semantic_overlap_percent / 100)
                
                # Get prefix from next chunk
                prefix = next_chunk.text[:overlap_size]
                
                # Extend to sentence boundary if possible
                for j in range(overlap_size, min(len(next_chunk.text), overlap_size * 2)):
                    if next_chunk.text[j] in self.sentence_endings:
                        prefix = next_chunk.text[:j + 1]
                        break
                    elif next_chunk.text[j] in self.word_breaks:
                        prefix = next_chunk.text[:j]
                
                # Append overlap to current chunk
                combined_text = current.text + prefix
                combined_tokens = len(bpe.encode(combined_text))
                
                # Only append if it doesn't exceed hard limits
                if (combined_tokens <= self.max_tokens_per_section * 1.2 and
                    len(combined_text) <= self.max_section_length * 1.2):
                    result.append(Chunk(
                        page_num=current.page_num,
                        text=combined_text,
                        token_count=combined_tokens
                    ))
                else:
                    result.append(current)
            else:
                result.append(current)

        return result


class SimpleTextSplitter:
    """Simple text splitter for basic chunking without semantic awareness."""
    
    def __init__(self, max_tokens: int = DEFAULT_MAX_TOKENS):
        self.max_tokens = max_tokens

    def split_text(self, text: str, page_num: int = 0) -> List[Chunk]:
        """Split text into fixed-size token chunks."""
        tokens = bpe.encode(text)
        chunks = []
        
        for i in range(0, len(tokens), self.max_tokens):
            chunk_tokens = tokens[i:i + self.max_tokens]
            chunk_text = bpe.decode(chunk_tokens)
            chunks.append(Chunk(
                page_num=page_num,
                text=chunk_text,
                token_count=len(chunk_tokens)
            ))
        
        return chunks
