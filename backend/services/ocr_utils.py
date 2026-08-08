from pathlib import Path

import pytesseract
from PIL import Image


def ocr_images(images: list[Image.Image]) -> str:
    return "\n".join(pytesseract.image_to_string(image) for image in images)


def ocr_image_file(path: Path) -> str:
    with Image.open(path) as image:
        return pytesseract.image_to_string(image)
