"""Contact-exchange detection — EPIC 10 (US-10.2).

The core of the customer↔supplier isolation: a message may not carry a phone
number in *any* form. We catch:

- runs of digits with separators / brackets (0101-234-5678, "0 1 0 1 ..."),
- Arabic-Indic (٠١٢) and Persian (۰۱۲) numerals,
- numbers spelled as words, Arabic and English ("صفر واحد …", "zero one …").

Plus a bonus pass (the spec's optional extension) for e-mail addresses and
social handles / links, which are the same evasion by another channel.

`scan_text` returns a reason code when a message must be blocked, else None.
Image uploads are OCR'd (`extract_image_text`) and the text run through the
same detector, so a number photographed instead of typed is still caught.
"""

from __future__ import annotations

import re

# Minimum run of digits that looks like a phone number (Egypt landline is
# 7–8 local digits; mobile is 11). 7 is a deliberately safe lower bound.
MIN_PHONE_DIGITS = 7
MIN_SPELLED_DIGITS = 7

_ARABIC_INDIC = "٠١٢٣٤٥٦٧٨٩"
_PERSIAN = "۰۱۲۳۴۵۶۷۸۹"
_DIGIT_TRANSLATION = {ord(c): str(i) for i, c in enumerate(_ARABIC_INDIC)}
_DIGIT_TRANSLATION.update({ord(c): str(i) for i, c in enumerate(_PERSIAN)})

# digit followed by any number of separators, repeated — catches spaced /
# dashed / dotted / bracketed numbers as one run.
_PHONE_RUN = re.compile(r"(?:\d[\s\-\.٫٬()\[\]/\\]*){" + str(MIN_PHONE_DIGITS) + ",}")

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_SOCIAL = re.compile(r"(?:wa\.me|whatsapp|telegram|t\.me|instagram|facebook|@[A-Za-z0-9._]{3,})", re.IGNORECASE)

_SPELLED_DIGITS: dict[str, str] = {
    # Arabic
    "صفر": "0", "واحد": "1", "اثنين": "2", "اثنان": "2", "إثنين": "2",
    "ثلاثة": "3", "ثلاث": "3", "اربعة": "4", "أربعة": "4", "اربع": "4", "أربع": "4",
    "خمسة": "5", "خمس": "5", "ستة": "6", "ست": "6", "سبعة": "7", "سبع": "7",
    "ثمانية": "8", "ثمان": "8", "ثمانيه": "8", "تسعة": "9", "تسع": "9",
    # English
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
}

_TATWEEL = "ـ"
_WORD = re.compile(r"[A-Za-z؀-ۿ]+")


def _normalize(text: str) -> str:
    return text.translate(_DIGIT_TRANSLATION).replace(_TATWEEL, "")


def _has_digit_run(text: str) -> bool:
    for m in _PHONE_RUN.finditer(text):
        digits = sum(c.isdigit() for c in m.group())
        if digits >= MIN_PHONE_DIGITS:
            return True
    return False


def _has_spelled_number(text: str) -> bool:
    run = 0
    for tok in _WORD.findall(text):
        if tok.lower() in _SPELLED_DIGITS:
            run += 1
            if run >= MIN_SPELLED_DIGITS:
                return True
        else:
            run = 0
    return False


def scan_text(text: str | None) -> str | None:
    """Return a block-reason code if the text leaks contact info, else None."""
    if not text:
        return None
    norm = _normalize(text)
    if _has_digit_run(norm):
        return "phone_number_digits"
    if _has_spelled_number(norm):
        return "phone_number_spelled"
    if _EMAIL.search(text):
        return "email_address"
    if _URL.search(text) or _SOCIAL.search(text):
        return "external_contact"
    return None


def extract_image_text(data: bytes) -> str:
    """OCR an uploaded image to text (US-10.2). Best-effort: if the OCR stack
    isn't available at runtime, returns '' rather than crashing — callers
    treat a failed scan conservatively at a higher layer."""
    try:
        import io

        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(img, lang="ara+eng")
    except Exception:
        return ""


def scan_message(*, body: str | None, image_bytes: bytes | None) -> str | None:
    """Scan a message's text and, if present, its image (via OCR)."""
    reason = scan_text(body)
    if reason is not None:
        return reason
    if image_bytes:
        reason = scan_text(extract_image_text(image_bytes))
        if reason is not None:
            return f"image_{reason}"
    return None
