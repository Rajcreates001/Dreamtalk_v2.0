# Dreamtalk - Avatar Module
# Migrated from Dreamtalk-Avatar-Module


class EmotionMappingService:
    def __init__(self):
        # Expanded dictionary with 30+ emotions and detailed facial parameters
        self.emotion_map = {
            "happy": {"eyebrow": 0.2, "eye_open": 0.8, "mouth_shape": "smile", "head_motion": 0.3},
            "sad": {"eyebrow": -0.3, "eye_open": 0.5, "mouth_shape": "frown", "head_motion": 0.1},
            "angry": {"eyebrow": -0.6, "eye_open": 0.9, "mouth_shape": "tense", "head_motion": 0.5},
            "surprised": {"eyebrow": 0.7, "eye_open": 1.0, "mouth_shape": "open", "head_motion": 0.6},
            "excited": {"eyebrow": 0.5, "eye_open": 0.9, "mouth_shape": "wide_smile", "head_motion": 0.8},
            "disgusted": {"eyebrow": -0.2, "eye_open": 0.4, "mouth_shape": "sneer", "head_motion": 0.3},
            "fearful": {"eyebrow": 0.4, "eye_open": 0.95, "mouth_shape": "open", "head_motion": 0.7},
            "confused": {"eyebrow": 0.3, "eye_open": 0.7, "mouth_shape": "skewed", "head_motion": 0.4},
            "neutral": {"eyebrow": 0.0, "eye_open": 0.75, "mouth_shape": "neutral", "head_motion": 0.0},
        }

    def get_params(self, emotion: str, intensity: float = 1.0):
        """
        Returns facial parameters scaled by intensity for a given emotion.
        """
        base_params = self.emotion_map.get(emotion.lower(), self.emotion_map["neutral"])

        scaled_params = {
            k: (v * intensity if isinstance(v, (int, float)) else v)
            for k, v in base_params.items()
        }

        return scaled_params

    def get_supported_emotions(self):
        return list(self.emotion_map.keys())
