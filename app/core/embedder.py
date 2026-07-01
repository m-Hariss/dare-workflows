import requests

from app.storage.key_store import get as get_key

_MODEL   = "text-embedding-3-large"
_API_URL = "https://api.openai.com/v1/embeddings"
_BATCH_SIZE = 50  # max chunks per API call


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Convert a list of text chunks into embedding vectors using OpenAI API.

    Sends chunks in batches to avoid hitting API limits.
    Returns one vector per input text, in the same order.
    """
    api_key = get_key("openai")
    if not api_key:
        raise RuntimeError("No OpenAI API key configured. Add one via the API Keys modal.")

    all_vectors = []

    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i: i + _BATCH_SIZE]

        response = requests.post(
            _API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={"model": _MODEL, "input": batch},
            timeout=60,
        )

        if not response.ok:
            raise RuntimeError(
                f"Embedding API call failed ({response.status_code}): {response.text[:200]}"
            )

        data = sorted(response.json()["data"], key=lambda x: x["index"])
        all_vectors.extend(d["embedding"] for d in data)

    return all_vectors


def embed_one(text: str) -> list[float]:
    """Convert a single text into an embedding vector."""
    return embed_batch([text])[0]
