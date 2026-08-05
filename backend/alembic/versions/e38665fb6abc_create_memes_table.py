"""create memes table

Revision ID: e38665fb6abc
Revises: 
Create Date: 2026-08-04 15:31:06.044955

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision: str = 'e38665fb6abc'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table("memes", sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
                    sa.Column("image_key", sa.Text, nullable=False, unique=True),
                    sa.Column("image_url", sa.Text, nullable=False),
                    sa.Column("source", sa.Text, nullable=False),
                    sa.Column("language", sa.Text, nullable=False, server_default="en"),
                    sa.Column("caption", sa.Text, nullable=True),
                    sa.Column("embedding", Vector(512), nullable=False),
                    sa.Column("width", sa.Integer, nullable=True),
                    sa.Column("height", sa.Integer, nullable=True),
                    sa.Column("file_size_bytes", sa.Integer, nullable=True),
                    sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,server_default=sa.text("now()")))
    op.execute(
        "CREATE INDEX memes_embedding_hnsw_idx "
        "ON memes USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)")


def downgrade() -> None:
    op.drop_table("memes")
