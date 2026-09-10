# DreamTalk — ASR (Automatic Speech Recognition) Module
# Supports: OpenAI Whisper API, faster-whisper (local), stub fallback

from .speech_recognizer import SpeechRecognizer, get_recognizer

__all__ = ["SpeechRecognizer", "get_recognizer"]
