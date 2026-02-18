from pathlib import Path
from typing import Any, Dict, List, Optional
import base64

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .fash_ai_client import HeadshotMaster


class FashAIRequest(BaseModel):
    image_b64: str = Field(..., description="Base64 or data URL string of the uploaded image")
    outfit: str = Field(..., description="Outfit type/description")
    occasion: Optional[str] = Field(None, description="Occasion (e.g. Office, Wedding, Streetwear)")
    fit: Optional[str] = Field(None, description="Fit preference (e.g. Slim, Oversized, Tailored)")
    color: Optional[str] = Field(None, description="Primary color preference")
    accessories: Optional[List[str]] = Field(None, description="List of accessories")
    vibe: Optional[str] = Field(None, description="Overall fashion vibe")
    variation: bool = Field(False, description="Whether to create a slight variation")
    ratio: str = Field("4:5", description="Aspect ratio for the generated image")


class FashAIResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    creation_id: Optional[str] = None
    result: Optional[List[Dict[str, Any]]] = None
    app: Optional[str] = None
    model: Optional[str] = None


app = FastAPI(title="Fash AI – Virtual Fashion Try-On API")

# Allow frontend to call the API if hosted separately (safe default: local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/fash-ai", response_model=FashAIResponse)
async def generate_fash_ai(payload: FashAIRequest) -> FashAIResponse:
    """
    Accepts a base64-encoded image and style preferences, converts the image
    to raw bytes, forwards them to HeadshotMaster.fash_ai, and returns the
    AI generation result.
    """
    try:
        client = HeadshotMaster()

        # Strip data URL prefix if present and decode base64 into bytes
        image_str = payload.image_b64.strip()
        if "," in image_str:
            image_str = image_str.split(",", 1)[1]
        image_bytes = base64.b64decode(image_str)

        result = client.fash_ai(
            image=image_bytes,
            outfit=payload.outfit,
            occasion=payload.occasion,
            fit=payload.fit,
            color=payload.color,
            accessories=payload.accessories,
            vibe=payload.vibe,
            variation=payload.variation,
            ratio=payload.ratio,
        )

        # Ensure we always reply with the expected schema
        if not isinstance(result, dict):
            raise ValueError("Unexpected result type from HeadshotMaster")

        # Coerce into FashAIResponse fields
        return FashAIResponse(
            success=bool(result.get("success", False)),
            error=result.get("error"),
            creation_id=result.get("creation_id"),
            result=result.get("result"),
            app=result.get("app"),
            model=result.get("model"),
        )

    except Exception as exc:
        # Surface a friendly error to the frontend
        raise HTTPException(status_code=500, detail=str(exc))


# Small inline SVG favicon served at `/favicon.ico` to avoid 404s in dev
FAVICON_SVG = """
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>
    <rect fill='#111827' width='64' height='64' rx='12'/>
    <g transform='translate(8,8) scale(0.9)'>
        <text x='50%' y='50%' font-size='36' fill='#FDE68A' text-anchor='middle' dominant-baseline='central'>🧥</text>
    </g>
</svg>
"""


@app.get('/favicon.ico')
async def favicon():
        return Response(content=FAVICON_SVG, media_type='image/svg+xml')


# ------------------------
# Static Frontend Hosting
# ------------------------

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

if FRONTEND_DIR.exists():
    # Serve the SPA (index.html) and static assets from the frontend folder.
    app.mount(
        "/",
        StaticFiles(directory=str(FRONTEND_DIR), html=True),
        name="frontend",
    )

