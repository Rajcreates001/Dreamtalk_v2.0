# Copyright (c) 2021 PaddlePaddle Authors. All Rights Reserved.
# Licensed under the Apache License, Version 2.0
import re
from typing import List
from .char_convert import tranditional_to_simplified
from .chronology import RE_DATE, RE_DATE2, RE_TIME, RE_TIME_RANGE, replace_date, replace_date2, replace_time
from .constants import F2H_ASCII_LETTERS, F2H_DIGITS, F2H_SPACE
from .num import (
    RE_VERSION_NUM, RE_DECIMAL_NUM, RE_DEFAULT_NUM, RE_FRAC, RE_INTEGER,
    RE_NUMBER, RE_PERCENTAGE, RE_POSITIVE_QUANTIFIERS, RE_RANGE, RE_TO_RANGE,
    RE_ASMD, RE_POWER, replace_vrsion_num, replace_default_num, replace_frac,
    replace_negative_num, replace_number, replace_percentage,
    replace_positive_quantifier, replace_range, replace_to_range,
    replace_asmd, replace_power,
)
from .phonecode import RE_MOBILE_PHONE, RE_NATIONAL_UNIFORM_NUMBER, RE_TELEPHONE, replace_mobile, replace_phone
from .quantifier import RE_TEMPERATURE, replace_measure, replace_temperature

class TextNormalizer:
    def __init__(self):
        self.SENTENCE_SPLITOR = re.compile(r"([：、，；。？！,;?!][”’]?)")

    def _split(self, text: str, lang="zh") -> List[str]:
        if lang == "zh":
            text = text.replace(" ", "")
            text = re.sub(r"[——《》【】<>{}()（）#&@“”^_|\\]", "", text)
        text = self.SENTENCE_SPLITOR.sub(r"\1\n", text)
        text = text.strip()
        return [sentence.strip() for sentence in re.split(r"\n+", text)]

    def _post_replace(self, sentence: str) -> str:
        sentence = sentence.replace("/", "每")
        for src, tgt in [
            ("①", "一"), ("②", "二"), ("③", "三"), ("④", "四"), ("⑤", "五"),
            ("⑥", "六"), ("⑦", "七"), ("⑧", "八"), ("⑨", "九"), ("⑩", "十"),
            ("α", "阿尔法"), ("β", "贝塔"), ("γ", "伽玛"), ("Γ", "伽玛"),
            ("δ", "德尔塔"), ("Δ", "德尔塔"), ("ε", "艾普西龙"), ("ζ", "捷塔"),
            ("η", "依塔"), ("θ", "西塔"), ("Θ", "西塔"), ("ι", "艾欧塔"),
            ("κ", "喀帕"), ("λ", "拉姆达"), ("Λ", "拉姆达"), ("μ", "缪"),
            ("ν", "拗"), ("ξ", "克西"), ("Ξ", "克西"), ("ο", "欧米克伦"),
            ("π", "派"), ("Π", "派"), ("ρ", "肉"), ("ς", "西格玛"),
            ("Σ", "西格玛"), ("σ", "西格玛"), ("τ", "套"), ("υ", "宇普西龙"),
            ("φ", "服艾"), ("Φ", "服艾"), ("χ", "器"), ("ψ", "普赛"),
            ("Ψ", "普赛"), ("ω", "欧米伽"), ("Ω", "欧米伽"),
            ("+", "加"), ("-", "减"), ("×", "乘"), ("÷", "除"), ("=", "等"),
        ]:
            sentence = sentence.replace(src, tgt)
        sentence = re.sub(r"[-——《》【】<=>{}()（）#&@“”^_|\\]", "", sentence)
        return sentence

    def normalize_sentence(self, sentence: str) -> str:
        sentence = tranditional_to_simplified(sentence)
        sentence = sentence.translate(F2H_ASCII_LETTERS).translate(F2H_DIGITS).translate(F2H_SPACE)
        sentence = RE_DATE.sub(replace_date, sentence)
        sentence = RE_DATE2.sub(replace_date2, sentence)
        sentence = RE_TIME_RANGE.sub(replace_time, sentence)
        sentence = RE_TIME.sub(replace_time, sentence)
        sentence = RE_TO_RANGE.sub(replace_to_range, sentence)
        sentence = RE_TEMPERATURE.sub(replace_temperature, sentence)
        sentence = replace_measure(sentence)
        while RE_ASMD.search(sentence):
            sentence = RE_ASMD.sub(replace_asmd, sentence)
        sentence = RE_POWER.sub(replace_power, sentence)
        sentence = RE_FRAC.sub(replace_frac, sentence)
        sentence = RE_PERCENTAGE.sub(replace_percentage, sentence)
        sentence = RE_MOBILE_PHONE.sub(replace_mobile, sentence)
        sentence = RE_TELEPHONE.sub(replace_phone, sentence)
        sentence = RE_NATIONAL_UNIFORM_NUMBER.sub(replace_phone, sentence)
        sentence = RE_RANGE.sub(replace_range, sentence)
        sentence = RE_INTEGER.sub(replace_negative_num, sentence)
        sentence = RE_VERSION_NUM.sub(replace_vrsion_num, sentence)
        sentence = RE_DECIMAL_NUM.sub(replace_number, sentence)
        sentence = RE_POSITIVE_QUANTIFIERS.sub(replace_positive_quantifier, sentence)
        sentence = RE_DEFAULT_NUM.sub(replace_default_num, sentence)
        sentence = RE_NUMBER.sub(replace_number, sentence)
        sentence = self._post_replace(sentence)
        return sentence

    def normalize(self, text: str) -> List[str]:
        return [self.normalize_sentence(sent) for sent in self._split(text)]
