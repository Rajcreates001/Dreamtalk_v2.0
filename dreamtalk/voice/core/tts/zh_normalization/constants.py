# Copyright (c) 2021 PaddlePaddle Authors. All Rights Reserved.
# Licensed under the Apache License, Version 2.0
import re
import string
from pypinyin.constants import SUPPORT_UCS4

F2H_ASCII_LETTERS = {ord(char) + 65248: ord(char) for char in string.ascii_letters}
H2F_ASCII_LETTERS = {value: key for key, value in F2H_ASCII_LETTERS.items()}
F2H_DIGITS = {ord(char) + 65248: ord(char) for char in string.digits}
H2F_DIGITS = {value: key for key, value in F2H_DIGITS.items()}
F2H_PUNCTUATIONS = {ord(char) + 65248: ord(char) for char in string.punctuation}
H2F_PUNCTUATIONS = {value: key for key, value in F2H_PUNCTUATIONS.items()}
F2H_SPACE = {"\u3000": " "}
H2F_SPACE = {" ": "\u3000"}

if SUPPORT_UCS4:
    RE_NSW = re.compile(
        r"(?:[^"
        r"\u3007\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
        r"\U00020000-\U0002A6DF\U0002A703-\U0002B73F"
        r"\U0002B740-\U0002B81D\U0002F80A-\U0002FA1F])+"
    )
else:
    RE_NSW = re.compile(
        r"(?:[^\u3007\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff])+"
    )
