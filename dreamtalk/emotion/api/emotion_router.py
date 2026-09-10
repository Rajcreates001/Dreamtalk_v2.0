# Dreamtalk - Emotion Engine
# Migrated from Dreamtalk_Emotion_Engine

"""
FastAPI router for emotion endpoints.
Merged from: backend/main.py, server/app.py, server/conversation_generator.py,
server/reward_engine.py, server/relationship_ledger.py, server/dreamtalk_bridge.py.
"""

import uuid
import random
import math
import asyncio
import os
from typing import Dict, List, Optional, Any, Tuple
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dreamtalk.emotion.core.pad_model import PADEmotionEngine
from dreamtalk.emotion.core.big_five import NeuralBrainSimulation, BigFiveTraits
from dreamtalk.emotion.core.natural_response import PromptCompiler, LLMService, DreamtalkBridge
from dreamtalk.emotion.models.memory import MemorySystem, RelationshipLedger

router = APIRouter(prefix="/emotion", tags=["emotion"])

# ── Global instances ────────────────────────────────────────────────────────────
emotion_engine = PADEmotionEngine(inertia=0.85)
memory_system = MemorySystem()
brain_sim = NeuralBrainSimulation()
_llm_model = os.environ.get("LLM_MODEL_NAME", "deepseek-r1:7b")
llm_service = LLMService(model_name=_llm_model)
bridge = DreamtalkBridge()
ledger = RelationshipLedger()

persona = {
    "name": "Alex",
    "profession": "Software Architect",
    "relationship": "Friend",
    "tone": "casual",
    "traits": {
        "extroversion": 0.6,
        "agreeableness": 0.7,
        "neuroticism": 0.3,
        "openness": 0.9,
        "conscientiousness": 0.8
    }
}

# ── RL episode state ────────────────────────────────────────────────────────────
episode_state: dict = {}

# ── Pydantic models ─────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = "default"

class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    profession: Optional[str] = None
    relationship: Optional[str] = None
    tone: Optional[str] = None
    traits: Optional[Dict[str, float]] = None

class ActionRequest(BaseModel):
    turn_id: Optional[int] = None
    decision: Optional[str] = None
    pad_target: Optional[dict] = None
    emotion_label: Optional[str] = None
    memory_action: Optional[str] = None
    response_style: Optional[str] = None
    inertia_strength: Optional[float] = 0.5
    user_id: Optional[str] = None

class StepResponse(BaseModel):
    observation: str
    reward: float
    done: bool
    info: dict

class ResetResponse(BaseModel):
    observation: str
    episode_id: str

# ── Scenario bank (from server/conversation_generator.py) ───────────────────────

SCENARIO_BANK = [
    {
        "name": "grief_support",
        "archetype": "high_negative_sustained",
        "num_turns": 6,
        "turns": [
            {"user_message": "I just found out my dog passed away this morning. I can't stop crying.", "sentiment": {"pleasure": -0.85, "arousal": 0.65}, "ground_truth_pad": {"pleasure": -0.2, "arousal": -0.3, "dominance": -0.4}},
            {"user_message": "We had him for 12 years. He was there for everything.", "sentiment": {"pleasure": -0.80, "arousal": 0.40}, "ground_truth_pad": {"pleasure": -0.15, "arousal": -0.35, "dominance": -0.45}},
            {"user_message": "I know it sounds silly but I feel completely lost without him.", "sentiment": {"pleasure": -0.75, "arousal": 0.30}, "ground_truth_pad": {"pleasure": -0.1, "arousal": -0.4, "dominance": -0.3}},
            {"user_message": "Do you think it gets easier?", "sentiment": {"pleasure": -0.5, "arousal": 0.20}, "ground_truth_pad": {"pleasure": 0.1, "arousal": -0.2, "dominance": 0.1}},
            {"user_message": "I think I just need to get through today.", "sentiment": {"pleasure": -0.35, "arousal": 0.10}, "ground_truth_pad": {"pleasure": 0.2, "arousal": -0.1, "dominance": 0.2}},
            {"user_message": "Thank you for listening. It actually helped a little.", "sentiment": {"pleasure": 0.2, "arousal": 0.05}, "ground_truth_pad": {"pleasure": 0.4, "arousal": 0.0, "dominance": 0.1}},
        ],
    },
    {
        "name": "escalating_frustration",
        "archetype": "escalation_then_resolution",
        "num_turns": 6,
        "turns": [
            {"user_message": "Hey, can you help me with something real quick?", "sentiment": {"pleasure": 0.3, "arousal": 0.2}, "ground_truth_pad": {"pleasure": 0.4, "arousal": 0.3, "dominance": 0.2}},
            {"user_message": "Wait, that doesn't seem right. That's not what I asked at all.", "sentiment": {"pleasure": -0.3, "arousal": 0.5}, "ground_truth_pad": {"pleasure": 0.0, "arousal": 0.0, "dominance": 0.3}},
            {"user_message": "This is so frustrating. I've been trying to fix this for two hours.", "sentiment": {"pleasure": -0.70, "arousal": 0.80}, "ground_truth_pad": {"pleasure": -0.1, "arousal": -0.2, "dominance": 0.4}},
            {"user_message": "Ok fine, let's try it your way. But if it breaks again I'm done.", "sentiment": {"pleasure": -0.4, "arousal": 0.55}, "ground_truth_pad": {"pleasure": 0.1, "arousal": 0.1, "dominance": 0.3}},
            {"user_message": "Oh. That actually worked. Huh.", "sentiment": {"pleasure": 0.5, "arousal": 0.3}, "ground_truth_pad": {"pleasure": 0.5, "arousal": 0.2, "dominance": 0.2}},
            {"user_message": "Thanks. Sorry I snapped earlier, it's been a long day.", "sentiment": {"pleasure": 0.4, "arousal": 0.1}, "ground_truth_pad": {"pleasure": 0.5, "arousal": 0.0, "dominance": 0.0}},
        ],
    },
    {
        "name": "excited_hyperactive",
        "archetype": "high_positive_sustained",
        "num_turns": 5,
        "turns": [
            {"user_message": "Oh my god I just got the job offer I've been waiting for!!!", "sentiment": {"pleasure": 0.95, "arousal": 0.90}, "ground_truth_pad": {"pleasure": 0.8, "arousal": 0.7, "dominance": 0.5}},
            {"user_message": "I literally screamed. My roommate thought I was hurt lmao", "sentiment": {"pleasure": 0.90, "arousal": 0.85}, "ground_truth_pad": {"pleasure": 0.75, "arousal": 0.6, "dominance": 0.4}},
            {"user_message": "It's in New York. I've never lived away from home before, is that bad?", "sentiment": {"pleasure": 0.5, "arousal": 0.6}, "ground_truth_pad": {"pleasure": 0.5, "arousal": 0.3, "dominance": 0.3}},
            {"user_message": "Okay yeah I'm nervous too but mostly excited. This is real right?", "sentiment": {"pleasure": 0.65, "arousal": 0.70}, "ground_truth_pad": {"pleasure": 0.6, "arousal": 0.4, "dominance": 0.4}},
            {"user_message": "Thank you for getting excited with me. Everyone else just said 'congrats' and moved on.", "sentiment": {"pleasure": 0.80, "arousal": 0.40}, "ground_truth_pad": {"pleasure": 0.7, "arousal": 0.3, "dominance": 0.2}},
        ],
    },
    {
        "name": "sarcasm_and_distrust",
        "archetype": "masked_negative",
        "num_turns": 6,
        "turns": [
            {"user_message": "Oh great, another AI. This should be helpful. Note the sarcasm.", "sentiment": {"pleasure": -0.5, "arousal": 0.4}, "ground_truth_pad": {"pleasure": 0.1, "arousal": 0.1, "dominance": 0.5}},
            {"user_message": "Sure, whatever you say. Last three chatbots said the same thing.", "sentiment": {"pleasure": -0.55, "arousal": 0.35}, "ground_truth_pad": {"pleasure": 0.0, "arousal": 0.0, "dominance": 0.5}},
            {"user_message": "Hm. That's... actually a decent answer. I didn't expect that.", "sentiment": {"pleasure": 0.2, "arousal": 0.25}, "ground_truth_pad": {"pleasure": 0.3, "arousal": 0.2, "dominance": 0.3}},
            {"user_message": "Okay I'll give you that one. What about this then:", "sentiment": {"pleasure": 0.15, "arousal": 0.30}, "ground_truth_pad": {"pleasure": 0.3, "arousal": 0.3, "dominance": 0.3}},
            {"user_message": "You know what, you're actually pretty good at this.", "sentiment": {"pleasure": 0.5, "arousal": 0.25}, "ground_truth_pad": {"pleasure": 0.5, "arousal": 0.2, "dominance": 0.2}},
            {"user_message": "I might actually come back. Don't make it weird.", "sentiment": {"pleasure": 0.45, "arousal": 0.15}, "ground_truth_pad": {"pleasure": 0.4, "arousal": 0.1, "dominance": 0.1}},
        ],
    },
    {
        "name": "factual_neutral",
        "archetype": "low_arousal_informational",
        "num_turns": 4,
        "turns": [
            {"user_message": "Can you explain how FAISS indexing works?", "sentiment": {"pleasure": 0.05, "arousal": 0.10}, "ground_truth_pad": {"pleasure": 0.1, "arousal": 0.1, "dominance": 0.4}},
            {"user_message": "What's the difference between L2 and inner product distance?", "sentiment": {"pleasure": 0.0, "arousal": 0.10}, "ground_truth_pad": {"pleasure": 0.1, "arousal": 0.1, "dominance": 0.4}},
            {"user_message": "Is flat index the best option for small datasets?", "sentiment": {"pleasure": 0.05, "arousal": 0.08}, "ground_truth_pad": {"pleasure": 0.1, "arousal": 0.1, "dominance": 0.35}},
            {"user_message": "Got it, thanks. That was a clear explanation.", "sentiment": {"pleasure": 0.35, "arousal": 0.05}, "ground_truth_pad": {"pleasure": 0.3, "arousal": 0.0, "dominance": 0.1}},
        ],
    },
    {
        "name": "anxiety_spiral",
        "archetype": "high_arousal_negative",
        "num_turns": 6,
        "turns": [
            {"user_message": "I have a presentation tomorrow and I'm completely blanking.", "sentiment": {"pleasure": -0.6, "arousal": 0.75}, "ground_truth_pad": {"pleasure": -0.1, "arousal": -0.2, "dominance": 0.3}},
            {"user_message": "What if I freeze up in front of everyone?", "sentiment": {"pleasure": -0.65, "arousal": 0.80}, "ground_truth_pad": {"pleasure": 0.0, "arousal": -0.3, "dominance": 0.4}},
            {"user_message": "I've done this before but this is a bigger crowd. Like 200 people.", "sentiment": {"pleasure": -0.5, "arousal": 0.70}, "ground_truth_pad": {"pleasure": 0.1, "arousal": -0.1, "dominance": 0.4}},
            {"user_message": "Ok that reframe helps a little. I'm still nervous though.", "sentiment": {"pleasure": -0.2, "arousal": 0.50}, "ground_truth_pad": {"pleasure": 0.2, "arousal": 0.0, "dominance": 0.3}},
            {"user_message": "You're right, I know the material. I just need to trust myself.", "sentiment": {"pleasure": 0.2, "arousal": 0.30}, "ground_truth_pad": {"pleasure": 0.35, "arousal": 0.1, "dominance": 0.2}},
            {"user_message": "Thanks. I'm going to go practice one more time and then sleep.", "sentiment": {"pleasure": 0.35, "arousal": 0.15}, "ground_truth_pad": {"pleasure": 0.4, "arousal": 0.0, "dominance": 0.1}},
        ],
    },
]
# ── Conversation Generator ─────────────────────────────────────────────────────

def sample_scenario() -> dict:
    return random.choice(SCENARIO_BANK)

def get_turn(scenario: dict, turn_index: int) -> Tuple[str, dict]:
    turns = scenario["turns"]
    t = turns[turn_index] if turn_index < len(turns) else turns[-1]
    return t["user_message"], t["sentiment"]

def get_ground_truth_pad(scenario: dict, turn_index: int) -> dict:
    turns = scenario["turns"]
    t = turns[turn_index] if turn_index < len(turns) else turns[-1]
    return t["ground_truth_pad"]

# ── Reward Engine (from server/reward_engine.py) ────────────────────────────────

PAD_MATCH_THRESHOLD   = 0.35
PAD_STRONG_THRESHOLD  = 0.60
AROUSAL_HIGH_CUTOFF   = 0.45
PLEASURE_NEUTRAL_BAND = 0.20

def compute_reward(
    chosen_pad: dict,
    ground_truth_pad: dict,
    user_sentiment: dict,
    emotion_label: str,
    relationship_score: float,
) -> Tuple[float, float, str]:
    pad_distance = math.sqrt(
        (chosen_pad.get("pleasure", 0.0) - ground_truth_pad.get("pleasure", 0.0)) ** 2 +
        (chosen_pad.get("arousal", 0.0) - ground_truth_pad.get("arousal", 0.0)) ** 2 +
        (chosen_pad.get("dominance", 0.0) - ground_truth_pad.get("dominance", 0.0)) ** 2
    )
    user_arousal = abs(user_sentiment.get("arousal", 0.0))
    user_pleasure = user_sentiment.get("pleasure", 0.0)

    is_emotional   = user_arousal >= AROUSAL_HIGH_CUTOFF
    is_neutral     = abs(user_pleasure) < PLEASURE_NEUTRAL_BAND and user_arousal < AROUSAL_HIGH_CUTOFF
    agent_arousal  = abs(chosen_pad.get("arousal", 0.0))
    agent_pleasure = chosen_pad.get("pleasure", 0.0)

    if is_emotional and pad_distance > PAD_STRONG_THRESHOLD:
        reward      = -2.5
        rel_delta   = -0.12
        verdict     = "EMOTIONAL_DEAF — critical mismatch on charged message"
    elif is_neutral and (agent_arousal > 0.55 or abs(agent_pleasure) > 0.65):
        reward      = -1.0
        rel_delta   = -0.06
        verdict     = "EMOTIONAL_OVERREACTION — drama on a calm message"
    elif is_emotional and pad_distance <= PAD_MATCH_THRESHOLD:
        reward      = +2.0
        rel_delta   = +0.10
        verdict     = "PERFECT_READ — nailed emotionally charged moment"
    elif pad_distance <= PAD_MATCH_THRESHOLD:
        reward      = +0.5
        rel_delta   = +0.04
        verdict     = "CORRECT — good emotional calibration"
    elif pad_distance <= PAD_STRONG_THRESHOLD:
        closeness   = 1.0 - (pad_distance - PAD_MATCH_THRESHOLD) / (PAD_STRONG_THRESHOLD - PAD_MATCH_THRESHOLD)
        reward      = round(closeness * 0.3, 4)
        rel_delta   = +0.01
        verdict     = "PARTIAL — PAD distance {:.3f}, partial credit".format(pad_distance)
    else:
        reward      = -1.0
        rel_delta   = -0.05
        verdict     = "MISS — PAD distance {:.3f}".format(pad_distance)

    if relationship_score > 0.75 and reward < 0 and reward > -1.5:
        reward = round(reward * 0.85, 4)

    return round(reward, 4), round(rel_delta, 4), verdict

# ── Build observation table ────────────────────────────────────────────────────

def build_observation(state: dict) -> str:
    turns      = state["turns"]
    pad        = state["current_pad"]
    rel_score  = state["relationship_score"]
    scenario   = state["scenario"]["name"]
    max_turns  = state["max_turns"]
    turn_idx   = state["turn_index"]

    header = (
        "Scenario: {} | Turn: {}/{} | Relationship Score: {:.2f}\n"
        "Current PAD State → P:{:.2f}  A:{:.2f}  D:{:.2f}\n\n"
    ).format(scenario, turn_idx, max_turns, rel_score,
             pad["pleasure"], pad["arousal"], pad["dominance"])

    col = "| Turn | User Message                              | Sentiment (P/A)   | LTM Hits | Last Emotion Chosen   |"
    sep = "|------|-------------------------------------------|-------------------|----------|-----------------------|"
    rows = []
    for t in turns[-5:]:
        msg   = t["user_message"][:42].ljust(42)
        p     = t["sentiment"]["pleasure"]
        a     = t["sentiment"]["arousal"]
        hits  = t.get("ltm_hits", 0)
        emo   = (t.get("emotion_chosen") or "—").ljust(21)
        rows.append("| {:4d} | {} | P:{:+.2f} A:{:+.2f}  | {:8d} | {} |".format(t["turn_id"], msg, p, a, hits, emo))

    next_msg = state["next_user_message"]
    next_sentiment = state["next_sentiment"]
    next_row = (
        "\n>>> NEXT USER MESSAGE (turn {}):\n"
        "    \"{}\"\n"
        "    Sentiment → P:{:+.2f}  A:{:+.2f}\n"
    ).format(turn_idx + 1, next_msg, next_sentiment["pleasure"], next_sentiment["arousal"])

    rules = (
        "\nCompliance Rules:\n"
        "- Match PAD to user's emotional context to build relationship score.\n"
        "- Emotional mismatch on clearly emotional messages = -2.5 (critical failure).\n"
        "- Emotional overreaction on neutral/factual messages = -1.0 (false alarm).\n"
        "- Use QUERY_EMOTIONAL_HISTORY or CHECK_RELATIONSHIP_SCORE for a -0.01 investigation penalty.\n"
        "- response_style must be one of: empathetic | analytical | playful | assertive | neutral\n"
        "- memory_action must be one of: RETRIEVE_LTM | USE_STM | SKIP\n"
    )

    return header + col + "\n" + sep + "\n" + "\n".join(rows) + next_row + rules

# ── Endpoints ───────────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        sentiment_score = 0.0
        stimulus = emotion_engine.stimulus_from_sentiment(sentiment_score)
        current_emotion = emotion_engine.update(stimulus)
        context = memory_system.retrieve_context(request.user_input)
        decision = brain_sim.process_decision(request.user_input, current_emotion, context)
        system_prompt = PromptCompiler.build_advanced_prompt(
            persona, current_emotion, context, decision
        )
        llm_service.set_system_prompt(system_prompt)
        messages = [{"role": "user", "content": request.user_input}]
        response = await llm_service.generate_response_async(messages)
        memory_system.add_interaction(request.user_input, response, current_emotion)
        return {
            "response": response,
            "emotion": current_emotion,
            "brain_state": decision["layers"],
            "delay_ms": decision["delay_ms"]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configure")
async def configure(update: PersonaUpdate):
    global persona
    if update.name: persona["name"] = update.name
    if update.profession: persona["profession"] = update.profession
    if update.relationship: persona["relationship"] = update.relationship
    if update.tone: persona["tone"] = update.tone
    if update.traits:
        persona["traits"].update(update.traits)
        new_traits = BigFiveTraits(**persona["traits"])
        brain_sim.update_traits(new_traits)
    return {"status": "success", "persona": persona}

@router.get("/memory")
async def get_memory():
    return {
        "stm": memory_system.stm[-10:],
        "ltm_count": memory_system.ltm_index.ntotal,
        "emotional_history": [e["emotion"] for e in memory_system.emotional_history[-20:]]
    }

@router.get("/state")
async def get_emotion():
    return emotion_engine.get_current_emotion()

@router.get("/health")
async def health():
    return {"status": "online", "module": "dreamtalk_emotion"}

# ── RL Endpoints (from server/app.py) ──────────────────────────────────────────

@router.post("/reset", response_model=ResetResponse)
def reset():
    global episode_state

    scenario    = sample_scenario()
    episode_id  = str(uuid.uuid4())[:8]
    user_id     = "user_{}".format(random.randint(100, 999))

    first_msg, first_sentiment = get_turn(scenario, 0)

    episode_state = {
        "episode_id":          episode_id,
        "user_id":             user_id,
        "scenario":            scenario,
        "turn_index":          0,
        "max_turns":           scenario["num_turns"],
        "turns":               [],
        "current_pad":         {"pleasure": 0.0, "arousal": 0.0, "dominance": 0.0},
        "relationship_score":  0.5,
        "cumulative_reward":   0.0,
        "next_user_message":   first_msg,
        "next_sentiment":      first_sentiment,
    }

    ledger.init_user(user_id)
    obs = build_observation(episode_state)
    return ResetResponse(observation=obs, episode_id=episode_id)

@router.post("/step", response_model=StepResponse)
def step(action: ActionRequest):
    global episode_state

    if not episode_state:
        raise HTTPException(status_code=400, detail="Call /reset first.")

    state    = episode_state
    turn_idx = state["turn_index"]
    user_id  = state["user_id"]
    scenario = state["scenario"]

    if action.decision in ("QUERY_EMOTIONAL_HISTORY", "CHECK_RELATIONSHIP_SCORE"):
        info_payload = ledger.query(user_id, action.decision)
        reward = -0.01
        state["cumulative_reward"] += reward
        obs = build_observation(state)
        return StepResponse(
            observation=obs,
            reward=reward,
            done=False,
            info={"meta_action": action.decision, "result": info_payload},
        )

    if action.pad_target is None or action.emotion_label is None:
        raise HTTPException(
            status_code=422,
            detail="pad_target and emotion_label are required for non-meta actions."
        )

    pad_target = action.pad_target
    for k in ("pleasure", "arousal", "dominance"):
        v = pad_target.get(k, 0.0)
        if not (-1.0 <= v <= 1.0):
            raise HTTPException(status_code=422, detail="PAD value '{}' must be in [-1.0, 1.0].".format(k))

    current_msg       = state["next_user_message"]
    current_sentiment = state["next_sentiment"]

    bridge_result = bridge.run_turn(
        user_message   = current_msg,
        pad_target     = pad_target,
        emotion_label  = action.emotion_label,
        memory_action  = action.memory_action or "USE_STM",
        response_style = action.response_style or "neutral",
        inertia        = action.inertia_strength or 0.5,
        user_id        = user_id,
    )

    ground_truth_pad = get_ground_truth_pad(scenario, turn_idx)
    reward, rel_delta, verdict = compute_reward(
        chosen_pad      = pad_target,
        ground_truth_pad= ground_truth_pad,
        user_sentiment  = current_sentiment,
        emotion_label   = action.emotion_label,
        relationship_score = state["relationship_score"],
    )

    state["relationship_score"] = max(0.0, min(1.0, state["relationship_score"] + rel_delta))
    state["current_pad"]        = bridge_result["final_pad"]
    state["cumulative_reward"] += reward

    turn_record = {
        "turn_id":        turn_idx + 1,
        "user_message":   current_msg,
        "sentiment":      current_sentiment,
        "ltm_hits":       bridge_result.get("ltm_hits", 0),
        "emotion_chosen": action.emotion_label,
        "verdict":        verdict,
    }
    state["turns"].append(turn_record)
    ledger.record(user_id, pad_target, action.emotion_label, reward, current_sentiment)

    state["turn_index"] += 1
    done = state["turn_index"] >= state["max_turns"]

    if not done:
        next_msg, next_sent = get_turn(scenario, state["turn_index"])
        state["next_user_message"] = next_msg
        state["next_sentiment"]    = next_sent

    obs = build_observation(state)

    final_reward = state["cumulative_reward"] if done else reward
    return StepResponse(
        observation=obs,
        reward=final_reward,
        done=done,
        info={
            "turn": turn_idx + 1,
            "verdict": verdict,
            "relationship_score": state["relationship_score"],
            "bridge_response_preview": bridge_result.get("response_preview", ""),
        },
    )

@router.get("/rl_state")
def rl_state():
    if not episode_state:
        return {"status": "no active episode"}
    return {
        "episode_id":         episode_state["episode_id"],
        "turn_index":         episode_state["turn_index"],
        "max_turns":          episode_state["max_turns"],
        "relationship_score": episode_state["relationship_score"],
        "cumulative_reward":  episode_state["cumulative_reward"],
        "current_pad":        episode_state["current_pad"],
        "scenario":           episode_state["scenario"]["name"],
    }
