# Dreamtalk - Voice Engine
# Extracted from GPT-SoVITS (MIT License)
# Source: GPT_SoVITS/text/ modules

from typing import Dict, List, Tuple
import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer

from .cleaner import clean_text
from .i18n import I18nAuto

i18n = I18nAuto()


class TextFrontend:
    def __init__(self, bert_model: AutoModelForMaskedLM, tokenizer: AutoTokenizer, device: torch.device):
        self.bert_model = bert_model
        self.tokenizer = tokenizer
        self.device = device

    def get_bert_feature(self, text: str, word2ph: list) -> torch.Tensor:
        with torch.no_grad():
            inputs = self.tokenizer(text, return_tensors="pt")
            for k in inputs:
                inputs[k] = inputs[k].to(self.device)
            res = self.bert_model(**inputs, output_hidden_states=True)
            res = torch.cat(res["hidden_states"][-3:-2], -1)[0].cpu()[1:-1]
        assert len(word2ph) == len(text)
        phone_level_feature = []
        for i in range(len(word2ph)):
            phone_level_feature.append(res[i].repeat(word2ph[i], 1))
        return torch.cat(phone_level_feature, dim=0).T

    def text_to_sequence(self, text: str, language: str, version: str = "v2"):
        phones, word2ph, norm_text = clean_text(text, language, version)
        from .__init__text import cleaned_text_to_sequence
        seq = cleaned_text_to_sequence(phones, version)
        return seq, word2ph, norm_text

    def extract_bert(self, phones, word2ph, norm_text, language: str):
        language = language.replace("all_", "")
        if language == "zh":
            return self.get_bert_feature(norm_text, word2ph).to(self.device)
        return torch.zeros((1024, len(phones)), dtype=torch.float32).to(self.device)
