import re
from datetime import date, datetime
from typing import Optional

DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d %b %Y", "%B %d, %Y")


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_float(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", value)
    try:
        return float(cleaned)
    except ValueError:
        return None
