_CHUNK_SIZE = 1000  # characters per chunk
_OVERLAP    = 200   # characters shared between consecutive chunks


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks, breaking at natural boundaries where possible."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= _CHUNK_SIZE:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + _CHUNK_SIZE, len(text))

        # Try to break at a natural boundary instead of mid-word
        if end < len(text):
            for separator in ("\n\n", "\n", ". "):
                pos = text.rfind(separator, start, end)
                if pos != -1:
                    end = pos + len(separator)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        # Advance start by at least 1 to guarantee progress even when the
        # separator falls inside the overlap zone (would otherwise loop forever).
        new_start = end - _OVERLAP
        start = new_start if new_start > start else end

    return chunks
