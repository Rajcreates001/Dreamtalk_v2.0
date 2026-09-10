# Dreamtalk - Emotion Engine
# Migrated from Dreamtalk_Emotion_Engine

"""
Personality profile schemas: BigFive, HumanPersonality, and related dataclasses.
"""

from dataclasses import dataclass


@dataclass
class BigFiveTraits:
    extroversion: float      # 0 to 1
    agreeableness: float     # 0 to 1
    neuroticism: float       # 0 to 1
    openness: float          # 0 to 1
    conscientiousness: float # 0 to 1


@dataclass
class PersonalityProfile:
    extroversion: float
    agreeableness: float
    neuroticism: float
    openness: float
    conscientiousness: float


@dataclass
class NeuralState:
    emotional_arousal: float
    cognitive_load: float
    creativity_level: float
    response_urgency: float


@dataclass
class HumanPersonality:
    extroversion: float
    agreeableness: float
    neuroticism: float
    openness: float
    conscientiousness: float
    assertiveness: float
    sarcasm_tendency: float
    emotional_depth: float


@dataclass
class HumanNeuralState:
    emotional_arousal: float
    cognitive_load: float
    creativity_level: float
    response_urgency: float
    patience_level: float
    mood_stability: float
    social_engagement: float
