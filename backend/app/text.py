import re
import unicodedata

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍﻿"))
_WHITESPACE = re.compile(r"\s+")


def nfc(text: str) -> str:
    """Canonical text form used everywhere: NFC, without zero-width characters."""
    return unicodedata.normalize("NFC", text).translate(_ZERO_WIDTH)


def normalize_for_cache(text: str) -> str:
    """Key form for query caching: trivially different queries share one key."""
    return _WHITESPACE.sub(" ", nfc(text).casefold()).strip()
