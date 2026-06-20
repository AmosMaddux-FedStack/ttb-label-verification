import argparse
import asyncio
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.vision.client import VisionConfigurationError
from app.vision.service import VisionService


SAMPLE_PATH = Path("samples/sample_label.jpg")


def create_sample_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1400, 900), "white")
    draw = ImageDraw.Draw(image)
    lines = [
        "ACME RESERVE",
        "RED WINE",
        "Produced by Acme Winery LLC",
        "United States",
        "13.5% Alc. by Vol.",
        "750 mL",
        "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink",
        "alcoholic beverages during pregnancy because of the risk of birth defects.",
        "(2) Consumption of alcoholic beverages impairs your ability to drive a car or",
        "operate machinery, and may cause health problems.",
    ]
    y = 70
    for line in lines:
        draw.text((70, y), line, fill="black")
        y += 72
    image.save(path, format="JPEG", quality=92)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run VisionService against one sample label image.")
    parser.add_argument(
        "image_path",
        nargs="?",
        default=str(SAMPLE_PATH),
        help="Path to an image. Defaults to samples/sample_label.jpg and creates it if missing.",
    )
    args = parser.parse_args()

    image_path = Path(args.image_path)
    if image_path == SAMPLE_PATH and not image_path.exists():
        create_sample_image(image_path)

    try:
        service = VisionService.from_env()
    except VisionConfigurationError as exc:
        raise SystemExit(f"{exc} Set OPENAI_API_KEY and rerun this script.") from exc

    extracted = await service.extract_label(image_path.read_bytes(), filename=image_path.name)
    print(json.dumps(extracted.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
