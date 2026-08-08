from pathlib import Path

import pdfplumber
from pdf2image import convert_from_path
from PIL import Image


def extract_pdf_text(path: Path) -> tuple[str, int]:
    with pdfplumber.open(path) as pdf:
        pages_text = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages_text), len(pdf.pages)


def convert_pdf_to_images(path: Path) -> list[Image.Image]:
    return convert_from_path(str(path), dpi=300)
