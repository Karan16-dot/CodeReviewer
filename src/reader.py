import tiktoken
from pathlib import Path
from typing import List, Union

class FileReader:
    """Provides utility methods for safe text file reading, token estimation, and text chunking."""

    def __init__(self, default_encoding: str = "utf-8"):
        self.default_encoding = default_encoding

    def read_file(self, path: Union[str, Path]) -> str:
        """
        Reads file content, trying the default encoding first and falling back
        to Latin-1, UTF-16, and UTF-8-sig as necessary.

        Args:
            path: Target file path.

        Returns:
            Decoded file text content.

        Raises:
            FileNotFoundError: If target path does not exist.
            IsADirectoryError: If path is a directory.
            UnicodeDecodeError: If decoding fails with all attempted encodings.
        """
        file_path = Path(path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not file_path.is_file():
            raise IsADirectoryError(f"Path is a directory, not a file: {file_path}")

        encodings = [self.default_encoding, "utf-8-sig", "utf-16", "latin-1"]
        last_err = None

        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, LookupError) as e:
                last_err = e
                continue

        raise last_err or UnicodeDecodeError(
            f"Could not decode file {file_path} with any attempted encoding."
        )

    def count_tokens(self, text: str, model: str = "gpt-4o-mini") -> int:
        """
        Counts the number of tokens in the given text using tiktoken.

        Args:
            text: Input string content.
            model: Target model model name.

        Returns:
            Integer token counts.
        """
        try:
            encoding = tiktoken.encoding_for_model(model)
        except Exception:
            try:
                # Default fallback encoding model
                encoding = tiktoken.get_encoding("cl100k_base")
            except Exception:
                # Character-based approximation fallback (~4 characters per token)
                return len(text) // 4
        return len(encoding.encode(text))

    def chunk_text(
        self,
        text: str,
        max_tokens: int = 2000,
        overlap_tokens: int = 200,
        model: str = "gpt-4o-mini"
    ) -> List[str]:
        """
        Chunks text based on token limits with an overlapping window.

        Args:
            text: Input string content.
            max_tokens: Maximum tokens allowed per chunk.
            overlap_tokens: Overlap tokens count between chunks.
            model: Target model model name.

        Returns:
            List of chunked strings.
        """
        try:
            encoding = tiktoken.encoding_for_model(model)
        except Exception:
            encoding = tiktoken.get_encoding("cl100k_base")

        tokens = encoding.encode(text)
        chunks = []

        if len(tokens) <= max_tokens:
            return [text]

        start = 0
        while start < len(tokens):
            end = min(start + max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunks.append(encoding.decode(chunk_tokens))

            if end == len(tokens):
                break

            start += max_tokens - overlap_tokens
            if start >= end:
                start = end

        return chunks
