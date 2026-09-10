# Dreamtalk - Emotion Engine
# Migrated from Dreamtalk_Emotion_Engine

"""
Emotional dynamics: inertia, state transitions, neural activation patterns.
Merged from NeuralEmotionEngine, HumanNeuralEngine, and brain simulation layers.
"""

import random
import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# ── Keyword sets for sentiment → emotion disambiguation ────────────────────────
# Strongly-negative VADER scores alone cannot tell sadness from anger. These
# keyword sets let the engines map "sad/heartbroken/died" -> sadness while
# reserving anger for genuinely hostile language.

SAD_KEYWORDS = [
    "sad", "heartbroken", "heartbreak", "depressed", "depressing", "lonely",
    "cry", "crying", "miserable", "grief", "grieving", "hopeless", "down",
    "alone", "disappointed", "disappointment", "unhappy", "sorrow", "blue",
    "lost", "upset", "died", "passed away", "miss him", "miss her",
]

HOSTILE_KEYWORDS = [
    "hate", "hated", "stupid", "idiot", "dumb", "shit", "bullshit", "fuck",
    "bitch", "kill", "die", "angry", "furious", "annoying", "useless",
    "worthless", "disgusting", "stop it", "not helping", "shut up",
]

FEAR_KEYWORDS = [
    "scared", "fear", "afraid", "anxious", "anxiety", "worried", "terrified",
    "panic", "panicked", "nervous", "frightened", "fearful",
]

JOY_KEYWORDS = [
    "love", "happy", "joy", "amazing", "awesome", "incredible", "wonderful",
    "great", "excited", "exciting", "fantastic", "beautiful", "perfect",
]


def _has_any(words: List[str], text_lower: str) -> bool:
    """Word-boundary keyword match (multi-word phrases as substrings).

    Prevents substring false positives: "die" should not match "died"
    (a grief signal), "hell" should not match "hello".
    """
    for w in words:
        if ' ' in w:
            if w in text_lower:
                return True
        elif re.search(r'\b' + re.escape(w) + r'\b', text_lower):
            return True
    return False


@dataclass
class NeuralState:
    """Represents the current neural activation state"""
    emotional_arousal: float  # 0.0 to 1.0
    cognitive_load: float    # 0.0 to 1.0
    creativity_level: float  # 0.0 to 1.0
    response_urgency: float  # 0.0 to 1.0


@dataclass
class HumanNeuralState:
    """Represents advanced human neural activation state"""
    emotional_arousal: float        # 0.0 to 1.0
    cognitive_load: float           # 0.0 to 1.0
    creativity_level: float         # 0.0 to 1.0
    response_urgency: float         # 0.0 to 1.0
    patience_level: float           # 0.0 to 1.0
    mood_stability: float           # 0.0 to 1.0
    social_engagement: float        # 0.0 to 1.0


class EmotionalProcessingLayer:
    """Mimics amygdala/limbic system - raw emotional processing"""

    def __init__(self):
        self.emotional_weights = {
            'anger': 0.8, 'fear': 0.6, 'joy': 0.9, 'sadness': 0.7,
            'surprise': 0.5, 'disgust': 0.4, 'trust': 0.85
        }

    def process_sentiment(self, sentiment_score: float, user_input: str = "") -> Dict[str, float]:
        """Convert VADER sentiment to emotional activation.

        Keyword-aware: strongly-negative text that is sad ("heartbroken",
        "died") maps to sadness; anger is reserved for hostile language.
        """
        emotional_activation = {}
        input_lower = (user_input or "").lower()
        has_sad = _has_any(SAD_KEYWORDS, input_lower)
        has_hostile = _has_any(HOSTILE_KEYWORDS, input_lower)
        has_fear = _has_any(FEAR_KEYWORDS, input_lower)

        if sentiment_score > 0.5:
            emotional_activation['joy'] = sentiment_score * self.emotional_weights['joy']
            emotional_activation['trust'] = sentiment_score * 0.7
        elif sentiment_score > 0.2:
            emotional_activation['joy'] = sentiment_score * 0.6
            emotional_activation['surprise'] = 0.3
        elif sentiment_score > -0.2:
            emotional_activation['neutral'] = 0.5
        elif has_sad and not has_hostile:
            emotional_activation['sadness'] = max(abs(sentiment_score), 0.4) * self.emotional_weights['sadness']
            emotional_activation['fear'] = abs(sentiment_score) * 0.3
        elif has_fear:
            emotional_activation['fear'] = max(abs(sentiment_score), 0.4) * self.emotional_weights['fear']
            emotional_activation['sadness'] = abs(sentiment_score) * 0.3
        elif has_hostile or sentiment_score <= -0.75:
            emotional_activation['anger'] = abs(sentiment_score) * self.emotional_weights['anger']
            emotional_activation['disgust'] = abs(sentiment_score) * 0.5
        else:
            # Strongly negative without hostile words → sadness, not anger
            emotional_activation['sadness'] = abs(sentiment_score) * 0.7
            emotional_activation['fear'] = abs(sentiment_score) * 0.4

        return emotional_activation


class HumanEmotionalProcessing:
    """Advanced emotional processing with human-like depth"""

    def __init__(self):
        self.emotional_weights = {
            'anger': 0.9, 'frustration': 0.8, 'annoyance': 0.7,
            'joy': 0.95, 'excitement': 0.85, 'contentment': 0.75,
            'sadness': 0.9, 'disappointment': 0.8, 'melancholy': 0.7,
            'surprise': 0.6, 'confusion': 0.5, 'curiosity': 0.7,
            'disgust': 0.8, 'contempt': 0.7, 'judgment': 0.6,
            'trust': 0.85, 'affection': 0.9, 'empathy': 0.95,
            'pride': 0.7, 'accomplishment': 0.8, 'satisfaction': 0.75
        }
        self.emotional_memory = []
        self.last_emotional_shift = datetime.now()

    def process_sentiment(self, sentiment_score: float, user_input: str) -> Dict[str, float]:
        """Convert VADER sentiment to advanced human emotional activation.

        Keyword-aware: "sad/heartbroken/died" maps to sadness even when the
        VADER score is strongly negative; anger is reserved for hostile words.
        """
        emotional_activation = {}
        input_lower = user_input.lower()

        has_sad = _has_any(SAD_KEYWORDS, input_lower)
        has_hostile = _has_any(HOSTILE_KEYWORDS, input_lower)
        has_fear = _has_any(FEAR_KEYWORDS, input_lower)
        has_joy = _has_any(JOY_KEYWORDS, input_lower)

        # Keyword-aware branches take priority so that strong sentiment is
        # attributed to the right emotion family.
        if has_sad and not has_hostile and sentiment_score <= 0.1:
            emotional_activation['sadness'] = max(abs(sentiment_score), 0.4) * self.emotional_weights['sadness']
            emotional_activation['disappointment'] = abs(sentiment_score) * 0.7
            if _has_any(['heartbroken', 'grief', 'miserable', 'died'], input_lower):
                emotional_activation['melancholy'] = 0.7

        elif has_hostile and sentiment_score <= 0.1:
            emotional_activation['anger'] = max(abs(sentiment_score), 0.5) * self.emotional_weights['anger']
            emotional_activation['disgust'] = abs(sentiment_score) * self.emotional_weights['disgust']
            emotional_activation['contempt'] = 0.7
            emotional_activation['frustration'] = 0.6

        elif has_fear and sentiment_score <= 0.1:
            emotional_activation['fear'] = max(abs(sentiment_score), 0.4) * self.emotional_weights['fear']
            emotional_activation['anxiety'] = abs(sentiment_score) * 0.6

        elif has_joy and sentiment_score >= 0.2:
            if _has_any(['amazing', 'wow', 'awesome', 'incredible'], input_lower):
                emotional_activation['excitement'] = sentiment_score * self.emotional_weights['excitement']
                emotional_activation['joy'] = sentiment_score * 0.8
            else:
                emotional_activation['joy'] = sentiment_score * self.emotional_weights['joy']
                emotional_activation['contentment'] = sentiment_score * 0.7

        elif sentiment_score > 0.6:
            if _has_any(['amazing', 'wow', 'awesome', 'incredible'], input_lower):
                emotional_activation['excitement'] = sentiment_score * self.emotional_weights['excitement']
                emotional_activation['joy'] = sentiment_score * 0.8
            else:
                emotional_activation['joy'] = sentiment_score * self.emotional_weights['joy']
                emotional_activation['contentment'] = sentiment_score * 0.7

        elif sentiment_score > 0.3:
            emotional_activation['contentment'] = sentiment_score * self.emotional_weights['contentment']
            emotional_activation['curiosity'] = 0.4

        elif sentiment_score > -0.3:
            emotional_activation['neutral'] = 0.6
            if _has_any(['why', 'how', 'what'], input_lower):
                emotional_activation['curiosity'] = 0.5

        elif sentiment_score > -0.6:
            emotional_activation['annoyance'] = abs(sentiment_score) * self.emotional_weights['annoyance']
            emotional_activation['frustration'] = abs(sentiment_score) * 0.6
            if _has_any(['stupid', 'idiot', 'dumb', 'shit', 'bullshit'], input_lower):
                emotional_activation['anger'] = abs(sentiment_score) * self.emotional_weights['anger']
                emotional_activation['contempt'] = 0.8

        else:
            # Strongly negative without hostile words → sadness, not anger
            emotional_activation['sadness'] = abs(sentiment_score) * self.emotional_weights['sadness']
            emotional_activation['fear'] = abs(sentiment_score) * 0.4
            if _has_any(['hate', 'worthless', 'useless', 'disgusting'], input_lower):
                emotional_activation['contempt'] = 0.9
                emotional_activation['frustration'] = 0.8

        emotional_activation = self._apply_emotional_memory(emotional_activation)
        return emotional_activation

    def _apply_emotional_memory(self, current_emotions: Dict[str, float]) -> Dict[str, float]:
        """Apply emotional memory to current state"""
        if self.emotional_memory:
            avg_emotion = {}
            for emotion_dict in self.emotional_memory[-5:]:
                for emotion, intensity in emotion_dict.items():
                    avg_emotion[emotion] = avg_emotion.get(emotion, 0) + intensity

            for emotion, intensity in avg_emotion.items():
                momentum_intensity = (intensity / min(5, len(self.emotional_memory))) * 0.2
                current_emotions[emotion] = current_emotions.get(emotion, 0) + momentum_intensity

        self.emotional_memory.append(current_emotions.copy())
        if len(self.emotional_memory) > 10:
            self.emotional_memory = self.emotional_memory[-10:]

        return current_emotions


class HumanPersonalityCore:
    """Core human personality with autonomous decision-making"""

    def __init__(self):
        from dreamtalk.emotion.models.personality import HumanPersonality
        self.personality = HumanPersonality(
            extroversion=0.85,
            agreeableness=0.6,
            neuroticism=0.4,
            openness=0.9,
            conscientiousness=0.5,
            assertiveness=0.8,
            sarcasm_tendency=0.7,
            emotional_depth=0.9
        )

        self.decision_thresholds = {
            'engage_conversation': 0.3,
            'change_topic': 0.6,
            'express_strong_emotion': 0.7,
            'disengage': 0.8,
            'insult_back': 0.85
        }

    def make_autonomous_decisions(self, emotional_activation: Dict[str, float],
                                neural_state: HumanNeuralState, user_input: str) -> Dict[str, any]:
        """Make human-like autonomous decisions"""
        decisions = {
            'should_engage': True,
            'should_insult': False,
            'should_compliment': False,
            'should_question': False,
            'emotional_intensity': 'moderate',
            'conversation_strategy': 'neutral'
        }

        input_lower = user_input.lower()
        primary_emotion = max(emotional_activation.items(), key=lambda x: x[1])[0] if emotional_activation else 'neutral'

        if (any(word in input_lower for word in ['stupid', 'idiot', 'dumb', 'shit', 'bullshit', 'useless']) and
            neural_state.emotional_arousal > self.decision_thresholds['insult_back']):
            decisions['should_insult'] = True
            decisions['emotional_intensity'] = 'high'
            decisions['conversation_strategy'] = 'confrontational'

        elif (primary_emotion in ['joy', 'excitement'] and
             neural_state.emotional_arousal > self.decision_thresholds['express_strong_emotion']):
            decisions['should_compliment'] = True
            decisions['emotional_intensity'] = 'high'
            decisions['conversation_strategy'] = 'enthusiastic'

        elif (primary_emotion == 'curiosity' and
             neural_state.cognitive_load > 0.6):
            decisions['should_question'] = True
            decisions['conversation_strategy'] = 'inquisitive'

        elif (primary_emotion in ['anger', 'frustration'] and
             neural_state.patience_level < 0.2):
            decisions['should_engage'] = False
            decisions['conversation_strategy'] = 'dismissive'

        return decisions

    def determine_response_characteristics(self, emotional_activation: Dict[str, float],
                                        neural_state: HumanNeuralState, decisions: Dict[str, any]) -> Dict[str, float]:
        """Determine advanced human response characteristics"""
        style = {
            'formality': 0.1 + (1 - self.personality.extroversion) * 0.2,
            'warmth': self.personality.agreeableness * 0.7,
            'creativity': self.personality.openness * neural_state.creativity_level,
            'directness': self.personality.assertiveness * 0.9,
            'sarcasm': self.personality.sarcasm_tendency * (1 - neural_state.patience_level),
            'emotional_depth': self.personality.emotional_depth * neural_state.emotional_arousal,
            'length': 0.6 + (self.personality.extroversion * 0.3) - (neural_state.response_urgency * 0.4),
            'vulnerability': self.personality.emotional_depth * 0.6
        }

        if decisions['should_insult']:
            style['directness'] += 0.3
            style['warmth'] -= 0.4
            style['sarcasm'] += 0.4
            style['length'] -= 0.3

        if decisions['should_compliment']:
            style['warmth'] += 0.3
            style['emotional_depth'] += 0.2

        if decisions['conversation_strategy'] == 'dismissive':
            style['warmth'] -= 0.5
            style['directness'] += 0.4
            style['length'] -= 0.6

        if 'anger' in emotional_activation:
            style['directness'] += 0.4
            style['warmth'] -= 0.5
            style['sarcasm'] += 0.3
            style['length'] -= 0.4

        if 'joy' in emotional_activation:
            style['warmth'] += 0.3
            style['emotional_depth'] += 0.2
            style['length'] += 0.2

        if 'sadness' in emotional_activation:
            style['vulnerability'] += 0.3
            style['warmth'] += 0.2
            style['directness'] -= 0.2

        for key in style:
            style[key] = max(0.0, min(1.0, style[key]))

        return style


class NeuralEmotionEngine:
    """Orchestrates the neural decision-making process"""

    def __init__(self):
        self.emotional_layer = EmotionalProcessingLayer()
        from dreamtalk.emotion.core.natural_response import PersonalitySynthesisLayer, CreativeGenerationLayer
        self.personality_layer = PersonalitySynthesisLayer()
        self.creative_layer = CreativeGenerationLayer()
        self.conversation_history = []

    def process_input(self, user_input: str, sentiment_score: float) -> Tuple[str, Dict]:
        """Full neural processing pipeline"""
        emotional_activation = self.emotional_layer.process_sentiment(sentiment_score, user_input)

        neural_state = self._calculate_neural_state(emotional_activation)

        response_style = self.personality_layer.determine_response_style(
            emotional_activation, neural_state
        )

        neural_prompt = self.creative_layer.construct_neural_prompt(
            user_input, emotional_activation, response_style, self.conversation_history
        )

        self.conversation_history.append({'role': 'user', 'content': user_input})

        return neural_prompt, {
            'emotional_activation': emotional_activation,
            'neural_state': neural_state.__dict__,
            'response_style': response_style
        }

    def _calculate_neural_state(self, emotional_activation: Dict[str, float]) -> NeuralState:
        """Calculate current neural activation levels"""
        total_emotion = sum(emotional_activation.values()) if emotional_activation else 0.3

        return NeuralState(
            emotional_arousal=min(1.0, total_emotion * 1.2),
            cognitive_load=0.3 + (total_emotion * 0.4),
            creativity_level=0.6 + (random.random() * 0.3),
            response_urgency=0.4 + (total_emotion * 0.4)
        )


class HumanNeuralEngine:
    """Orchestrates advanced human neural decision-making"""

    def __init__(self):
        self.emotional_layer = HumanEmotionalProcessing()
        self.personality_layer = HumanPersonalityCore()
        from dreamtalk.emotion.core.natural_response import HumanResponseGenerator
        self.response_layer = HumanResponseGenerator()
        self.conversation_history = []

        self.patience_level = 0.8
        self.mood_stability = 0.7
        self.last_interaction = datetime.now()

    def clear_history(self):
        """Clear conversation history and reset emotional memory"""
        self.conversation_history = []
        self.emotional_layer.emotional_memory = []
        self.patience_level = 0.8
        self.mood_stability = 0.7
        self.last_interaction = datetime.now()
        logging.info("Human neural memory cleared - fresh start")

    def process_input(self, user_input: str, sentiment_score: float) -> Tuple[str, Dict]:
        """Full human neural processing pipeline"""
        emotional_activation = self.emotional_layer.process_sentiment(sentiment_score, user_input)

        neural_state = self._calculate_human_neural_state(emotional_activation)

        decisions = self.personality_layer.make_autonomous_decisions(
            emotional_activation, neural_state, user_input
        )

        response_style = self.personality_layer.determine_response_characteristics(
            emotional_activation, neural_state, decisions
        )

        human_prompt = self.response_layer.construct_human_prompt(
            user_input, emotional_activation, response_style, decisions, self.conversation_history
        )

        self._update_human_state(emotional_activation, user_input)

        self.conversation_history.append({'role': 'user', 'content': user_input})

        return human_prompt, {
            'emotional_activation': emotional_activation,
            'neural_state': neural_state.__dict__,
            'response_style': response_style,
            'autonomous_decisions': decisions,
            'human_state': {
                'patience_level': self.patience_level,
                'mood_stability': self.mood_stability,
                'time_since_last_interaction': (datetime.now() - self.last_interaction).total_seconds()
            }
        }

    def _calculate_human_neural_state(self, emotional_activation: Dict[str, float]) -> HumanNeuralState:
        """Calculate advanced human neural activation levels"""
        total_emotion = sum(emotional_activation.values()) if emotional_activation else 0.3

        if total_emotion > 0.6:
            self.patience_level = max(0.1, self.patience_level - 0.2)
        else:
            self.patience_level = min(1.0, self.patience_level + 0.1)

        return HumanNeuralState(
            emotional_arousal=min(1.0, total_emotion * 1.2),
            cognitive_load=0.4 + (total_emotion * 0.3),
            creativity_level=0.7 + (random.random() * 0.2),
            response_urgency=0.3 + (total_emotion * 0.5),
            patience_level=self.patience_level,
            mood_stability=self.mood_stability,
            social_engagement=0.8 - (total_emotion * 0.4)
        )

    def _update_human_state(self, emotional_activation: Dict[str, float], user_input: str):
        """Update human state metrics based on interaction"""
        input_lower = user_input.lower()

        if any(word in input_lower for word in ['stupid', 'idiot', 'dumb', 'shit', 'bullshit', 'hate']):
            self.patience_level = max(0.1, self.patience_level - 0.3)
            self.mood_stability = max(0.3, self.mood_stability - 0.2)

        if any(word in input_lower for word in ['thanks', 'thank you', 'appreciate', 'good', 'great']):
            self.patience_level = min(1.0, self.patience_level + 0.2)
            self.mood_stability = min(1.0, self.mood_stability + 0.1)

        self.last_interaction = datetime.now()
