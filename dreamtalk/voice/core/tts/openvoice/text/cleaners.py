# Dreamtalk - Voice Engine
# Extracted from OpenVoice

import re


def cjke_cleaners2(text):
    text = re.sub(r'\[ZH\](.*?)\[ZH\]',
                  lambda x: chinese_to_ipa(x.group(1)) + ' ', text)
    text = re.sub(r'\[JA\](.*?)\[JA\]',
                  lambda x: japanese_to_ipa2(x.group(1)) + ' ', text)
    text = re.sub(r'\[KO\](.*?)\[KO\]',
                  lambda x: korean_to_ipa(x.group(1)) + ' ', text)
    text = re.sub(r'\[EN\](.*?)\[EN\]',
                  lambda x: english_to_ipa2(x.group(1)) + ' ', text)
    text = re.sub(r'\s+$', '', text)
    text = re.sub(r'([^\.,!\?\-…~])$', r'\1.', text)
    return text


def chinese_to_ipa(text):
    from dreamtalk.voice.core.tts.openvoice.text.mandarin import chinese_to_ipa as _chinese_to_ipa
    return _chinese_to_ipa(text)


def english_to_ipa2(text):
    from dreamtalk.voice.core.tts.openvoice.text.english import english_to_ipa2 as _english_to_ipa2
    return _english_to_ipa2(text)


def japanese_to_ipa2(text):
    return text


def korean_to_ipa(text):
    return text
