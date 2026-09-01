def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """
    Splits the input text into chunks of specified size.

    Args:
        text (str): The input text to be chunked.
        chunk_size (int): The maximum size of each chunk.

    Returns:
        list: A list containing the text chunks.
    """

    if not text or chunk_size <= 0:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk.strip())

        start += chunk_size - chunk_overlap
    return chunks
