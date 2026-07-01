import requests

from app.storage.key_store import get as get_key

# Default models per provider — used when the workflow node doesn't specify one
_DEFAULTS = {
    "openai": "gpt-4o",
    "claude": "claude-sonnet-4-6",
    "gemini": "gemini-1.5-pro",
    "ollama": "llama3",
}


def call_llm(
    provider: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """Call the right LLM provider and return the response as plain text."""
    provider = (provider or "openai").lower()
    model = model or _DEFAULTS.get(provider, "")

    if provider == "openai":
        return _call_openai(model, system_prompt, user_prompt, temperature, max_tokens)
    if provider == "claude":
        return _call_claude(model, system_prompt, user_prompt, temperature, max_tokens)
    if provider == "gemini":
        return _call_gemini(model, system_prompt, user_prompt, temperature, max_tokens)
    if provider == "ollama":
        return _call_ollama(model, system_prompt, user_prompt)

    raise ValueError(f"Unknown provider '{provider}'. Supported: openai, claude, gemini, ollama")


def _call_openai(model: str, system: str, user: str, temperature: float, max_tokens: int) -> str:
    key = get_key("openai")
    if not key:
        raise RuntimeError("No OpenAI API key configured. Add one via ⚙ API Keys.")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
        timeout=120,
    )
    if not resp.ok:
        raise RuntimeError(f"OpenAI error ({resp.status_code}): {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"]


def _call_claude(model: str, system: str, user: str, temperature: float, max_tokens: int) -> str:
    key = get_key("claude")
    if not key:
        raise RuntimeError("No Claude API key configured. Add one via ⚙ API Keys.")

    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": user}],
    }
    if system:
        body["system"] = system

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=body,
        timeout=120,
    )
    if not resp.ok:
        raise RuntimeError(f"Claude error ({resp.status_code}): {resp.text[:300]}")
    return resp.json()["content"][0]["text"]


def _call_gemini(model: str, system: str, user: str, temperature: float, max_tokens: int) -> str:
    key = get_key("gemini")
    if not key:
        raise RuntimeError("No Gemini API key configured. Add one via ⚙ API Keys.")

    body = {
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        headers={"Content-Type": "application/json"},
        json=body,
        timeout=120,
    )
    if not resp.ok:
        raise RuntimeError(f"Gemini error ({resp.status_code}): {resp.text[:300]}")
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def _call_ollama(model: str, system: str, user: str) -> str:
    base_url = (get_key("ollama") or "http://localhost:11434").rstrip("/")
    prompt = f"{system}\n\n{user}" if system else user

    resp = requests.post(
        f"{base_url}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=300,
    )
    if not resp.ok:
        raise RuntimeError(f"Ollama error ({resp.status_code}): {resp.text[:300]}")
    return resp.json()["response"]
