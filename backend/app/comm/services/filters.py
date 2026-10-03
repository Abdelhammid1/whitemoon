"""Contact-exchange detection — EPIC 10 (US-10.2).

The core of the customer↔supplier isolation: a message may not carry a phone
number in *any* form. The detector works on a single "digit signal" so the
usual evasions collapse into one check:

- digits with arbitrary separators (0101-234-5678, "0 1 0 1 …", "0101،234"),
- Arabic-Indic (٠١٢) and Persian (۰۱۲) numerals,
- numbers spelled as words, Arabic and English ("صفر واحد …", "zero one …"),
- short filler tokens between digits (homoglyph letters like O/l, connectives
  like "و"/"and") are treated as non-breaking, so they can't split a run.

Plus a pass for e-mail addresses and social handles / links (the same
evasion by another channel).

`scan_text` returns a block-reason code when a message must be withheld.
Images are OCR'd and run through the same detector; if an image can't be
scanned the caller fails **closed** (blocks), never open.
"""

from __future__ import annotations

import re

# A run of this many digit-equivalents looks like a phone number (Egypt
# landline is 7–8 local digits, mobile 11). Deliberately low: over-blocking a
# long numeric string is acceptable, letting a number through is not.
MIN_PHONE_DIGITS = 7
# Non-digit word tokens this short (homoglyph letters, "و"/"and"/"is") are
# treated as filler and do not break a digit run.
MAX_FILLER_LEN = 3

_ARABIC_INDIC = "٠١٢٣٤٥٦٧٨٩"
_PERSIAN = "۰۱۲۳۴۵۶۷۸۹"
_DIGIT_TRANSLATION = {ord(c): str(i) for i, c in enumerate(_ARABIC_INDIC)}
_DIGIT_TRANSLATION.update({ord(c): str(i) for i, c in enumerate(_PERSIAN)})
_TATWEEL = "ـ"

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_SOCIAL = re.compile(
    r"(?:wa\.me|whatsapp|telegram|t\.me|instagram|facebook|@[A-Za-z0-9._]{3,})",
    re.IGNORECASE,
)

# tokens: a run of ASCII digits, or a run of letters (Latin or Arabic).
_TOKEN = re.compile(r"[0-9]+|[A-Za-z؀-ۿ]+")

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


def _normalize(text: str) -> str:
    return text.translate(_DIGIT_TRANSLATION).replace(_TATWEEL, "")


def _max_digit_run(text: str) -> int:
    """Longest run of digit-equivalents, allowing short filler tokens between
    them (so separators, homoglyph letters, and connectives can't split it)."""
    run = 0
    best = 0
    for tok in _TOKEN.findall(_normalize(text)):
        if tok.isdigit():
            run += len(tok)
        elif tok.lower() in _SPELLED_DIGITS:
            run += 1
        elif len(tok) <= MAX_FILLER_LEN:
            # Filler (homoglyph letter, connective) — neither adds nor breaks.
            continue
        else:
            run = 0
        best = max(best, run)
    return best


def scan_text(text: str | None) -> str | None:
    """Return a block-reason code if the text leaks contact info, else None."""
    if not text:
        return None
    if _max_digit_run(text) >= MIN_PHONE_DIGITS:
        return "phone_number"
    if _EMAIL.search(text):
        return "email_address"
    if _URL.search(text) or _SOCIAL.search(text):
        return "external_contact"
    return None


def extract_image_text(data: bytes) -> str | None:
    """OCR an uploaded image to text (US-10.2).

    Returns the extracted text, or ``None`` if the image could not be scanned
    at all (OCR stack missing / unreadable image). ``None`` is distinct from
    ``""`` (scanned, no text) so the caller can fail CLOSED on an unscannable
    image rather than letting it through.
    """
    try:
        import io

        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(img, lang="ara+eng")
    except Exception:
        return None


def scan_message(*, body: str | None, image_bytes: bytes | None) -> str | None:
    """Scan a message's text and, if present, its image. An image that cannot
    be OCR-scanned is blocked (fail closed), since it may hide a number."""
    reason = scan_text(body)
    if reason is not None:
        return reason
    if image_bytes:
        text = extract_image_text(image_bytes)
        if text is None:
            return "image_unscannable"
        reason = scan_text(text)
        if reason is not None:
            return f"image_{reason}"
    return None
