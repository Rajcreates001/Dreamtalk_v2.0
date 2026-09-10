# Dreamtalk - Voice Engine
# Extracted from OpenVoice

import re
from pypinyin import lazy_pinyin, BOPOMOFO
import jieba
import cn2an


def number_to_chinese(text):
    numbers = re.findall(r'\d+(?:\.?\d+)?', text)
    for number in numbers:
        text = text.replace(number, cn2an.an2cn(number), 1)
    return text


def chinese_to_bopomofo(text):
    text = text.replace('\u3001', '\uff0c').replace('\uff1b', '\uff0c').replace('\uff1a', '\uff0c')
    words = jieba.lcut(text, cut_all=False)
    text = ''
    for word in words:
        bopomofos = lazy_pinyin(word, BOPOMOFO)
        if not re.search('[\u4e00-\u9fff]', word):
            text += word
            continue
        for i in range(len(bopomofos)):
            bopomofos[i] = re.sub(r'([\u3105-\u3129])$', r'\1\u02c9', bopomofos[i])
        if text != '':
            text += ' '
        text += ''.join(bopomofos)
    return text


_latin_to_bopomofo = [(re.compile('%s' % x[0], re.IGNORECASE), x[1]) for x in [
    ('a', '\u311f\u02c9'), ('b', '\u3107\u310b\u02cb'), ('c', '\u3119\u3109\u02c9'),
    ('d', '\u3109\u310b\u02cb'), ('e', '\u310b\u02cb'), ('f', '\u311d\u02ca\u3114\u310b\u02cb'),
    ('g', '\u3110\u310b\u02cb'), ('h', '\u311d\u02c7\u3118\u02cb'), ('i', '\u311e\u02cb'),
    ('j', '\u310f\u311f\u02cb'), ('k', '\u310e\u311f\u02cb'), ('l', '\u311d\u02ca\u311b\u02cb'),
    ('m', '\u311d\u02ca\u3108\u310b\u02cb'), ('n', '\u3123\u02c9'), ('o', '\u3125\u02c9'),
    ('p', '\u3106\u3109\u02c9'), ('q', '\u310e\u3109\u3125\u02c9'), ('r', '\u311a\u02cb'),
    ('s', '\u311d\u02ca\u3119\u02cb'), ('t', '\u310a\u310b\u02cb'), ('u', '\u3109\u3125\u02c9'),
    ('v', '\u3127\u3109\u02c9'), ('w', '\u3109\u311a\u02cb\u3114\u3121\u310b\u02cb\u3125\u02cb'),
    ('x', '\u311d\u02c9\u3118\u310b\u02cb\u3119\u02cb'), ('y', '\u3127\u311e\u02cb'),
    ('z', '\u3119\u311f\u02cb'),
]]


def latin_to_bopomofo(text):
    for regex, replacement in _latin_to_bopomofo:
        text = re.sub(regex, replacement, text)
    return text


def chinese_to_ipa(text):
    text = number_to_chinese(text)
    text = chinese_to_bopomofo(text)
    text = latin_to_bopomofo(text)
    text = bopomofo_to_ipa(text)
    text = re.sub('i([aoe])', r'j\1', text)
    text = re.sub('u([ao\u0259e])', r'w\1', text)
    text = re.sub('([s\u0279]`[\u207a\u02b0]?)([\u2192\u2193\u2191 ]+|$)', r'\1\u0279`\2', text).replace('\u027b', '\u0279`')
    text = re.sub('([s][\u207a\u02b0]?)([\u2192\u2193\u2191 ]+|$)', r'\1\u0279\2', text)
    return text


def chinese_to_ipa2(text):
    text = number_to_chinese(text)
    text = chinese_to_bopomofo(text)
    text = latin_to_bopomofo(text)
    text = bopomofo_to_ipa2(text)
    text = re.sub(r'i([aoe])', r'j\1', text)
    text = re.sub(r'u([ao\u0259e])', r'w\1', text)
    text = re.sub(r'([\u0282\u0279]\u02b0?)([\u0329\u02a7\u02a6\u02a5\u02a4 ]+|$)', r'\1\u0285\2', text)
    text = re.sub(r'(s\u02b0?)([\u0329\u02a7\u02a6\u02a5\u02a4 ]+|$)', r'\1\u0240\2', text)
    return text


_bopomofo_to_ipa = [
    (re.compile('\u3105\u311b'), 'p\u207awo'),
    (re.compile('\u3106\u311b'), 'p\u02b0wo'),
    (re.compile('\u3107\u311b'), 'mwo'),
    (re.compile('\u3108\u311b'), 'fwo'),
    (re.compile('\u3105'), 'p\u207a'),
    (re.compile('\u3106'), 'p\u02b0'),
    (re.compile('\u3107'), 'm'),
    (re.compile('\u3108'), 'f'),
    (re.compile('\u3109'), 't\u207a'),
    (re.compile('\u310a'), 't\u02b0'),
    (re.compile('\u310b'), 'n'),
    (re.compile('\u310c'), 'l'),
    (re.compile('\u310d'), 'k\u207a'),
    (re.compile('\u310e'), 'k\u02b0'),
    (re.compile('\u310f'), 'x'),
    (re.compile('\u3110'), 't\u0283\u207a'),
    (re.compile('\u3111'), 't\u0283\u02b0'),
    (re.compile('\u3112'), '\u0283'),
    (re.compile('\u3113'), 'ts`\u207a'),
    (re.compile('\u3114'), 'ts`\u02b0'),
    (re.compile('\u3115'), 's`'),
    (re.compile('\u3116'), '\u0279`'),
    (re.compile('\u3117'), 'ts\u207a'),
    (re.compile('\u3118'), 'ts\u02b0'),
    (re.compile('\u3119'), 's'),
    (re.compile('\u311a'), 'a'),
    (re.compile('\u311b'), 'o'),
    (re.compile('\u311c'), '\u0259'),
    (re.compile('\u311d'), '\u025b'),
    (re.compile('\u311e'), 'a\u026a'),
    (re.compile('\u311f'), 'e\u026a'),
    (re.compile('\u3120'), '\u0251\u028a'),
    (re.compile('\u3121'), 'o\u028a'),
    (re.compile('\u3109\u3122'), 'j\u025bn'),
    (re.compile('\u3127\u3122'), '\u0265\u00e6n'),
    (re.compile('\u3122'), 'an'),
    (re.compile('\u3109\u3123'), 'in'),
    (re.compile('\u3127\u3123'), '\u0265n'),
    (re.compile('\u3123'), '\u0259n'),
    (re.compile('\u3124'), '\u0251\u014b'),
    (re.compile('\u3109\u3125'), 'i\u014b'),
    (re.compile('\u3128\u3125'), '\u028a\u014b'),
    (re.compile('\u3127\u3125'), 'j\u028a\u014b'),
    (re.compile('\u3125'), '\u0259\u014b'),
    (re.compile('\u3126'), '\u0259\u027b'),
    (re.compile('\u3109'), 'i'),
    (re.compile('\u3128'), 'u'),
    (re.compile('\u3127'), '\u0265'),
    (re.compile('\u02c9'), '\u2192'),
    (re.compile('\u02ca'), '\u2191'),
    (re.compile('\u02c7'), '\u2193\u2191'),
    (re.compile('\u02cb'), '\u2193'),
    (re.compile('\u02d9'), ''),
    (re.compile('\uff0c'), ','),
    (re.compile('\u3002'), '.'),
    (re.compile('\uff01'), '!'),
    (re.compile('\uff1f'), '?'),
    (re.compile('\u2014'), '-'),
]


def bopomofo_to_ipa(text):
    for regex, replacement in _bopomofo_to_ipa:
        text = re.sub(regex, replacement, text)
    return text


_bopomofo_to_ipa2 = [
    (re.compile('\u3105\u311b'), 'pwo'),
    (re.compile('\u3106\u311b'), 'p\u02b0wo'),
    (re.compile('\u3107\u311b'), 'mwo'),
    (re.compile('\u3108\u311b'), 'fwo'),
    (re.compile('\u3105'), 'p'),
    (re.compile('\u3106'), 'p\u02b0'),
    (re.compile('\u3107'), 'm'),
    (re.compile('\u3108'), 'f'),
    (re.compile('\u3109'), 't'),
    (re.compile('\u310a'), 't\u02b0'),
    (re.compile('\u310b'), 'n'),
    (re.compile('\u310c'), 'l'),
    (re.compile('\u310d'), 'k'),
    (re.compile('\u310e'), 'k\u02b0'),
    (re.compile('\u310f'), 'h'),
    (re.compile('\u3110'), 't\u0255'),
    (re.compile('\u3111'), 't\u0255\u02b0'),
    (re.compile('\u3112'), '\u0255'),
    (re.compile('\u3113'), 't\u0282'),
    (re.compile('\u3114'), 't\u0282\u02b0'),
    (re.compile('\u3115'), '\u0282'),
    (re.compile('\u3116'), '\u027b'),
    (re.compile('\u3117'), 'ts'),
    (re.compile('\u3118'), 'ts\u02b0'),
    (re.compile('\u3119'), 's'),
    (re.compile('\u311a'), 'a'),
    (re.compile('\u311b'), 'o'),
    (re.compile('\u311c'), '\u0264'),
    (re.compile('\u311d'), '\u025b'),
    (re.compile('\u311e'), 'a\u026a'),
    (re.compile('\u311f'), 'e\u026a'),
    (re.compile('\u3120'), '\u0251\u028a'),
    (re.compile('\u3121'), 'o\u028a'),
    (re.compile('\u3109\u3122'), 'j\u025bn'),
    (re.compile('\u3127\u3122'), 'y\u00e6n'),
    (re.compile('\u3122'), 'an'),
    (re.compile('\u3109\u3123'), 'in'),
    (re.compile('\u3127\u3123'), 'yn'),
    (re.compile('\u3123'), '\u0259n'),
    (re.compile('\u3124'), '\u0251\u014b'),
    (re.compile('\u3109\u3125'), 'i\u014b'),
    (re.compile('\u3128\u3125'), '\u028a\u014b'),
    (re.compile('\u3127\u3125'), 'j\u028a\u014b'),
    (re.compile('\u3125'), '\u0264\u014b'),
    (re.compile('\u3126'), '\u0259\u027b'),
    (re.compile('\u3109'), 'i'),
    (re.compile('\u3128'), 'u'),
    (re.compile('\u3127'), 'y'),
    (re.compile('\u02c9'), '\u02a5'),
    (re.compile('\u02ca'), '\u02a7\u02a5'),
    (re.compile('\u02c7'), '\u02a8\u02a9\u02a6'),
    (re.compile('\u02cb'), '\u02a5\u02a9'),
    (re.compile('\u02d9'), ''),
    (re.compile('\uff0c'), ','),
    (re.compile('\u3002'), '.'),
    (re.compile('\uff01'), '!'),
    (re.compile('\uff1f'), '?'),
    (re.compile('\u2014'), '-'),
]


def bopomofo_to_ipa2(text):
    for regex, replacement in _bopomofo_to_ipa2:
        text = re.sub(regex, replacement, text)
    return text
