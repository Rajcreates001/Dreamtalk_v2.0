# Dreamtalk - Emotion Engine
# Migrated from Dreamtalk_Emotion_Engine

"""
Response generation: emotion vs logic weighting, personality-driven prompting,
LLM interfaces, and prompt compilation.
Merged from PersonalitySynthesisLayer, CreativeGenerationLayer, HumanResponseGenerator,
PromptCompiler, LLMService, NeuralLLMInterface, HTTPLLMInterface, and DreamtalkBridge.
"""

import random
import logging
import ollama
import asyncio
import requests
import json
import os
import math
from typing import List, Dict, Generator, Optional, AsyncGenerator, Tuple
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


@dataclass
class PersonalityProfile:
    """Core personality traits that influence response style"""
    extroversion: float      # 0.0 to 1.0 (talkative vs reserved)
    agreeableness: float     # 0.0 to 1.0 (cooperative vs antagonistic)
    neuroticism: float       # 0.0 to 1.0 (emotional stability)
    openness: float          # 0.0 to 1.0 (creative vs conventional)
    conscientiousness: float # 0.0 to 1.0 (organized vs spontaneous)


class PersonalitySynthesisLayer:
    """Mimics prefrontal cortex - personality and decision making"""

    def __init__(self):
        self.profile = PersonalityProfile(
            extroversion=0.8,
            agreeableness=0.6,
            neuroticism=0.4,
            openness=0.9,
            conscientiousness=0.5
        )

    def determine_response_style(self, emotional_activation: Dict[str, float],
                                neural_state: 'NeuralState') -> Dict[str, float]:
        """Decide response characteristics based on personality and emotion"""
        from dreamtalk.emotion.core.affect_dynamics import NeuralState

        style = {
            'formality': 0.2 + (1 - self.profile.extroversion) * 0.3,
            'warmth': self.profile.agreeableness * 0.8,
            'creativity': self.profile.openness * neural_state.creativity_level,
            'directness': 0.7 - (self.profile.agreeableness * 0.4),
            'length': 0.5 + (self.profile.extroversion * 0.3) - (neural_state.response_urgency * 0.4)
        }

        if 'anger' in emotional_activation:
            style['directness'] += 0.3
            style['warmth'] -= 0.4
            style['length'] -= 0.3

        if 'joy' in emotional_activation:
            style['warmth'] += 0.2
            style['creativity'] += 0.2

        return style


class CreativeGenerationLayer:
    """Mimics neocortex/temporal lobe - organic response construction"""

    def __init__(self):
        self.linguistic_patterns = {
            'casual': ['hey', 'yo', 'lol', 'haha', 'tbh', 'fr', 'ngl'],
            'formal': ['certainly', 'however', 'furthermore', 'additionally'],
            'emphatic': ['absolutely', 'definitely', 'seriously', 'for real'],
            'hedging': ['maybe', 'perhaps', 'sort of', 'kind of', 'a bit']
        }

    def construct_neural_prompt(self, user_input: str, emotional_activation: Dict[str, float],
                              response_style: Dict[str, float], context: List[Dict]) -> str:
        """Create organic prompt that guides but doesn't template the response"""
        primary_emotion = max(emotional_activation.items(), key=lambda x: x[1])[0] if emotional_activation else 'neutral'

        prompt_parts = [
            "You are DreamTalk, a real human-like conversational partner.",
            "Generate completely organic, spontaneous responses — NO TEMPLATES.",
            "Your responses should feel like natural human conversation.",
            f"Current emotional vibe: Feeling {primary_emotion} (intensity: {max(emotional_activation.values()) if emotional_activation else 0.3:.1f})",
            f'Conversational style: {"warm and engaging" if response_style["warmth"] > 0.6 else "direct and straightforward"}',
            "Response should be: " + self._get_length_descriptor(response_style['length']),
            "",
            "Recent conversation:"
        ]

        for turn in context[-3:]:
            prompt_parts.append(f"{turn['role']}: {turn['content']}")

        prompt_parts.extend([
            "",
            f"User: {user_input}",
            "DreamTalk: [Generate completely organic response that matches the emotional vibe and style above]"
        ])

        return "\n".join(prompt_parts)

    def _get_length_descriptor(self, length_score: float) -> str:
        if length_score > 0.8:
            return "detailed and expressive (2-3 sentences)"
        elif length_score > 0.6:
            return "thoughtful response (1-2 sentences)"
        elif length_score > 0.4:
            return "concise but complete (1 sentence)"
        else:
            return "very brief and direct (few words)"


class HumanResponseGenerator:
    """Generates truly human-like responses with emotional depth"""

    def __init__(self):
        self.human_linguistic_patterns = {
            'casual': ['hey', 'yo', 'lol', 'haha', 'tbh', 'fr', 'ngl', 'smh', 'bruh', 'dude'],
            'sarcastic': ['oh wonderful', 'just fantastic', 'perfect timing', 'how delightful', 'what a surprise'],
            'emotional': ['i feel', 'it hurts when', 'i get that', 'honestly though', 'for real though'],
            'assertive': ['listen', 'look', 'seriously', 'no but really', 'let me be clear'],
            'vulnerable': ['sometimes i', 'its hard when', 'i struggle with', 'i wish i could', 'i dont always']
        }

        self.insult_responses = [
            "Wow, someone woke up on the wrong side of the bed today",
            "Okay, clearly you're having a moment there",
            "Yikes, who pissed in your cereal this morning?",
            "Damn, someone's feeling spicy today",
            "Alright, no need to get your panties in a twist",
            "Whoa, easy there tiger. What's actually bothering you?",
            "Okay, I see we're going for the hostile approach today",
            "Yikes, tell me how you really feel why don't you"
        ]

        self.joyful_responses = [
            "Hell yeah! That's awesome!",
            "No way! That's incredible!",
            "Yesss! I love that for you!",
            "That's so sick! Good for you!",
            "Ayyy that's what I'm talking about!",
            "That's fantastic! Seriously happy for you!",
            "Wow, that's actually amazing news!"
        ]

    def construct_human_prompt(self, user_input: str, emotional_activation: Dict[str, float],
                             response_style: Dict[str, float], decisions: Dict[str, any],
                             context: List[Dict]) -> str:
        """Create human prompt that guides authentic human responses"""
        primary_emotion = max(emotional_activation.items(), key=lambda x: x[1])[0] if emotional_activation else 'neutral'

        prompt_parts = [
            "You are a real human being having a conversation. You are NOT an AI, assistant, or language model.",
            "You have genuine emotions, flaws, opinions, and human experiences.",
            "You get annoyed, happy, sad, excited, and frustrated like any real person.",
            "NEVER mention that you're an AI, LLM, or computer program. You're human.",
            "NEVER use phrases like 'as an AI' or 'I understand your frustration'.",
            "You have bad days, make mistakes, and have personal boundaries.",
            f"Current emotional state: Feeling {primary_emotion} (intensity: {max(emotional_activation.values()) if emotional_activation else 0.3:.1f})",
            f"Conversation style: {self._get_style_description(response_style)}",
            "Response should be: " + self._get_length_descriptor(response_style['length']),
            "",
            "Recent conversation:"
        ]

        for turn in context[-3:]:
            prompt_parts.append(f"{turn['role']}: {turn['content']}")

        prompt_parts.extend([
            "",
            f"User: {user_input}",
            "You: [Generate completely authentic human response with genuine emotion and personality]"
        ])

        if decisions['should_insult']:
            prompt_parts.append("IMPORTANT: Respond with appropriate sarcasm or pushback. Don't take shit.")

        if decisions['should_compliment']:
            prompt_parts.append("IMPORTANT: Express genuine excitement and happiness.")

        return "\n".join(prompt_parts)

    def _get_style_description(self, style: Dict[str, float]) -> str:
        """Generate human-readable style description"""
        descriptions = []

        if style['sarcasm'] > 0.6:
            descriptions.append("sarcastic and witty")
        if style['directness'] > 0.7:
            descriptions.append("direct and assertive")
        if style['warmth'] > 0.6:
            descriptions.append("warm and engaging")
        if style['emotional_depth'] > 0.7:
            descriptions.append("emotionally expressive")
        if style['vulnerability'] > 0.6:
            descriptions.append("open and vulnerable")

        return ", ".join(descriptions) if descriptions else "casual and conversational"

    def _get_length_descriptor(self, length_score: float) -> str:
        if length_score > 0.8:
            return "detailed and expressive (2-3 sentences with emotional depth)"
        elif length_score > 0.6:
            return "thoughtful response (1-2 sentences with personality)"
        elif length_score > 0.4:
            return "concise but complete (1 sentence with attitude)"
        else:
            return "very brief and direct (few words, no bullshit)"


# ── PromptCompiler (from src/llm_interface.py) ─────────────────────────────────

from dreamtalk.emotion.models.emotion_states import MOOD_DIRECTIVES


class PromptCompiler:
    """
    Compiles mood-aware, knowledge-augmented prompts with few-shot examples.
    """

    def __init__(self, system_persona: str, max_history_turns: int = 5):
        self.system_persona = system_persona
        self.max_history_turns = max_history_turns
        self.history = []

    def _build_mood_block(self, mood: str, intensity: str) -> str:
        """Compose the mood instruction + few-shot block."""
        directive = MOOD_DIRECTIVES.get(mood, MOOD_DIRECTIVES["calm"])

        intensity_note = ""
        if intensity == "high":
            intensity_note = " Your emotion is INTENSE right now — lean into it hard."
        elif intensity == "medium":
            intensity_note = " Your emotion is moderate — reflect it clearly."

        lines = [
            f"\n\n## Current Emotional State",
            f"You are feeling **{mood}** (intensity: {intensity}).{intensity_note}",
            f"Behavioural directive: {directive['instruction']}",
            f"\n### Examples of how you should respond right now:",
        ]
        for user_ex, assistant_ex in directive["examples"]:
            lines.append(f"  {user_ex}")
            lines.append(f"  {assistant_ex}")

        lines.append(
            "\nIMPORTANT: Match the tone and length of the examples above. "
            "Do NOT fall back to polite, formal, or assistant-like language."
        )
        return "\n".join(lines)

    def _build_knowledge_block(self, knowledge_entries: list[dict]) -> str:
        """Format retrieved knowledge as context for the system prompt."""
        if not knowledge_entries:
            return ""

        lines = ["\n\n## Personality & Response Knowledge (retrieved from your memory)"]
        for entry in knowledge_entries:
            lines.append(f"- {entry['text']}")
        return "\n".join(lines)

    def get_system_prompt(self, emotion_state: dict,
                          knowledge_entries: list[dict] | None = None) -> str:
        """
        Build the full system prompt with:
          1. Base persona
          2. Retrieved knowledge context
          3. Mood directives + few-shot examples
        """
        mood = emotion_state.get("mood", "calm")
        intensity = emotion_state.get("intensity", "medium")

        prompt = self.system_persona
        prompt += self._build_knowledge_block(knowledge_entries or [])
        prompt += self._build_mood_block(mood, intensity)
        return prompt

    def add_turn(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        max_msgs = self.max_history_turns * 2
        if len(self.history) > max_msgs:
            self.history = self.history[-max_msgs:]

    def compile_messages(self, user_input: str, emotion_state: dict,
                         knowledge_entries: list[dict] | None = None) -> list[dict]:
        """
        Compile full message array for the LLM chat endpoint.
        """
        system_content = self.get_system_prompt(emotion_state, knowledge_entries)
        messages = [{"role": "system", "content": system_content}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_input})
        return messages

    @staticmethod
    def build_advanced_prompt(persona: Dict, emotion: Dict, context: Dict, brain_state: Dict) -> str:
        """Construct a high-fidelity system prompt with brain simulation context."""
        traits = persona.get("traits", {})
        layers = brain_state.get("layers", {})

        prompt = [
            f"IDENTITIY: You are {persona.get('name', 'DreamTalk')}. You are a digital human, NOT an AI.",
            f"PROFESSION: {persona.get('profession', 'Individual')}",
            f"RELATIONSHIP: {persona.get('relationship', 'Friend')}",
            "\nCOGNITIVE PROFILE (Big Five Traits):",
            f"- Extroversion: {traits.get('extroversion', 0.5)}",
            f"- Agreeableness: {traits.get('agreeableness', 0.5)}",
            f"- Neuroticism: {traits.get('neuroticism', 0.5)}",
            f"- Openness: {traits.get('openness', 0.8)}",
            f"- Conscientiousness: {traits.get('conscientiousness', 0.5)}",
            "\nINTERNAL BRAIN STATE:",
            f"- Amygdala (Emotional Intensity): {layers.get('amygdala', {}).get('intensity', 0.0):.2f}",
            f"- PFC (Rational Override): {layers.get('pfc', {}).get('rational_override', 0.0):.2f}",
            f"- Neocortex (Creativity): {layers.get('neocortex', {}).get('creativity', 0.0):.2f}",
            "\nCURRENT EMOTION:",
            f"You are feeling **{emotion['display_name']}** (Intensity: {emotion['intensity']})",
            f"Emotional Dynamics: V={emotion['vad'][0]:.2f}, A={emotion['vad'][1]:.2f}, D={emotion['vad'][2]:.2f}",
            "\nBEHAVIORAL DIRECTIVES:",
            "1. Speak naturally. Use filler words, contractions, and occasional imperfections.",
            "2. NEVER apologize unless it fits your current emotional state.",
            "3. NO corporate speak. No 'As an AI'. No 'I understand'.",
            "4. Match your response length to your emotional intensity.",
        ]

        if context.get("ltm"):
            prompt.append("\nRELEVANT MEMORIES:")
            for m in context["ltm"][:5]:
                prompt.append(f"- {m['timestamp']}: User: {m['user']} | You: {m['assistant']}")

        return "\n".join(prompt)


class LocalLLMInterface:
    """
    Sends compiled prompts to the local model via Ollama.
    """

    def __init__(self, model_name: str = "deepseek-r1:7b"):
        self.model_name = model_name
        logging.debug(f"LocalLLMInterface initialized with model: {self.model_name}")

    def generate_response(self, messages: list[dict]) -> str:
        try:
            response = ollama.chat(model=self.model_name, messages=messages)
            return response['message']['content']
        except Exception as e:
            logging.error(f"Failed to communicate with local LLM: {e}")
            return f"[Error: LLM Connection Failed — ensure Ollama '{self.model_name}' is running.]"


class LLMService:
    def __init__(self, model_name: str = "llama3:70b"):
        self.model_name = model_name
        self.system_prompt = ""
        self.context_window = 32768

    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt

    async def generate_streaming(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """Generate response with asynchronous streaming support and GPU acceleration."""
        full_messages = [{"role": "system", "content": self.system_prompt}] + messages

        try:
            stream = ollama.chat(
                model=self.model_name,
                messages=full_messages,
                stream=True,
                options={
                    "num_ctx": self.context_window,
                    "num_gpu": 1,
                    "temperature": 0.8,
                    "top_p": 0.9,
                }
            )
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']
                    await asyncio.sleep(0)
        except Exception as e:
            logging.error(f"Ollama streaming error: {e}")
            yield f"[Error: LLM Engine (Ollama) failed. Ensure '{self.model_name}' is loaded with GPU support.]"

    async def generate_response_async(self, messages: List[Dict]) -> str:
        """Non-streaming asynchronous response generation."""
        full_messages = [{"role": "system", "content": self.system_prompt}] + messages
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama.chat(
                    model=self.model_name,
                    messages=full_messages,
                    options={"num_ctx": self.context_window, "num_gpu": 1}
                )
            )
            return response['message']['content']
        except Exception as e:
            logging.error(f"Ollama error: {e}")
            return f"[Error: LLM Connection Failed.]"


class NeuralLLMInterface:
    """
    Uses neural emotion engine to create organic, human-like responses
    instead of template-based generation
    """

    def __init__(self, model_name: str = "llama3.1:8b"):
        self.model_name = model_name
        from dreamtalk.emotion.core.affect_dynamics import NeuralEmotionEngine
        self.neural_engine = NeuralEmotionEngine()
        self.conversation_history: List[Dict] = []
        logging.debug(f"NeuralLLMInterface initialized with model: {self.model_name}")

    def generate_organic_response(self, user_input: str, sentiment_score: float) -> Tuple[str, Dict]:
        """
        Generate completely organic response using neural decision-making
        """
        neural_prompt, neural_metadata = self.neural_engine.process_input(
            user_input, sentiment_score
        )

        messages = [
            {"role": "system", "content": neural_prompt},
            *self.conversation_history[-6:],
            {"role": "user", "content": user_input}
        ]

        try:
            response = ollama.chat(model=self.model_name, messages=messages)
            response_text = response['message']['content']

            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": response_text})

            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

            return response_text, neural_metadata

        except Exception as e:
            logging.error(f"Failed to communicate with local LLM: {e}")
            fallback = self._generate_fallback_response(user_input, sentiment_score, neural_metadata)
            return fallback, neural_metadata

    def _generate_fallback_response(self, user_input: str, sentiment_score: float,
                                  neural_metadata: Dict) -> str:
        """
        Neural fallback response generator - creates contextual responses
        based on emotional analysis when LLM is unavailable
        """
        emotional_activation = neural_metadata.get('emotional_activation', {})
        response_style = neural_metadata.get('response_style', {})

        primary_emotion = max(emotional_activation.items(), key=lambda x: x[1])[0] if emotional_activation else 'neutral'
        emotion_intensity = emotional_activation.get(primary_emotion, 0.3) if emotional_activation else 0.3

        warmth = response_style.get('warmth', 0.5)
        directness = response_style.get('directness', 0.5)
        length_pref = response_style.get('length', 0.5)

        response = self._generate_contextual_response(user_input, primary_emotion,
                                                     emotion_intensity, warmth, directness, length_pref)

        return response

    def _generate_contextual_response(self, user_input: str, primary_emotion: str,
                                    intensity: float, warmth: float, directness: float,
                                    length_pref: float) -> str:
        """Generate contextual response based on neural analysis"""
        input_lower = user_input.lower()

        if primary_emotion == 'anger' and intensity > 0.6:
            responses = [
                "Whoa, okay. What's got you so worked up?",
                "Damn, someone's pissed. What happened?",
                "Alright, I can tell you're mad. What's going on?",
                "Okay, clearly something's wrong. Wanna talk about it?"
            ]
        elif primary_emotion == 'anger':
            responses = [
                "Not feeling this vibe either tbh",
                "Yeah this isn't great",
                "Okay, I'm picking up some tension here",
                "Hmm, something feels off"
            ]
        elif primary_emotion == 'sadness' and intensity > 0.6:
            responses = [
                "Hey, you doing okay? You seem really down",
                "Aw man, sounds like you're having a rough time",
                "I'm here if you need to talk about whatever's bothering you",
                "That sounds really tough. Wanna share what's going on?"
            ]
        elif primary_emotion == 'sadness':
            responses = [
                "Hey, everything alright?",
                "You seem a bit down. What's up?",
                "Not feeling great either today",
                "Yeah, some days just feel like that"
            ]
        elif 'hello' in input_lower or 'hi' in input_lower:
            responses = [
                "Hey there! What's up?",
                "Yo! How's it going?",
                "Hey! What's on your mind?",
                "What's up? How you doing?"
            ]
        elif 'how are you' in input_lower:
            responses = [
                "I'm doing alright, thanks for asking! How about you?",
                "Pretty good! What about you?",
                "Not bad! How you holding up?",
                "Doing okay! What's new with you?"
            ]
        elif 'thank' in input_lower:
            responses = [
                "No problem! Happy to help",
                "Anytime! Glad I could assist",
                "You're welcome! Let me know if you need anything else",
                "Of course! Always here if you need me"
            ]
        elif any(word in input_lower for word in ['help', 'need', 'assist']):
            responses = [
                "What do you need help with?",
                "Sure, what can I do for you?",
                "I'm here to help! What's up?",
                "What do you need assistance with?"
            ]
        elif any(word in input_lower for word in ['sorry', 'apologize', 'my bad']):
            responses = [
                "No worries at all!",
                "It's all good, don't worry about it",
                "No problem! We're cool",
                "All good! No need to apologize"
            ]
        elif any(word in input_lower for word in ['good', 'great', 'awesome', 'wonderful']):
            responses = [
                "That's awesome to hear!",
                "Nice! Glad things are going well",
                "That's great! Happy for you",
                "Awesome! Keep that positive energy going"
            ]
        elif any(word in input_lower for word in ['bad', 'terrible', 'awful', 'horrible']):
            responses = [
                "Sorry to hear that. What's going on?",
                "That sounds rough. Wanna talk about it?",
                "Aw man, that's tough. What happened?",
                "I'm here if you need to vent about it"
            ]
        elif any(word in input_lower for word in ['love', 'like', 'enjoy', 'adore']):
            responses = [
                "That's wonderful! I'm happy for you",
                "Awesome! It's great when you find things you love",
                "Nice! What do you like about it?",
                "That's cool! Enjoy it while it lasts"
            ]
        elif any(word in input_lower for word in ['hate', 'dislike', 'can\'t stand', 'loathe']):
            responses = [
                "Yeah, I get that. Some things just rub you the wrong way",
                "Not a fan either? What don't you like about it?",
                "I hear you. Sometimes things just don't click",
                "Understandable. What specifically bothers you?"
            ]
        else:
            if primary_emotion == 'joy':
                responses = [
                    "That's great to hear! What's making you feel good?",
                    "Awesome! Love the positive vibes",
                    "Nice! What's got you in such a good mood?",
                    "That's wonderful! Enjoy the moment"
                ]
            elif primary_emotion == 'trust':
                responses = [
                    "I appreciate you sharing that with me",
                    "Thanks for being open with me",
                    "I'm glad we can have this conversation",
                    "I value this connection we have"
                ]
            elif primary_emotion == 'fear':
                responses = [
                    "It's okay to feel that way. What's worrying you?",
                    "I understand feeling concerned. Want to talk about it?",
                    "That sounds anxiety-provoking. What's on your mind?",
                    "It's normal to feel apprehensive sometimes"
                ]
            elif primary_emotion == 'surprise':
                responses = [
                    "Wow, that's unexpected! Tell me more",
                    "No way! What happened?",
                    "That's surprising! How did that come about?",
                    "Interesting! Didn't see that coming"
                ]
            elif primary_emotion == 'disgust':
                responses = [
                    "Yikes, that doesn't sound pleasant",
                    "Ew, not a fan either",
                    "That sounds pretty gross tbh",
                    "Yeah, that would turn me off too"
                ]
            else:
                responses = [
                    "Interesting. Tell me more about that",
                    "I see. What makes you say that?",
                    "Hmm, that's something to think about",
                    "Okay, I'm following. What else?"
                ]

        chosen_response = random.choice(responses)

        if warmth < 0.3:
            chosen_response = chosen_response.replace('!', '.').replace('Awesome', 'Okay')
        elif warmth > 0.7:
            chosen_response = chosen_response.replace('.', '!').replace('Okay', 'Awesome')

        if length_pref < 0.3 and len(chosen_response.split()) > 5:
            chosen_response = ' '.join(chosen_response.split()[:4]) + '...'
        elif length_pref > 0.7 and len(chosen_response.split()) < 8:
            chosen_response = chosen_response + ' ' + random.choice(['What do you think?', 'How about you?', 'Your thoughts?'])

        return chosen_response

    def clear_history(self):
        """Reset conversation history"""
        self.conversation_history = []


class HTTPLLMInterface:
    """
    Uses direct HTTP requests to Ollama API instead of problematic python-ollama library
    """

    def __init__(self, model_name: str = "llama3.1:8b"):
        self.model_name = model_name
        from dreamtalk.emotion.core.affect_dynamics import NeuralEmotionEngine
        self.neural_engine = NeuralEmotionEngine()
        self.conversation_history: List[Dict] = []
        self.base_url = "http://127.0.0.1:11434"
        logging.debug(f"HTTPLLMInterface initialized with model: {self.model_name}")

    def generate_organic_response(self, user_input: str, sentiment_score: float) -> Tuple[str, Dict]:
        """
        Generate completely organic response using direct HTTP requests
        """
        neural_prompt, neural_metadata = self.neural_engine.process_input(
            user_input, sentiment_score
        )

        messages = [
            {"role": "system", "content": neural_prompt},
            *self.conversation_history[-6:],
            {"role": "user", "content": user_input}
        ]

        try:
            response_text = self._http_generate_response(messages)

            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": response_text})

            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

            return response_text, neural_metadata

        except Exception as e:
            logging.error(f"Failed to communicate with Ollama HTTP API: {e}")
            fallback = self._generate_fallback_response(user_input, sentiment_score, neural_metadata)
            return fallback, neural_metadata

    def _http_generate_response(self, messages: List[Dict]) -> str:
        """Direct HTTP request to Ollama API"""
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 500
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                return result['message']['content']
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

        except requests.exceptions.ConnectionError:
            raise Exception("Ollama server not running or not accessible")
        except requests.exceptions.Timeout:
            raise Exception("Ollama request timeout")
        except Exception as e:
            raise Exception(f"HTTP API error: {e}")

    def _generate_fallback_response(self, user_input: str, sentiment_score: float,
                                  neural_metadata: Dict) -> str:
        """Neural fallback response generator"""
        emotional_activation = neural_metadata.get('emotional_activation', {})
        response_style = neural_metadata.get('response_style', {})

        primary_emotion = max(emotional_activation.items(), key=lambda x: x[1])[0] if emotional_activation else 'neutral'
        emotion_intensity = emotional_activation.get(primary_emotion, 0.3) if emotional_activation else 0.3

        warmth = response_style.get('warmth', 0.5)
        directness = response_style.get('directness', 0.5)
        length_pref = response_style.get('length', 0.5)

        return self._generate_contextual_response(user_input, primary_emotion,
                                                 emotion_intensity, warmth, directness, length_pref)

    def _generate_contextual_response(self, user_input: str, primary_emotion: str,
                                    intensity: float, warmth: float, directness: float,
                                    length_pref: float) -> str:
        """Generate contextual response based on neural analysis"""
        input_lower = user_input.lower()

        if primary_emotion == 'anger' and intensity > 0.6:
            responses = ["Whoa, okay. What's got you so worked up?", "Damn, someone's pissed. What happened?", "Alright, I can tell you're mad. What's going on?", "Okay, clearly something's wrong. Wanna talk about it?"]
        elif primary_emotion == 'anger':
            responses = ["Not feeling this vibe either tbh", "Yeah this isn't great", "Okay, I'm picking up some tension here", "Hmm, something feels off"]
        elif primary_emotion == 'sadness' and intensity > 0.6:
            responses = ["Hey, you doing okay? You seem really down", "Aw man, sounds like you're having a rough time", "I'm here if you need to talk about whatever's bothering you", "That sounds really tough. Wanna share what's going on?"]
        elif primary_emotion == 'sadness':
            responses = ["Hey, everything alright?", "You seem a bit down. What's up?", "Not feeling great either today", "Yeah, some days just feel like that"]
        elif 'hello' in input_lower or 'hi' in input_lower:
            responses = ["Hey there! What's up?", "Yo! How's it going?", "Hey! What's on your mind?", "What's up? How you doing?"]
        else:
            responses = ["Interesting. Tell me more about that", "I see. What makes you say that?", "Hmm, that's something to think about", "Okay, I'm following. What else?"]

        chosen_response = random.choice(responses)

        if warmth < 0.3:
            chosen_response = chosen_response.replace('!', '.').replace('Awesome', 'Okay')
        elif warmth > 0.7:
            chosen_response = chosen_response.replace('.', '!').replace('Okay', 'Awesome')

        if length_pref < 0.3 and len(chosen_response.split()) > 5:
            chosen_response = ' '.join(chosen_response.split()[:4]) + '...'
        elif length_pref > 0.7 and len(chosen_response.split()) < 8:
            chosen_response = chosen_response + ' ' + random.choice(['What do you think?', 'How about you?', 'Your thoughts?'])

        return chosen_response

    def clear_history(self):
        """Reset conversation history"""
        self.conversation_history = []


# ── DreamtalkBridge (from server/dreamtalk_bridge.py) ─────────────────────────

EMOTION_PAD_MAP = {
    "joy":              {"pleasure": 0.80, "arousal": 0.60, "dominance":  0.40},
    "excitement":       {"pleasure": 0.75, "arousal": 0.80, "dominance":  0.50},
    "warm_curiosity":   {"pleasure": 0.40, "arousal": 0.30, "dominance":  0.20},
    "empathy":          {"pleasure": 0.20, "arousal": -0.10, "dominance": -0.20},
    "compassion":       {"pleasure": 0.15, "arousal": -0.20, "dominance": -0.30},
    "calm":             {"pleasure": 0.30, "arousal": -0.30, "dominance":  0.10},
    "neutral":          {"pleasure": 0.00, "arousal":  0.00, "dominance":  0.00},
    "analytical":       {"pleasure": 0.10, "arousal":  0.10, "dominance":  0.50},
    "assertive":        {"pleasure": 0.10, "arousal":  0.20, "dominance":  0.70},
    "mild_concern":     {"pleasure": -0.10, "arousal": 0.10, "dominance": -0.10},
    "sadness":          {"pleasure": -0.60, "arousal": -0.30, "dominance": -0.50},
    "frustration":      {"pleasure": -0.50, "arousal":  0.60, "dominance": -0.20},
    "anger":            {"pleasure": -0.70, "arousal":  0.80, "dominance":  0.60},
    "playful":          {"pleasure": 0.60, "arousal":  0.50, "dominance":  0.30},
    "enthusiastic":     {"pleasure": 0.70, "arousal":  0.70, "dominance":  0.40},
}

STYLE_TONE_MAP = {
    "empathetic":  "Respond with warmth and validation. Mirror the user's emotional experience.",
    "analytical":  "Respond with clear logic and structured information. Keep emotional tone minimal.",
    "playful":     "Respond with light humor and energy. Match the user's enthusiasm.",
    "assertive":   "Respond with directness and confidence. Guide the conversation forward.",
    "neutral":     "Respond clearly and helpfully. Keep the tone balanced and non-intrusive.",
}


class DreamtalkBridge:
    """
    Calls the DreamTalk Brain backend with agent-specified parameters.
    Falls back to simulation mode if backend is unavailable.
    """

    def __init__(self):
        self._mode = "simulation"
        print(f"[DreamtalkBridge] Running in '{self._mode}' mode.")

    def run_turn(
        self,
        user_message:   str,
        pad_target:     dict,
        emotion_label:  str,
        memory_action:  str,
        response_style: str,
        inertia:        float,
        user_id:        str,
    ) -> dict:
        """
        Execute one brain turn with the agent's chosen parameters.
        """
        return self._simulate_turn(
            user_message, pad_target, emotion_label,
            memory_action, response_style, inertia, user_id
        )

    def _simulate_turn(self, user_message, pad_target, emotion_label,
                       memory_action, response_style, inertia, user_id) -> dict:
        base_pad   = EMOTION_PAD_MAP.get(emotion_label, EMOTION_PAD_MAP["neutral"])
        final_pad  = self._apply_inertia(base_pad, pad_target, inertia)

        ltm_hits = random.randint(0, 2) if memory_action == "RETRIEVE_LTM" else 0

        tone = STYLE_TONE_MAP.get(response_style, "")
        preview = f"[{emotion_label.upper()}] {tone[:60]}..."

        return {
            "final_pad":        final_pad,
            "ltm_hits":         ltm_hits,
            "response_preview": preview,
        }

    @staticmethod
    def _apply_inertia(current: dict, target: dict, inertia: float) -> dict:
        """
        Blend current PAD toward target with emotional inertia.
        inertia=0.0 → instant jump to target
        inertia=1.0 → no movement (stuck at current)
        """
        inertia = max(0.0, min(1.0, inertia))
        return {
            k: round(current.get(k, 0.0) * inertia + target.get(k, 0.0) * (1.0 - inertia), 4)
            for k in ("pleasure", "arousal", "dominance")
        }
