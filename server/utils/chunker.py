"""
Text chunking utilities for processing long documents
"""

import re
import logging
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata"""

    text: str
    start_index: int
    end_index: int
    chunk_id: str
    metadata: Dict[str, Any]


class TextChunker:
    """Advanced text chunker with overlap and context preservation"""

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 200,
        preserve_sentences: bool = True,
        preserve_paragraphs: bool = True,
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.preserve_sentences = preserve_sentences
        self.preserve_paragraphs = preserve_paragraphs

        # Sentence boundary patterns
        self.sentence_endings = re.compile(r"[.!?]+\s+")
        self.paragraph_breaks = re.compile(r"\n\s*\n")

    def chunk_text(
        self, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[TextChunk]:
        """
        Split text into overlapping chunks with context preservation
        """
        if not text.strip():
            return []

        if metadata is None:
            metadata = {}

        chunks = []

        # Handle different chunking strategies
        if self.preserve_paragraphs:
            chunks = self._chunk_by_paragraphs(text, metadata)
        elif self.preserve_sentences:
            chunks = self._chunk_by_sentences(text, metadata)
        else:
            chunks = self._chunk_by_characters(text, metadata)

        # Add overlap to chunks
        if len(chunks) > 1:
            chunks = self._add_overlap(chunks, text)

        logger.debug(f"Created {len(chunks)} chunks from {len(text)} characters")
        return chunks

    def _chunk_by_paragraphs(
        self, text: str, metadata: Dict[str, Any]
    ) -> List[TextChunk]:
        """Chunk text preserving paragraph boundaries"""
        paragraphs = self.paragraph_breaks.split(text)
        chunks = []
        current_chunk = ""
        start_index = 0

        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # If adding this paragraph would exceed chunk size, finalize current chunk
            if (
                current_chunk
                and len(current_chunk) + len(paragraph) + 2 > self.chunk_size
            ):
                chunk = TextChunk(
                    text=current_chunk.strip(),
                    start_index=start_index,
                    end_index=start_index + len(current_chunk),
                    chunk_id=f"chunk_{len(chunks)}",
                    metadata={
                        **metadata,
                        "chunk_type": "paragraph",
                        "paragraph_count": i,
                    },
                )
                chunks.append(chunk)

                # Start new chunk
                start_index = start_index + len(current_chunk) - self.overlap
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph

        # Add final chunk
        if current_chunk:
            chunk = TextChunk(
                text=current_chunk.strip(),
                start_index=start_index,
                end_index=start_index + len(current_chunk),
                chunk_id=f"chunk_{len(chunks)}",
                metadata={
                    **metadata,
                    "chunk_type": "paragraph",
                    "paragraph_count": len(paragraphs),
                },
            )
            chunks.append(chunk)

        return chunks

    def _chunk_by_sentences(
        self, text: str, metadata: Dict[str, Any]
    ) -> List[TextChunk]:
        """Chunk text preserving sentence boundaries"""
        sentences = self._split_sentences(text)
        chunks = []
        current_chunk = ""
        start_index = 0

        for i, sentence in enumerate(sentences):
            # If adding this sentence would exceed chunk size, finalize current chunk
            if (
                current_chunk
                and len(current_chunk) + len(sentence) + 1 > self.chunk_size
            ):
                chunk = TextChunk(
                    text=current_chunk.strip(),
                    start_index=start_index,
                    end_index=start_index + len(current_chunk),
                    chunk_id=f"chunk_{len(chunks)}",
                    metadata={
                        **metadata,
                        "chunk_type": "sentence",
                        "sentence_count": i,
                    },
                )
                chunks.append(chunk)

                # Start new chunk
                start_index = start_index + len(current_chunk) - self.overlap
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence

        # Add final chunk
        if current_chunk:
            chunk = TextChunk(
                text=current_chunk.strip(),
                start_index=start_index,
                end_index=start_index + len(current_chunk),
                chunk_id=f"chunk_{len(chunks)}",
                metadata={
                    **metadata,
                    "chunk_type": "sentence",
                    "sentence_count": len(sentences),
                },
            )
            chunks.append(chunk)

        return chunks

    def _chunk_by_characters(
        self, text: str, metadata: Dict[str, Any]
    ) -> List[TextChunk]:
        """Simple character-based chunking"""
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))

            # Try to break at word boundary if possible
            if end < len(text):
                # Look backward for a space
                for i in range(end, max(start, end - 100), -1):
                    if text[i].isspace():
                        end = i
                        break

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk = TextChunk(
                    text=chunk_text,
                    start_index=start,
                    end_index=end,
                    chunk_id=f"chunk_{len(chunks)}",
                    metadata={**metadata, "chunk_type": "character"},
                )
                chunks.append(chunk)

            start = max(start + self.chunk_size - self.overlap, end)

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences with better handling of edge cases"""
        # Simple sentence splitting - can be enhanced with spaCy/NLTK
        sentences = []
        current_sentence = ""

        # Split by sentence endings but preserve context
        parts = self.sentence_endings.split(text)

        for i, part in enumerate(parts):
            current_sentence += part.strip()

            # If this isn't the last part, add the sentence ending back
            if i < len(parts) - 1:
                # Find the sentence ending that was removed
                remaining_text = text[len("".join(parts[: i + 1])) :]
                match = self.sentence_endings.match(remaining_text)
                if match:
                    current_sentence += match.group()

                if current_sentence.strip():
                    sentences.append(current_sentence.strip())
                    current_sentence = ""

        # Add any remaining text
        if current_sentence.strip():
            sentences.append(current_sentence.strip())

        return [s for s in sentences if s.strip()]

    def _add_overlap(
        self, chunks: List[TextChunk], original_text: str
    ) -> List[TextChunk]:
        """Add overlap between chunks for better context"""
        if not chunks or self.overlap <= 0:
            return chunks

        overlapped_chunks = [chunks[0]]  # First chunk remains the same

        for i in range(1, len(chunks)):
            current_chunk = chunks[i]
            previous_chunk = chunks[i - 1]

            # Get overlap text from the end of the previous chunk
            overlap_start = max(0, len(previous_chunk.text) - self.overlap)
            overlap_text = previous_chunk.text[overlap_start:].strip()

            # Add overlap to the beginning of current chunk
            if overlap_text and not current_chunk.text.startswith(overlap_text):
                new_text = overlap_text + " " + current_chunk.text

                # Create new chunk with overlap
                new_chunk = TextChunk(
                    text=new_text,
                    start_index=current_chunk.start_index - len(overlap_text) - 1,
                    end_index=current_chunk.end_index,
                    chunk_id=current_chunk.chunk_id,
                    metadata={**current_chunk.metadata, "has_overlap": True},
                )
                overlapped_chunks.append(new_chunk)
            else:
                overlapped_chunks.append(current_chunk)

        return overlapped_chunks

    def merge_chunks(
        self, chunks: List[TextChunk], max_merged_size: Optional[int] = None
    ) -> List[TextChunk]:
        """Merge small chunks together to optimize processing"""
        if not chunks:
            return []

        if max_merged_size is None:
            max_merged_size = self.chunk_size * 2

        merged_chunks = []
        current_merged = chunks[0]

        for i in range(1, len(chunks)):
            chunk = chunks[i]

            # Check if we can merge with current chunk
            potential_size = len(current_merged.text) + len(chunk.text) + 1

            if potential_size <= max_merged_size:
                # Merge chunks
                merged_text = current_merged.text + " " + chunk.text
                current_merged = TextChunk(
                    text=merged_text,
                    start_index=current_merged.start_index,
                    end_index=chunk.end_index,
                    chunk_id=f"merged_{current_merged.chunk_id}_{chunk.chunk_id}",
                    metadata={
                        **current_merged.metadata,
                        "merged": True,
                        "original_chunks": [current_merged.chunk_id, chunk.chunk_id],
                    },
                )
            else:
                # Can't merge, add current to results and start new
                merged_chunks.append(current_merged)
                current_merged = chunk

        # Add the last chunk
        merged_chunks.append(current_merged)

        logger.debug(f"Merged {len(chunks)} chunks into {len(merged_chunks)} chunks")
        return merged_chunks


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
    preserve_sentences: bool = True,
) -> List[str]:
    """
    Simple function interface for text chunking
    Returns list of chunk texts
    """
    chunker = TextChunker(
        chunk_size=chunk_size, overlap=overlap, preserve_sentences=preserve_sentences
    )

    chunks = chunker.chunk_text(text)
    return [chunk.text for chunk in chunks]


def chunk_text_with_metadata(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[TextChunk]:
    """
    Function interface for text chunking with full metadata
    Returns list of TextChunk objects
    """
    chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
    return chunker.chunk_text(text, metadata)
