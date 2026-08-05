import uuid

import boto3
from PIL import Image
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.db import SessionLocal
from app.models import Meme

model = SentenceTransformer(settings.embedding_model_name)
s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
)

def embed_image(image: Image.Image) -> list[float]:
    return model.encode(image, normalize_embeddings=True).tolist()


def upload_image(image_bytes: bytes, content_type: str) -> tuple[str, str]:
    image_key = f"memes/{uuid.uuid4()}.jpg"
    s3_client.put_object(
        Bucket=settings.s3_bucket_name,
        Key=image_key,
        Body=image_bytes,
        ContentType=content_type,
    )
    image_url = f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{image_key}"
    return (image_key, image_url)

def ingest_meme(
    image: Image.Image,
    image_bytes: bytes,
    content_type: str,
    source: str,
    language: str = "en",
    caption: str | None = None,
) -> Meme:
    embedding = embed_image(image)
    image_key, image_url = upload_image(image_bytes, content_type)
    width, height = image.size
    meme= Meme(
        image_key=image_key,
        image_url=image_url,
        source=source,
        language=language,
        caption=caption,
        embedding=embedding,
        width=width,
        height=height,
        file_size_bytes=len(image_bytes),
    )
    db = SessionLocal()
    try:
        db.add(meme)
        db.commit()
        db.refresh(meme)
        return meme
    finally:
        db.close()