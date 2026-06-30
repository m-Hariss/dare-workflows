import json
from pathlib import Path

_DATA_DIR  = Path(__file__).resolve().parents[2] / ".data"
_KEYS_FILE = _DATA_DIR / "keys.json"

SUPPORTED_PROVIDERS = {"openai", "claude", "gemini", "ollama"}


def _read() -> dict:
    """Read the keys file from disk, returning an empty dict if it doesn't exist."""
    if not _KEYS_FILE.exists():
        return {}
    return json.loads(_KEYS_FILE.read_text())


def _write(data: dict) -> None:
    """Write the keys dict to disk."""
    _DATA_DIR.mkdir(exist_ok=True)
    _KEYS_FILE.write_text(json.dumps(data, indent=2))


def set(provider: str, key: str) -> None:
    """Save an API key for a provider."""
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider '{provider}'. Choose from: {SUPPORTED_PROVIDERS}")
    data = _read()
    data[provider] = key
    _write(data)


def get(provider: str) -> str | None:
    """Return the API key for a provider, or None if not set."""
    return _read().get(provider)


def delete(provider: str) -> None:
    """Remove the API key for a provider."""
    data = _read()
    data.pop(provider, None)
    _write(data)


def all_statuses() -> dict:
    """Return which providers have a key configured (True/False, not the key itself)."""
    data = _read()
    return {provider: provider in data for provider in SUPPORTED_PROVIDERS}
