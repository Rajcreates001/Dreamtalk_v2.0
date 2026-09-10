# by https://github.com/Cosmo-klara
from __future__ import print_function
import re
import inflect
import unicodedata

measurement_map = {
    "m": ["meter", "meters"], "km": ["kilometer", "kilometers"],
    "km/h": ["kilometer per hour", "kilometers per hour"],
    "ft": ["feet", "feet"], "L": ["liter", "liters"],
    "tbsp": ["tablespoon", "tablespoons"], "tsp": ["teaspoon", "teaspoons"],
    "h": ["hour", "hours"], "min": ["minute", "minutes"],
    "s": ["second", "seconds"], "°C": ["degree celsius", "degrees celsius"],
    "°F": ["degree fahrenheit", "degrees fahrenheit"],
}

_inflect = inflect.engine()
_ordinal_number_re = re.compile(r"\b([0-9]+)\. ")
_comma_number_re = re.compile(r"([0-9][0-9\,]+[0-9])")
_time_re = re.compile(r"\b([01]?[0-9]|2[0-3]):([0-5][0-9])\b")
_measurement_re = re.compile(r"\b([0-9]+(\.[0-9]+)?(m|km|km/h|ft|L|tbsp|tsp|h|min|s|°C|°F))\b")
_pounds_re_start = re.compile(r"£([0-9\.\,]*[0-9]+)")
_pounds_re_end = re.compile(r"([0-9\.\,]*[0-9]+)£")
_dollars_re_start = re.compile(r"\$([0-9\.\,]*[0-9]+)")
_dollars_re_end = re.compile(r"([(0-9\.\,]*[0-9]+)\$")
_decimal_number_re = re.compile(r"([0-9]+\.\s*[0-9]+)")
_fraction_re = re.compile(r"([0-9]+/[0-9]+)")
_ordinal_re = re.compile(r"[0-9]+(st|nd|rd|th)")
_number_re = re.compile(r"[0-9]+")

def _convert_ordinal(m):
    return _inflect.ordinal(m.group(1)) + ", "

def _remove_commas(m):
    return m.group(1).replace(",", "")

def _expand_time(m):
    hours, minutes = map(int, m.group(1, 2))
    period = "a.m." if hours < 12 else "p.m."
    if hours > 12:
        hours -= 12
    hour_word = _inflect.number_to_words(hours)
    minute_word = _inflect.number_to_words(minutes) if minutes != 0 else ""
    if minutes == 0:
        return f"{hour_word} o'clock {period}"
    return f"{hour_word} {minute_word} {period}"

def _expand_measurement(m):
    sign = m.group(3)
    ptr = 1
    num = int(m.group(1).replace(sign, "").replace(".", ""))
    decimal_part = m.group(2)
    if decimal_part is None and num == 1:
        ptr = 0
    return m.group(1).replace(sign, " " + measurement_map[sign][ptr])

def _expand_pounds(m):
    match = m.group(1)
    parts = match.split(".")
    if len(parts) > 2:
        return match + " pounds"
    pounds = int(parts[0]) if parts[0] else 0
    pence = int(parts[1].ljust(2, "0")) if len(parts) > 1 and parts[1] else 0
    if pounds and pence:
        return f"{pounds} {'pound' if pounds == 1 else 'pounds'} and {pence} {'penny' if pence == 1 else 'pence'}"
    elif pounds:
        return f"{pounds} {'pound' if pounds == 1 else 'pounds'}"
    elif pence:
        return f"{pence} {'penny' if pence == 1 else 'pence'}"
    return "zero pounds"

def _expand_dollars(m):
    match = m.group(1)
    parts = match.split(".")
    if len(parts) > 2:
        return match + " dollars"
    dollars = int(parts[0]) if parts[0] else 0
    cents = int(parts[1].ljust(2, "0")) if len(parts) > 1 and parts[1] else 0
    if dollars and cents:
        return f"{dollars} {'dollar' if dollars == 1 else 'dollars'} and {cents} {'cent' if cents == 1 else 'cents'}"
    elif dollars:
        return f"{dollars} {'dollar' if dollars == 1 else 'dollars'}"
    elif cents:
        return f"{cents} {'cent' if cents == 1 else 'cents'}"
    return "zero dollars"

def _expand_decimal_number(m):
    match = m.group(1)
    parts = match.split(".")
    words = []
    for char in parts[1]:
        if char == ".":
            words.append("point")
        else:
            words.append(char)
    return parts[0] + " point " + " ".join(words)

def _expend_fraction(m):
    match = m.group(0)
    numerator, denominator = map(int, match.split("/"))
    numerator_part = _inflect.number_to_words(numerator)
    if denominator == 2:
        denominator_part = "half" if numerator == 1 else "halves"
    elif denominator == 1:
        return f"{numerator_part}"
    else:
        denominator_part = _inflect.ordinal(_inflect.number_to_words(denominator))
        if numerator > 1:
            denominator_part += "s"
    return f"{numerator_part} {denominator_part}"

def _expand_ordinal(m):
    return _inflect.number_to_words(m.group(0))

def _expand_number(m):
    num = int(m.group(0))
    if num > 1000 and num < 3000:
        if num == 2000:
            return "two thousand"
        elif num > 2000 and num < 2010:
            return "two thousand " + _inflect.number_to_words(num % 100)
        elif num % 100 == 0:
            return _inflect.number_to_words(num // 100) + " hundred"
        else:
            return _inflect.number_to_words(num, andword="", zero="oh", group=2).replace(", ", " ")
    else:
        return _inflect.number_to_words(num, andword="")

RE_ASMD = re.compile(
    r"((-?)((\d+)(\.\d+)?[⁰¹²³⁴⁵⁶⁷⁸⁹ˣʸⁿ]*)|(\.\d+[⁰¹²³⁴⁵⁶⁷⁸⁹ˣʸⁿ]*)|([A-Za-z][⁰¹²³⁴⁵⁶⁷⁸⁹ˣʸⁿ]*))\s+([\+\-\×÷=])\s+((-?)((\d+)(\.\d+)?[⁰¹²³⁴⁵⁶⁷⁸⁹ˣʸⁿ]*)|(\.\d+[⁰¹²³⁴⁵⁶⁷⁸⁹ˣʸⁿ]*)|([A-Za-z][⁰¹²³⁴⁵⁶⁷⁸⁹ˣʸⁿ]*))"
)
asmd_map = {"+": " plus ", "-": " minus ", "×": " times ", "÷": " divided by ", "=": " Equals "}
def replace_asmd(match) -> str:
    return match.group(1) + asmd_map[match.group(8)] + match.group(9)

RE_INTEGER = re.compile(r"(?:^|\s+)(-)(\d+)")
def replace_negative_num(match) -> str:
    sign = match.group(1)
    number = match.group(2)
    return f"{'negative ' if sign else ''}{number}"

def normalize(text):
    text = re.sub(_ordinal_number_re, _convert_ordinal, text)
    while RE_ASMD.search(text):
        text = RE_ASMD.sub(replace_asmd, text)
    text = RE_INTEGER.sub(replace_negative_num, text)
    text = re.sub(_comma_number_re, _remove_commas, text)
    text = re.sub(_time_re, _expand_time, text)
    text = re.sub(_measurement_re, _expand_measurement, text)
    text = re.sub(_pounds_re_start, _expand_pounds, text)
    text = re.sub(_pounds_re_end, _expand_pounds, text)
    text = re.sub(_dollars_re_start, _expand_dollars, text)
    text = re.sub(_dollars_re_end, _expand_dollars, text)
    text = re.sub(_decimal_number_re, _expand_decimal_number, text)
    text = re.sub(_fraction_re, _expend_fraction, text)
    text = re.sub(_ordinal_re, _expand_ordinal, text)
    text = re.sub(_number_re, _expand_number, text)
    text = "".join(char for char in unicodedata.normalize("NFD", text) if unicodedata.category(char) != "Mn")
    text = re.sub("%", " percent", text)
    text = re.sub("[^ A-Za-z'.,?!\-]", "", text)
    text = re.sub(r"(?i)i\.e\.", "that is", text)
    text = re.sub(r"(?i)e\.g\.", "for example", text)
    text = re.sub(r"(?<!^)(?<![\s])([A-Z])", r" \1", text)
    return text
