"""Search-link builders and best-effort Vinted catalog fetch."""

from __future__ import annotations

from urllib.parse import quote_plus

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def build_links(description: dict, image_public_url: str | None) -> dict:
    query = description.get("search_query") or "clothing"
    q = quote_plus(query)

    links: dict[str, str] = {
        "vinted": f"https://www.vinted.com/catalog?search_text={q}",
        "google_shopping": f"https://www.google.com/search?tbm=shop&q={q}",
        "google_images": f"https://www.google.com/search?tbm=isch&q={q}",
    }

    if image_public_url:
        links["google_lens"] = (
            f"https://lens.google.com/uploadbyurl?url={quote_plus(image_public_url)}"
        )

    brand = (description.get("brand_guess") or "").strip()
    confidence = (description.get("confidence") or "").lower()
    if brand and confidence in {"medium", "high"}:
        domain = _brand_domain_hint(brand)
        if domain:
            site_query = f"{query} site:{domain}"
            links["brand_site"] = (
                f"https://www.google.com/search?q={quote_plus(site_query)}"
            )

    return links


def _brand_domain_hint(brand: str) -> str:
    slug = "".join(c for c in brand.lower() if c.isalnum())
    return f"{slug}.com" if slug else ""


async def fetch_vinted_top(description: dict, limit: int = 8) -> list[dict]:
    """Best-effort: pull top Vinted listings for the search query. Returns [] on failure."""
    query = description.get("search_query") or ""
    if not query:
        return []

    try:
        async with httpx.AsyncClient(
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=10.0,
            follow_redirects=True,
        ) as client:
            warmup = await client.get("https://www.vinted.com/")
            if warmup.status_code >= 400:
                return []

            resp = await client.get(
                "https://www.vinted.com/api/v2/catalog/items",
                params={
                    "search_text": query,
                    "per_page": str(limit),
                    "page": "1",
                    "order": "relevance",
                },
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return []

    items_raw = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items_raw, list):
        return []

    results: list[dict] = []
    for item in items_raw[:limit]:
        if not isinstance(item, dict):
            continue
        photo = item.get("photo") or {}
        price = item.get("price")
        if isinstance(price, dict):
            amount = price.get("amount")
            currency = price.get("currency_code", "")
            price_str = f"{amount} {currency}".strip() if amount else ""
        else:
            price_str = str(price) if price else ""

        results.append(
            {
                "title": item.get("title") or "Untitled",
                "price": price_str,
                "url": item.get("url") or "",
                "thumbnail": photo.get("url") if isinstance(photo, dict) else "",
                "brand": item.get("brand_title") or "",
                "size": item.get("size_title") or "",
            }
        )

    return results
