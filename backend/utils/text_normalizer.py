import re
import unicodedata
from collections import Counter


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"-\n(?=\w)", "", text)

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    lines = _drop_repeated_header_footer(lines)

    return "\n".join(lines).strip()


def _drop_repeated_header_footer(lines: list[str]) -> list[str]:
    if len(lines) < 6:
        return lines

    counts = Counter(lines)
    repeated = {line for line, count in counts.items() if count > 2 and len(line) < 60}
    return [line for line in lines if line not in repeated]
