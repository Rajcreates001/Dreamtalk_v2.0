# Dreamtalk - Voice Engine
# Extracted from OpenVoice

_pad        = '_'
_punctuation = ',.!?-~…'
_letters = 'NQabdefghijklmnopstuvwxyzɑæʃʑçɯɪɔɛɹðəɫɥɸʊɾʒθβŋɦ⁼ʰ`^#*=ˈˌ→↓↑ '

symbols = [_pad] + list(_punctuation) + list(_letters)

SPACE_ID = symbols.index(" ")

num_ja_tones = 1
num_kr_tones = 1
num_zh_tones = 6
num_en_tones = 4

language_tone_start_map = {
    "ZH": 0,
    "JP": num_zh_tones,
    "EN": num_zh_tones + num_ja_tones,
    'KR': num_zh_tones + num_ja_tones + num_en_tones,
}
