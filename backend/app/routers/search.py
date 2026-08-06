from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.ingest_service import embed_text

router = APIRouter(prefix="/api/search", tags=["search"])

SEARCH_SQL = text(
    "SELECT id, image_url, caption, source, 1 - (embedding <=> :q) AS score "
    "FROM memes "
    "ORDER BY embedding <=> :q "
    "LIMIT :k"
)


@router.get("")
def search(q: str, k: int = 12, db: Session = Depends(get_db)):
    embedding = embed_text(q)
    result = db.execute(SEARCH_SQL, {"q": str(embedding), "k": k})
    return [dict(row._mapping) for row in result]
