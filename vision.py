"""Groq vision call: image bytes -> structured description JSON."""

from __future__ import annotations

import base64
import json
import os

from openai import OpenAI

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
PRIMARY_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
FALLBACK_MODEL = "llama-3.2-90b-vision-preview"

SYSTEM_PROMPT = (
    "You are a fashion identification expert. Given a photo of a clothing item, "
    "extract a structured description that can be used to find the exact item on "
    "resale sites (Vinted) and the original seller's website. Respond ONLY with "
    "valid JSON matching this schema:\n"
    "{\n"
    '  "brand_guess": string | null,        // Best guess at the brand, or null if not identifiable\n'
    '  "item_type": string,                 // e.g. "hoodie", "denim jacket", "sneakers"\n'
    '  "colour": string,                    // Primary colour(s)\n'
    '  "pattern": string | null,            // e.g. "striped", "floral", or null if plain\n'
    '  "material_guess": string | null,     // e.g. "denim", "leather", "cotton"\n'
    '  "distinctive_features": [string],    // Logos, prints, cuts, hardware, etc.\n'
    '  "search_query": string,              // Short search string (3-7 words) optimised for Vinted/Google\n'
    '  "confidence": "low" | "medium" | "high"\n'
    "}\n"
    "Be specific but concise. The search_query is the most important field — make it the "
    "kind of query a human shopper would type to find this exact item."
)


def _client() -> OpenAI:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")
    return OpenAI(base_url=GROQ_BASE_URL, api_key=api_key)


def _call(model: str, data_url: str) -> str:
    client = _client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Identify this clothing item."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=600,
    )
    return response.choices[0].message.content or "{}"


def describe_item(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """Send image to Groq vision model and return a structured description dict."""
    encoded = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded}"

    try:
        raw = _call(PRIMARY_MODEL, data_url)
    except Exception:
        raw = _call(FALLBACK_MODEL, data_url)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {}

    parsed.setdefault("brand_guess", None)
    parsed.setdefault("item_type", "clothing item")
    parsed.setdefault("colour", "")
    parsed.setdefault("pattern", None)
    parsed.setdefault("material_guess", None)
    parsed.setdefault("distinctive_features", [])
    parsed.setdefault("confidence", "low")

    if not parsed.get("search_query"):
        parts = [
            parsed.get("brand_guess") or "",
            parsed.get("colour") or "",
            parsed.get("item_type") or "",
        ]
        parsed["search_query"] = " ".join(p for p in parts if p).strip() or "clothing"

    return parsed
