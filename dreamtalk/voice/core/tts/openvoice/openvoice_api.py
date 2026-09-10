import re
import os
import json
import torch
import numpy as np
import soundfile
import librosa
import logging
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger("dreamtalk.openvoice")

from .tone_color_clone import SynthesizerTrn
from .mel_processing import spectrogram_torch

OPENVOICE_STYLES = {
    "default": {"emotion": "neutral", "speed": 1.0, "description": "Default speaking style"},
    "happy": {"emotion": "happy", "speed": 1.1, "description": "Cheerful and bright"},
    "sad": {"emotion": "sad", "speed": 0.9, "description": "Soft and melancholic"},
    "angry": {"emotion": "angry", "speed": 1.05, "description": "Firm and assertive"},
    "surprised": {"emotion": "surprised", "speed": 1.15, "description": "Raised pitch, energetic"},
    "whisper": {"emotion": "whisper", "speed": 0.85, "description": "Breathy, quiet"},
    "authoritative": {"emotion": "neutral", "speed": 0.95, "description": "Deep, commanding tone"},
    "gentle": {"emotion": "neutral", "speed": 0.9, "description": "Soft, caring tone"},
    "excited": {"emotion": "happy", "speed": 1.2, "description": "High energy, enthusiastic"},
}

OPENVOICE_LANGUAGES = {
    "en": {"name": "English", "mark": "EN", "text_cleaners": ["english_cleaners"]},
    "zh": {"name": "Chinese", "mark": "ZH", "text_cleaners": ["chinese_cleaners"]},
    "ja": {"name": "Japanese", "mark": "JP", "text_cleaners": ["japanese_cleaners"]},
    "ko": {"name": "Korean", "mark": "KO", "text_cleaners": ["korean_cleaners"]},
    "es": {"name": "Spanish", "mark": "ES", "text_cleaners": ["spanish_cleaners"]},
    "fr": {"name": "French", "mark": "FR", "text_cleaners": ["french_cleaners"]},
}

OPENVOICE_SPEAKERS = {
    "default": 0,
    "male_1": 1,
    "female_1": 2,
    "male_2": 3,
    "female_2": 4,
}


class HParams:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if type(v) == dict:
                v = HParams(**v)
            self[k] = v

    def keys(self):
        return self.__dict__.keys()

    def items(self):
        return self.__dict__.items()

    def values(self):
        return self.__dict__.values()

    def __len__(self):
        return len(self.__dict__)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    def __contains__(self, key):
        return key in self.__dict__

    def __repr__(self):
        return self.__dict__.__repr__()


def get_hparams_from_file(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        data = f.read()
    config = json.loads(data)
    return HParams(**config)


def string_to_bits(string, pad_len=8):
    ascii_values = [ord(char) for char in string]
    binary_values = [bin(value)[2:].zfill(8) for value in ascii_values]
    bit_arrays = [[int(bit) for bit in binary] for binary in binary_values]
    numpy_array = np.array(bit_arrays)
    numpy_array_full = np.zeros((pad_len, 8), dtype=numpy_array.dtype)
    numpy_array_full[:, 2] = 1
    max_len = min(pad_len, len(numpy_array))
    numpy_array_full[:max_len] = numpy_array[:max_len]
    return numpy_array_full


def bits_to_string(bits_array):
    binary_values = [''.join(str(bit) for bit in row) for row in bits_array]
    ascii_values = [int(binary, 2) for binary in binary_values]
    output_string = ''.join(chr(value) for value in ascii_values)
    return output_string


def split_sentence(text, min_len=10, language_str='[EN]'):
    if language_str in ['EN', 'ES', 'FR']:
        sentences = split_sentences_latin(text, min_len=min_len)
    elif language_str in ['JP', 'KO', 'ZH']:
        sentences = split_sentences_east_asian(text, min_len=min_len)
    else:
        sentences = split_sentences_latin(text, min_len=min_len)
    return sentences


def split_sentences_latin(text, min_len=10):
    text = re.sub('[。！？；]', '.', text)
    text = re.sub('[，]', ',', text)
    text = re.sub('[“”]', '"', text)
    text = re.sub('[‘’]', "'", text)
    text = re.sub(r"[\<\>\(\)\[\]\"\«\»]+", "", text)
    text = re.sub('[\n\t ]+', ' ', text)
    text = re.sub('([,.!?;])', r'\1 $#!', text)
    sentences = [s.strip() for s in text.split('$#!')]
    if len(sentences[-1]) == 0:
        del sentences[-1]
    new_sentences = []
    new_sent = []
    count_len = 0
    for ind, sent in enumerate(sentences):
        new_sent.append(sent)
        count_len += len(sent.split(" "))
        if count_len > min_len or ind == len(sentences) - 1:
            count_len = 0
            new_sentences.append(' '.join(new_sent))
            new_sent = []
    return merge_short_sentences_latin(new_sentences)


def merge_short_sentences_latin(sens):
    sens_out = []
    for s in sens:
        if len(sens_out) > 0 and len(sens_out[-1].split(" ")) <= 2:
            sens_out[-1] = sens_out[-1] + " " + s
        else:
            sens_out.append(s)
    try:
        if len(sens_out[-1].split(" ")) <= 2:
            sens_out[-2] = sens_out[-2] + " " + sens_out[-1]
            sens_out.pop(-1)
    except:
        pass
    return sens_out


def split_sentences_east_asian(text, min_len=10):
    text = re.sub('[。！？；]', '.', text)
    text = re.sub('[，]', ',', text)
    text = re.sub('[\n\t ]+', ' ', text)
    text = re.sub('([,.!?;])', r'\1 $#!', text)
    sentences = [s.strip() for s in text.split('$#!')]
    if len(sentences[-1]) == 0:
        del sentences[-1]
    new_sentences = []
    new_sent = []
    count_len = 0
    for ind, sent in enumerate(sentences):
        new_sent.append(sent)
        count_len += len(sent)
        if count_len > min_len or ind == len(sentences) - 1:
            count_len = 0
            new_sentences.append(' '.join(new_sent))
            new_sent = []
    return merge_short_sentences_east_asian(new_sentences)


def merge_short_sentences_east_asian(sens):
    sens_out = []
    for s in sens:
        if len(sens_out) > 0 and len(sens_out[-1]) <= 2:
            sens_out[-1] = sens_out[-1] + " " + s
        else:
            sens_out.append(s)
    try:
        if len(sens_out[-1]) <= 2:
            sens_out[-2] = sens_out[-2] + " " + sens_out[-1]
            sens_out.pop(-1)
    except:
        pass
    return sens_out


class OpenVoiceBaseClass(object):
    def __init__(self, config_path, device='cuda:0'):
        if 'cuda' in device:
            assert torch.cuda.is_available()

        hps = get_hparams_from_file(config_path)

        model = SynthesizerTrn(
            len(getattr(hps, 'symbols', [])),
            hps.data.filter_length // 2 + 1,
            n_speakers=hps.data.n_speakers,
            **hps.model,
        ).to(device)

        model.eval()
        self.model = model
        self.hps = hps
        self.device = device

    def load_ckpt(self, ckpt_path):
        checkpoint_dict = torch.load(ckpt_path, map_location=torch.device(self.device))
        a, b = self.model.load_state_dict(checkpoint_dict['model'], strict=False)

    @staticmethod
    def audio_numpy_concat(segment_data_list, sr, speed=1.):
        audio_segments = []
        for segment_data in segment_data_list:
            audio_segments += segment_data.reshape(-1).tolist()
            audio_segments += [0] * int((sr * 0.05) / speed)
        audio_segments = np.array(audio_segments).astype(np.float32)
        return audio_segments


class BaseSpeakerTTS(OpenVoiceBaseClass):
    language_marks = {
        "english": "EN",
        "chinese": "ZH",
        "japanese": "JP",
        "korean": "KO",
        "spanish": "ES",
        "french": "FR",
    }

    @staticmethod
    def get_text(text, hps, is_symbol):
        from .text import text_to_sequence, intersperse
        text_norm = text_to_sequence(text, hps.symbols, [] if is_symbol else hps.data.text_cleaners)
        if hps.data.add_blank:
            text_norm = intersperse(text_norm, 0)
        text_norm = torch.LongTensor(text_norm)
        return text_norm

    def tts(self, text, output_path, speaker, language='English', speed=1.0):
        mark = self.language_marks.get(language.lower(), None)
        assert mark is not None, f"language {language} is not supported, supported: {list(self.language_marks.keys())}"

        texts = split_sentence(text, language_str=mark)

        audio_list = []
        for t in texts:
            t = re.sub(r'([a-z])([A-Z])', r'\1 \2', t)
            t = f'[{mark}]{t}[{mark}]'
            stn_tst = self.get_text(t, self.hps, False)
            device = self.device
            speaker_id = self.hps.speakers[speaker]
            with torch.no_grad():
                x_tst = stn_tst.unsqueeze(0).to(device)
                x_tst_lengths = torch.LongTensor([stn_tst.size(0)]).to(device)
                sid = torch.LongTensor([speaker_id]).to(device)
                audio = self.model.infer(x_tst, x_tst_lengths, sid=sid,
                                         noise_scale=0.667, noise_scale_w=0.6,
                                         length_scale=1.0 / speed)[0][0, 0].data.cpu().float().numpy()
            audio_list.append(audio)
        audio = self.audio_numpy_concat(audio_list, sr=self.hps.data.sampling_rate, speed=speed)

        if output_path is None:
            return audio
        else:
            soundfile.write(output_path, audio, self.hps.data.sampling_rate)

    def tts_with_style(self, text, output_path, speaker, language='English', style='default', speed_override=None):
        style_config = OPENVOICE_STYLES.get(style, OPENVOICE_STYLES["default"])
        speed = speed_override or style_config["speed"]
        return self.tts(text, output_path, speaker, language, speed)


class ToneColorConverter(OpenVoiceBaseClass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if kwargs.get('enable_watermark', True):
            try:
                import wavmark
                self.watermark_model = wavmark.load_model().to(self.device)
            except ImportError:
                logger.warning("wavmark not installed, watermark disabled")
                self.watermark_model = None
        else:
            self.watermark_model = None
        self.version = getattr(self.hps, '_version_', "v1")

    def extract_se(self, ref_wav_list, se_save_path=None):
        if isinstance(ref_wav_list, str):
            ref_wav_list = [ref_wav_list]

        device = self.device
        hps = self.hps
        gs = []

        for fname in ref_wav_list:
            audio_ref, sr = librosa.load(fname, sr=hps.data.sampling_rate)
            y = torch.FloatTensor(audio_ref)
            y = y.to(device)
            y = y.unsqueeze(0)
            y = spectrogram_torch(y, hps.data.filter_length,
                                  hps.data.sampling_rate, hps.data.hop_length,
                                  hps.data.win_length, center=False).to(device)
            with torch.no_grad():
                g = self.model.ref_enc(y.transpose(1, 2)).unsqueeze(-1)
                gs.append(g.detach())
        gs = torch.stack(gs).mean(0)

        if se_save_path is not None:
            os.makedirs(os.path.dirname(se_save_path), exist_ok=True)
            torch.save(gs.cpu(), se_save_path)

        return gs

    def convert(self, audio_src_path, src_se, tgt_se, output_path=None, tau=0.3, message="default"):
        hps = self.hps
        audio, sample_rate = librosa.load(audio_src_path, sr=hps.data.sampling_rate)
        audio = torch.tensor(audio).float()

        with torch.no_grad():
            y = torch.FloatTensor(audio).to(self.device)
            y = y.unsqueeze(0)
            spec = spectrogram_torch(y, hps.data.filter_length,
                                     hps.data.sampling_rate, hps.data.hop_length,
                                     hps.data.win_length, center=False).to(self.device)
            spec_lengths = torch.LongTensor([spec.size(-1)]).to(self.device)
            audio = self.model.voice_conversion(spec, spec_lengths,
                                                sid_src=src_se, sid_tgt=tgt_se,
                                                tau=tau)[0][0, 0].data.cpu().float().numpy()
            audio = self.add_watermark(audio, message)
            if output_path is None:
                return audio
            else:
                soundfile.write(output_path, audio, hps.data.sampling_rate)

    def add_watermark(self, audio, message):
        if self.watermark_model is None:
            return audio
        device = self.device
        bits = string_to_bits(message).reshape(-1)
        n_repeat = len(bits) // 32

        K = 16000
        coeff = 2
        for n in range(n_repeat):
            trunck = audio[(coeff * n) * K: (coeff * n + 1) * K]
            if len(trunck) != K:
                break
            message_npy = bits[n * 32: (n + 1) * 32]
            with torch.no_grad():
                signal = torch.FloatTensor(trunck).to(device)[None]
                message_tensor = torch.FloatTensor(message_npy).to(device)[None]
                signal_wmd_tensor = self.watermark_model.encode(signal, message_tensor)
                signal_wmd_npy = signal_wmd_tensor.detach().cpu().squeeze()
            audio[(coeff * n) * K: (coeff * n + 1) * K] = signal_wmd_npy
        return audio

    def detect_watermark(self, audio, n_repeat):
        bits = []
        K = 16000
        coeff = 2
        for n in range(n_repeat):
            trunck = audio[(coeff * n) * K: (coeff * n + 1) * K]
            if len(trunck) != K:
                return 'Fail'
            with torch.no_grad():
                signal = torch.FloatTensor(trunck).to(self.device).unsqueeze(0)
                message_decoded_npy = (self.watermark_model.decode(signal) >= 0.5).int().detach().cpu().numpy().squeeze()
            bits.append(message_decoded_npy)
        bits = np.stack(bits).reshape(-1, 8)
        message = bits_to_string(bits)
        return message


class OpenVoiceAPI:
    def __init__(self, config_path: str, ckpt_path: str, device: str = "cuda:0"):
        self.base_tts = BaseSpeakerTTS(config_path, device)
        self.base_tts.load_ckpt(ckpt_path)
        self.tone_converter = None
        self.device = device

    def init_tone_converter(self, config_path: str, ckpt_path: str):
        self.tone_converter = ToneColorConverter(config_path, device=self.device)
        self.tone_converter.load_ckpt(ckpt_path)

    def synthesize(self, text: str, speaker: str = "default", language: str = "English",
                   style: str = "default", output_path: Optional[str] = None) -> np.ndarray:
        return self.base_tts.tts_with_style(text, output_path, speaker, language, style)

    def clone_voice(self, source_audio: str, target_ref_audio: str, output_path: str,
                    tau: float = 0.3, message: str = "dreamtalk"):
        if self.tone_converter is None:
            raise RuntimeError("Tone color converter not initialized. Call init_tone_converter() first.")
        src_se = self.tone_converter.extract_se(source_audio)
        tgt_se = self.tone_converter.extract_se(target_ref_audio)
        return self.tone_converter.convert(source_audio, src_se, tgt_se, output_path, tau, message)
