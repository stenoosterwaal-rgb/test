"""Clothing Finder — FastAPI app.

Upload a clothing photo, get a structured description from a vision LLM, and
search links to find the item on Vinted, Google Lens, and Google Shopping.
"""

from __future__ import annotations

import io
import os
import uuid
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image

from search import build_links, fetch_vinted_top
from vision import describe_item

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB
MAX_IMAGE_DIM = 1024
IMAGE_STORE_CAP = 32

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Clothing Finder")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Image store: id -> (jpeg_bytes,). OrderedDict for LRU eviction.
IMAGE_STORE: "OrderedDict[str, bytes]" = OrderedDict()


def _store_image(jpeg_bytes: bytes) -> str:
    image_id = uuid.uuid4().hex
    IMAGE_STORE[image_id] = jpeg_bytes
    while len(IMAGE_STORE) > IMAGE_STORE_CAP:
        IMAGE_STORE.popitem(last=False)
    return image_id


def _prepare_image(raw: bytes) -> bytes:
    """Validate, downscale, and re-encode as JPEG."""
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Not a valid image: {exc}")

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    img.thumbnail((MAX_IMAGE_DIM, MAX_IMAGE_DIM), Image.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85, optimize=True)
    return out.getvalue()


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
async def status() -> dict:
    return {"has_api_key": bool(os.environ.get("GROQ_API_KEY"))}


@app.post("/api/analyze")
async def analyze(request: Request, image: UploadFile = File(...)) -> JSONResponse:
    if not os.environ.get("GROQ_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is not configured on the server.",
        )

    raw = await image.read()
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Empty upload.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image is larger than 8 MB.")

    prepared = _prepare_image(raw)
    image_id = _store_image(prepared)

    try:
        description = describe_item(prepared, mime_type="image/jpeg")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Vision model failed: {exc}")

    base_url = str(request.base_url).rstrip("/")
    image_public_url = f"{base_url}/api/image/{image_id}"
    links = build_links(description, image_public_url)

    vinted_items = await fetch_vinted_top(description)

    return JSONResponse(
        {
            "image_id": image_id,
            "image_url": image_public_url,
            "description": description,
            "links": links,
            "vinted_items": vinted_items,
        }
    )


@app.get("/api/image/{image_id}")
async def get_image(image_id: str) -> Response:
    data = IMAGE_STORE.get(image_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found or expired.")
    IMAGE_STORE.move_to_end(image_id)
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )
