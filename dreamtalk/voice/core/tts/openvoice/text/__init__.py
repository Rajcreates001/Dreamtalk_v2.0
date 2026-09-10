# Dreamtalk - Voice Engine
# Extracted from OpenVoice

from dreamtalk.voice.core.tts.openvoice.text import cleaners
from dreamtalk.voice.core.tts.openvoice.text.symbols import symbols, language_tone_start_map


def text_to_sequence(text, symbols, cleaner_names):
    sequence = []
    symbol_to_id = {s: i for i, s in enumerate(symbols)}
    clean_text = _clean_text(text, cleaner_names)
    for symbol in clean_text:
        if symbol not in symbol_to_id.keys():
            continue
        symbol_id = symbol_to_id[symbol]
        sequence += [symbol_id]
    return sequence


def cleaned_text_to_sequence(cleaned_text, symbols):
    symbol_to_id = {s: i for i, s in enumerate(symbols)}
    sequence = [symbol_to_id[symbol] for symbol in cleaned_text if symbol in symbol_to_id.keys()]
    return sequence


def cleaned_text_to_sequence_vits2(cleaned_text, tones, language, symbols, languages):
    symbol_to_id = {s: i for i, s in enumerate(symbols)}
    language_id_map = {s: i for i, s in enumerate(languages)}
    phones = [symbol_to_id[symbol] for symbol in cleaned_text]
    tone_start = language_tone_start_map[language]
    tones = [i + tone_start for i in tones]
    lang_id = language_id_map[language]
    lang_ids = [lang_id for i in phones]
    return phones, tones, lang_ids


def intersperse(lst, item):
    result = [item] * (len(lst) * 2 + 1)
    result[1::2] = lst
    return result


def sequence_to_text(sequence):
    result = ''
    _id_to_symbol = {i: s for i, s in enumerate(symbols)}
    for symbol_id in sequence:
        s = _id_to_symbol[symbol_id]
        result += s
    return result


def _clean_text(text, cleaner_names):
    for name in cleaner_names:
        cleaner = getattr(cleaners, name)
        if not cleaner:
            raise Exception('Unknown cleaner: %s' % name)
        text = cleaner(text)
    return text
