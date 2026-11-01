"""PII masking for anything that reaches the logs (constitution: no PII in logs)."""

import re

_EMAIL = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")
# Brazilian phones: optional +55, optional DDD in parentheses, 8-9 digit number, loose separators.
_PHONE = re.compile(
    r"(?<![\d-])(?:\+?55[\s-]?)?(?:\(?\d{2}\)?[\s-]?)(?:9\s?)?\d{4}[\s-]?(\d{4})(?![\d-])"
)


def mask_pii(text: str) -> str:
    text = _EMAIL.sub(r"***@\1", text)
    return _PHONE.sub(r"(**) *****-\1", text)
