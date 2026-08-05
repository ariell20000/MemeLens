from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import TIMESTAMP, BigInteger, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Meme(Base):
    __tablename__ = "memes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    image_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(Text, nullable=False, server_default="en")
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(512), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
