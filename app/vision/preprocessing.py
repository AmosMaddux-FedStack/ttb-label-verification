from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_LONG_EDGE = 1600
JPEG_QUALITY = 82


class ImagePreprocessingError(ValueError):
    pass


@dataclass(frozen=True)
class PreparedImage:
    data: bytes
    content_type: str
    width: int
    height: int


def prepare_image(image_bytes: bytes) -> PreparedImage:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            corrected = ImageOps.exif_transpose(image)
            rgb = corrected.convert("RGB")
            resized = _resize_to_long_edge(rgb, MAX_LONG_EDGE)
            output = BytesIO()
            resized.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            data = output.getvalue()
            return PreparedImage(
                data=data,
                content_type="image/jpeg",
                width=resized.width,
                height=resized.height,
            )
    except (OSError, UnidentifiedImageError) as exc:
        raise ImagePreprocessingError("Input could not be processed as an image.") from exc


def _resize_to_long_edge(image: Image.Image, max_long_edge: int) -> Image.Image:
    long_edge = max(image.size)
    if long_edge <= max_long_edge:
        return image.copy()

    scale = max_long_edge / long_edge
    size = (round(image.width * scale), round(image.height * scale))
    return image.resize(size, Image.Resampling.LANCZOS)
