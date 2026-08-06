import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel

from app.auth import require_admin
from app.ingest_service import ingest_meme

router = APIRouter(prefix="/api/memes", tags=["memes"])


class MemeCreateResponse(BaseModel):
    id: int
    image_url: str


@router.post(
    "",
    status_code=201,
    dependencies=[Depends(require_admin)],
    response_model=MemeCreateResponse,
)
async def create_meme(
    image: UploadFile = File(...),
    caption: str | None = Form(None),
    language: str = Form("en"),
):
    image_bytes = await image.read()
    try:
        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid image file") from exc

    meme = ingest_meme(
        image=pil_image,
        image_bytes=image_bytes,
        content_type=image.content_type or "image/jpeg",
        source="manual",
        language=language,
        caption=caption,
    )
    return MemeCreateResponse(id=meme.id, image_url=meme.image_url)
