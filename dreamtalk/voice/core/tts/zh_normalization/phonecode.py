# Copyright (c) 2021 PaddlePaddle Authors. All Rights Reserved.
# Licensed under the Apache License, Version 2.0
import re
from .num import verbalize_digit

RE_MOBILE_PHONE = re.compile(r"(?<!\d)((\+?86 ?)?1([38]\d|5[0-35-9]|7[678]|9[89])\d{8})(?!\d)")
RE_TELEPHONE = re.compile(r"(?<!\d)((0(10|2[1-3]|[3-9]\d{2})-?)?[1-9]\d{6,7})(?!\d)")
RE_NATIONAL_UNIFORM_NUMBER = re.compile(r"(400)(-)?\d{3}(-)?\d{4}")

def phone2str(phone_string: str, mobile=True) -> str:
    if mobile:
        sp_parts = phone_string.strip("+").split()
        return "，".join([verbalize_digit(part, alt_one=True) for part in sp_parts])
    else:
        sil_parts = phone_string.split("-")
        return "，".join([verbalize_digit(part, alt_one=True) for part in sil_parts])

def replace_phone(match) -> str:
    return phone2str(match.group(0), mobile=False)

def replace_mobile(match) -> str:
    return phone2str(match.group(0))
