import csv
from pathlib import Path

from PIL import Image

from app.ingest_service import ingest_meme

DATASET_DIR = Path("/tmp/gm_full")
METADATA_CSV = DATASET_DIR / "metadata.csv"


def main() -> None:
    with open(METADATA_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            image_path = DATASET_DIR / row["dataset"] / row["dataset"] / row["label"] / row["image"]
            if not image_path.exists():
                print(f"[{i}] skip, missing file: {image_path}")
                continue

            image_bytes = image_path.read_bytes()
            image = Image.open(image_path).convert("RGB")

            try:
                meme = ingest_meme(
                    image=image,
                    image_bytes=image_bytes,
                    content_type="image/jpeg",
                    source="kaggle_meme_generator",
                    caption=row["label"],
                )
                print(f"[{i}] ingested meme id={meme.id} ({row['label']})")
            except Exception as exc:
                print(f"[{i}] FAILED {image_path}: {exc}")


if __name__ == "__main__":
    main()
