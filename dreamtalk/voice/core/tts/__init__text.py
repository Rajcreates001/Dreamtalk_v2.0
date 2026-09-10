# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: GPT_SoVITS/text/__init__.py

from . import symbols as symbols_v1
from . import symbols2 as symbols_v2

_symbol_to_id_v1 = {s: i for i, s in enumerate(symbols_v1.symbols)}
_symbol_to_id_v2 = {s: i for i, s in enumerate(symbols_v2.symbols)}


def cleaned_text_to_sequence(cleaned_text, version=None):
    if version is None:
        version = "v2"
    if version == "v1":
        phones = [_symbol_to_id_v1[symbol] for symbol in cleaned_text]
    else:
        phones = [_symbol_to_id_v2[symbol] for symbol in cleaned_text]
    return phones
