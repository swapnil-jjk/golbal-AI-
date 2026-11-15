import json
import os
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class ModelResponseError(ValueError):
    """Raised when a model response cannot be used as a JSON object."""


def create_bifrost_client() -> tuple[OpenAI, str]:
    virtual_key = os.getenv("BIFROST_VIRTUAL_KEY") or os.getenv("BIFROST_API_KEY")
    api_key = os.getenv("BIFROST_API_KEY") or virtual_key
    base_url = os.getenv("BIFROST_BASE_URL", "").strip()
    model = os.getenv("BIFROST_MODEL_NAME", "").strip()

    missing = []
    if not virtual_key:
        missing.append("BIFROST_VIRTUAL_KEY (or BIFROST_API_KEY)")
    if not api_key:
        missing.append("BIFROST_API_KEY")
    if not base_url:
        missing.append("BIFROST_BASE_URL")
    if not model:
        missing.append("BIFROST_MODEL_NAME")
    if missing:
        raise ValueError(f"Missing Bifrost configuration: {', '.join(missing)}.")

    parsed_url = urlsplit(base_url.rstrip("/"))
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("BIFROST_BASE_URL must be an absolute HTTP or HTTPS URL.")

    path = parsed_url.path.rstrip("/")
    if not path.endswith(("/v1", "/openai")):
        path = f"{path}/v1"
    normalized_base_url = urlunsplit((parsed_url.scheme, parsed_url.netloc, path, parsed_url.query, ""))

    return (OpenAI(api_key=api_key, base_url=normalized_base_url, default_headers={"x-bf-vk": virtual_key}, timeout=60, max_retries=0), model)


def parse_json_object(content: Any, context: str) -> dict[str, Any]:
    if not isinstance(content, str) or not content.strip():
        raise ModelResponseError(f"{context} returned an empty response; please retry.")
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2 and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1]).strip()
            if text.lower().startswith("json"):
                text = text[4:].lstrip()
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            data, _ = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    raise ModelResponseError(f"{context} returned invalid JSON. Please retry; the model must return a JSON object.")


def response_text(response: Any, context: str) -> Any:
    choices = getattr(response, "choices", None)
    if not choices:
        raise ModelResponseError(f"{context} returned no completion choices; please retry.")
    message = getattr(choices[0], "message", None)
    if message is None:
        raise ModelResponseError(f"{context} returned no message content; please retry.")
    return getattr(message, "content", None)

