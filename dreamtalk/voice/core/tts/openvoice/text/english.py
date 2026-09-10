# Dreamtalk - Voice Engine
# Extracted from OpenVoice

import re
import inflect
from unidecode import unidecode
import eng_to_ipa as ipa

_inflect = inflect.engine()
_comma_number_re = re.compile(r'([0-9][0-9\,]+[0-9])')
_decimal_number_re = re.compile(r'([0-9]+\.[0-9]+)')
_pounds_re = re.compile(r'\u00a3([0-9\,]*[0-9]+)')
_dollars_re = re.compile(r'\$([0-9\.\,]*[0-9]+)')
_ordinal_re = re.compile(r'[0-9]+(st|nd|rd|th)')
_number_re = re.compile(r'[0-9]+')

_abbreviations = [(re.compile('\\b%s\\.' % x[0], re.IGNORECASE), x[1]) for x in [
    ('mrs', 'misess'), ('mr', 'mister'), ('dr', 'doctor'), ('st', 'saint'),
    ('co', 'company'), ('jr', 'junior'), ('maj', 'major'), ('gen', 'general'),
    ('drs', 'doctors'), ('rev', 'reverend'), ('lt', 'lieutenant'),
    ('hon', 'honorable'), ('sgt', 'sergeant'), ('capt', 'captain'),
    ('esq', 'esquire'), ('ltd', 'limited'), ('col', 'colonel'), ('ft', 'fort'),
]]

_lazy_ipa = [(re.compile('%s' % x[0]), x[1]) for x in [
    ('r', '\u0279'), ('\u00e6', 'e'), ('\u0251', 'a'), ('\u0254', 'o'),
    ('\u00f0', 'z'), ('\u03b8', 's'), ('\u025b', 'e'), ('\u026a', 'i'),
    ('\u028a', 'u'), ('\u0292', '\u0265'), ('\u02a4', '\u0265'),
    ('\u02c8', '\u2193'),
]]

_lazy_ipa2 = [(re.compile('%s' % x[0]), x[1]) for x in [
    ('r', '\u0279'), ('\u00f0', 'z'), ('\u03b8', 's'), ('\u0292', '\u0291'),
    ('\u02a4', 'd\u0291'), ('\u02c8', '\u2193'),
]]

_ipa_to_ipa2 = [(re.compile('%s' % x[0]), x[1]) for x in [
    ('r', '\u0279'), ('\u02a4', 'd\u0292'), ('\u02a7', 't\u0283'),
]]


def expand_abbreviations(text):
    for regex, replacement in _abbreviations:
        text = re.sub(regex, replacement, text)
    return text


def collapse_whitespace(text):
    return re.sub(r'\s+', ' ', text)


def _remove_commas(m):
    return m.group(1).replace(',', '')


def _expand_decimal_point(m):
    return m.group(1).replace('.', ' point ')


def _expand_dollars(m):
    match = m.group(1)
    parts = match.split('.')
    if len(parts) > 2:
        return match + ' dollars'
    dollars = int(parts[0]) if parts[0] else 0
    cents = int(parts[1]) if len(parts) > 1 and parts[1] else 0
    if dollars and cents:
        dollar_unit = 'dollar' if dollars == 1 else 'dollars'
        cent_unit = 'cent' if cents == 1 else 'cents'
        return '%s %s, %s %s' % (dollars, dollar_unit, cents, cent_unit)
    elif dollars:
        dollar_unit = 'dollar' if dollars == 1 else 'dollars'
        return '%s %s' % (dollars, dollar_unit)
    elif cents:
        cent_unit = 'cent' if cents == 1 else 'cents'
        return '%s %s' % (cents, cent_unit)
    else:
        return 'zero dollars'


def _expand_ordinal(m):
    return _inflect.number_to_words(m.group(0))


def _expand_number(m):
    num = int(m.group(0))
    if num > 1000 and num < 3000:
        if num == 2000:
            return 'two thousand'
        elif num > 2000 and num < 2010:
            return 'two thousand ' + _inflect.number_to_words(num % 100)
        elif num % 100 == 0:
            return _inflect.number_to_words(num // 100) + ' hundred'
        else:
            return _inflect.number_to_words(num, andword='', zero='oh', group=2).replace(', ', ' ')
    else:
        return _inflect.number_to_words(num, andword='')


def normalize_numbers(text):
    text = re.sub(_comma_number_re, _remove_commas, text)
    text = re.sub(_pounds_re, r'\1 pounds', text)
    text = re.sub(_dollars_re, _expand_dollars, text)
    text = re.sub(_decimal_number_re, _expand_decimal_point, text)
    text = re.sub(_ordinal_re, _expand_ordinal, text)
    text = re.sub(_number_re, _expand_number, text)
    return text


def mark_dark_l(text):
    return re.sub(r'l([^aeiou\u00e6\u0251\u0254\u0259\u025b\u026a\u028a ]*(?: |$))',
                  lambda x: '\u026b' + x.group(1), text)


def english_to_ipa(text):
    text = unidecode(text).lower()
    text = expand_abbreviations(text)
    text = normalize_numbers(text)
    phonemes = ipa.convert(text)
    phonemes = collapse_whitespace(phonemes)
    return phonemes


def english_to_lazy_ipa(text):
    text = english_to_ipa(text)
    for regex, replacement in _lazy_ipa:
        text = re.sub(regex, replacement, text)
    return text


def english_to_ipa2(text):
    text = english_to_ipa(text)
    text = mark_dark_l(text)
    for regex, replacement in _ipa_to_ipa2:
        text = re.sub(regex, replacement, text)
    return text.replace('...', '\u2026')


def english_to_lazy_ipa2(text):
    text = english_to_ipa(text)
    for regex, replacement in _lazy_ipa2:
        text = re.sub(regex, replacement, text)
    return text
