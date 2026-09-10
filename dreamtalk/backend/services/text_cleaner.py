# Dreamtalk - Voice Module
# Migrated from Dreamtalk-Voice-Cloning-Module
import re

DIGITS = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"
}
SYMBOL_MAP = {
    "\u20b9": " rupees ",
    "$": " dollars ",
    "\u20ac": " euros ",
    "\u00a3": " pounds ",
    "%": " percent ",
    "&": " and ",
    "@": " at ",
    "#": " number ",
    "+": " plus ",
    "=": " equals ",
    "<": " less than ",
    ">": " greater than ",
    "/": " slash ",
    "\\": " slash ",
    "*": " star ",
}


def normalize_symbols(text: str) -> str:
    for symbol, word in SYMBOL_MAP.items():
        text = text.replace(symbol, word)
    return text


def speak_digits(text: str) -> str:
    return " ".join(DIGITS.get(ch, ch) for ch in text if ch.isdigit())


def normalize_phone_numbers(text: str) -> str:
    pattern = r"(\+91[\s-]?\d{5}[\s-]?\d{5})"

    def replace(match):
        number = match.group(0)
        if number.startswith("+91"):
            rest = re.sub(r"\D", "", number[3:])
            return "plus nine one, " + speak_digits(rest)

        digits = re.sub(r"\D", "", number)
        return speak_digits(digits)

    return re.sub(pattern, replace, text)


def normalize_currency(text: str) -> str:
    # Converts \u20b92499 or \u20b92,499 to "2499 rupees"
    text = re.sub(r"\u20b9\s?([\d,]+)", lambda m: m.group(1).replace(",", "") + " rupees", text)
    text = re.sub(r"Rs\.?\s?([\d,]+)", lambda m: m.group(1).replace(",", "") + " rupees", text, flags=re.IGNORECASE)
    return text


def normalize_punctuation(text: str) -> str:
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r"\?{2,}", "?", text)
    text = re.sub(r"!{2,}", "!", text)
    text = re.sub(r"\?!+|\?+!+", "?", text)
    text = re.sub(r"[,;:]{2,}", ",", text)
    return text


def reject_bad_text(text: str) -> bool:
    # Use isalpha() to count letters from ALL scripts (English, Hindi, Tamil, etc.)
    # instead of stripping non-ASCII which broke Devanagari/Tamil/Kannada
    clean = "".join(ch for ch in text if ch.isalpha())

    if len(clean) < 2:
        return True

    # Too many repeated characters like zzzzzzz
    if re.search(r"([a-zA-Z0-9])\1{5,}", text):
        return True

    # Mostly ASCII gibberish / no vowels (only applies to Latin text)
    ascii_only = "".join(ch for ch in clean if ord(ch) < 128)
    if len(ascii_only) > 8:
        vowels = sum(1 for ch in ascii_only.lower() if ch in "aeiou")
        if vowels == 0:
            return True

    return False


def clean_text_for_tts(text: str) -> str:
    text = text.strip()

    # 1. Clean repeated punctuation first
    text = normalize_punctuation(text)

    # 2. Check if meaningful after punctuation cleanup
    if reject_bad_text(text):
        raise ValueError("Please enter meaningful text for voice generation.")

    # 3. Normalize special cases
    text = normalize_currency(text)
    text = normalize_phone_numbers(text)

    # 4. Normalize general symbols
    text = normalize_symbols(text)

    # 5. Remove extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text
