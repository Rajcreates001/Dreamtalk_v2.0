# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: tools/i18n/i18n.py

import json
import locale
import os


def load_language_list(language):
    i18n_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale")
    path = os.path.join(i18n_dir, f"{language}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def scan_language_list():
    i18n_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale")
    language_list = []
    if os.path.exists(i18n_dir):
        for name in os.listdir(i18n_dir):
            if name.endswith(".json"):
                language_list.append(name.split(".")[0])
    return language_list


class I18nAuto:
    def __init__(self, language=None):
        if language in ("Auto", None):
            try:
                language = locale.getdefaultlocale()[0]
            except:
                language = "en_US"
        i18n_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale")
        lang_path = os.path.join(i18n_dir, f"{language}.json")
        if not os.path.exists(lang_path):
            language = "en_US"
        self.language = language
        self.language_map = load_language_list(language)

    def __call__(self, key):
        return self.language_map.get(key, key)
