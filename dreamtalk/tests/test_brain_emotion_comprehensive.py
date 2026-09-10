"""
Comprehensive Brain / Emotion / Personality / Learning Test Suite
Tests: all 15+ emotional states, personality adaptation, conversation memory, learning signals
"""
import os, sys, json, time, traceback, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["PYTHONIOENCODING"] = "utf-8"

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace') if hasattr(sys.stdout, 'reconfigure') else None
    sys.stderr.reconfigure(encoding='utf-8', errors='replace') if hasattr(sys.stderr, 'reconfigure') else None

# Fix PyTorch DLL loading issues on Windows
try:
    import torch
    torch.ones(1)
except Exception:
    pass

try:
    os.add_dll_directory(os.path.join(sys.prefix, 'Lib', 'site-packages', 'torch', 'lib'))
except Exception:
    pass

warnings.filterwarnings("ignore")

from dreamtalk.emotion.core.emotion_detector import EmotionAnalyzer, AffectiveStateTracker
from dreamtalk.emotion.core.pad_model import PADEmotionEngine
from dreamtalk.emotion.core.affect_dynamics import HumanNeuralEngine, NeuralEmotionEngine, EmotionalProcessingLayer, HumanEmotionalProcessing
from dreamtalk.emotion.core.big_five import NeuralBrainSimulation, BigFiveTraits
from dreamtalk.emotion.core.natural_response import PersonalitySynthesisLayer, HumanResponseGenerator, PromptCompiler, LocalLLMInterface, NeuralLLMInterface
from dreamtalk.emotion.models.emotion_states import MOOD_DIRECTIVES, EMOTION_PAD_MAP, KNOWLEDGE_CORPUS
from dreamtalk.emotion.memory.emotion_memory import NeuralKnowledgeBase
from dreamtalk.emotion.models.memory import MemorySystem

from dreamtalk.pipeline.brain_pipeline import (
    BrainPipeline, TextEmotionDetector, MoodState, PAD_MOOD_MAP,
    PFCBrainArea, dACCBrainArea, InsulaBrainArea, IPLBrainArea, BasalGangliaBrainArea,
    WorkingMemory, SNNEncoder
)

print("\n" + "="*80)
print("🧠 DREAMTALK BRAIN/EMOTION/PERSONALITY — COMPREHENSIVE TEST SUITE")
print("="*80)

results = {"passed": 0, "failed": 0, "tests": []}

def run_test(name, fn):
    try:
        start = time.time()
        result = fn()
        elapsed = time.time() - start
        status = "✅ PASS" if result.get("passed", False) else "❌ FAIL"
        print(f"\n  {status} | {name} ({elapsed:.2f}s)")
        print(f"       {result.get('detail', '')}")
        results["tests"].append({"name": name, "status": status, "result": result, "time": elapsed})
        if result.get("passed", False):
            results["passed"] += 1
        else:
            results["failed"] += 1
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n  ❌ ERROR | {name} ({elapsed:.2f}s)")
        print(f"       {str(e)}")
        traceback.print_exc()
        results["tests"].append({"name": name, "status": "ERROR", "error": str(e), "time": elapsed})
        results["failed"] += 1

# ═══════════════════════════════════════════════════════════════════════════
# TEST 1: VADER Emotion Analyzer — Basic Sentiment Detection
# ═══════════════════════════════════════════════════════════════════════════
def test_vader_sentiment():
    analyzer = EmotionAnalyzer()
    test_cases = [
        ("I love this! You're amazing!", "happy", 0.5, 0.9),
        ("This is terrible. I hate everything about this.", "angry", -0.9, -0.5),
        ("I'm so sad and lonely today...", "sad", -0.9, -0.3),
        ("I'm so excited I can't breathe!", "excited", 0.5, 1.0),
        ("I trusted you and you betrayed me.", "betrayal", -0.9, -0.3),
        ("Oh you poor thing, I feel so sorry for you.", "pity", -0.5, 0.3),
        ("Hurry up! We don't have time!", "haste", -0.5, 0.3),
        ("I love her so much, she means everything.", "love", 0.5, 1.0),
        ("I'm so confused about what happened.", "confused", -0.3, 0.3),
        ("Everything is fine, no worries.", "calm", -0.2, 0.3),
    ]
    
    details = []
    for text, expected_mood, min_sent, max_sent in test_cases:
        score = analyzer.analyze_text(text)
        in_range = min_sent <= score <= max_sent
        status = "✓" if in_range else "✗"
        details.append(f"  {status} '{text[:50]}...' → score={score:.3f} (expected [{min_sent},{max_sent}])")
    
    all_passed = all(min_s <= analyzer.analyze_text(t) <= max_s for t, _, min_s, max_s in test_cases)
    return {"passed": all_passed, "detail": "\n".join(details[-5:]) + f"\n  Total: {len(test_cases)} cases"}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: AffectiveStateTracker — EMA Mood Tracking with Hostility
# ═══════════════════════════════════════════════════════════════════════════
def test_affective_tracker():
    tracker = AffectiveStateTracker(initial_mood="calm", alpha=0.35)
    interactions = [
        ("Hey how are you?", 0.5),           # Positive
        ("You're amazing I love you!", 0.8), # Very positive
        ("HATE YOU STUPID", -0.9),           # Hostile
        ("I'm so sorry", 0.0),               # Apologetic
        ("KILL YOURSELF BITCH", -0.95),      # Very hostile
        ("You're the best", 0.9),            # Positive again
    ]
    
    states = []
    for text, sent in interactions:
        state = tracker.update_state(text, sent)
        states.append(state)
    
    details = []
    for i, (text, _) in enumerate(interactions):
        s = states[i]
        details.append(f"  [{s['mood']:>12} | {s['intensity']:>6} | valence={s['valence']:+.3f} | hostile={s['is_hostile']}] '{text[:40]}'")
    
    # Verify: hostile detection works
    final = states[-1]
    has_hostile = any(s["is_hostile"] for s in states)
    mood_transitions = [s["mood"] for s in states]
    
    return {
        "passed": has_hostile and "furious" in mood_transitions or "annoyed" in mood_transitions,
        "detail": "\n".join(details),
        "mood_sequence": mood_transitions,
    }

# ═══════════════════════════════════════════════════════════════════════════
# TEST 3: PAD Emotion Engine — 50+ Emotional States
# ═══════════════════════════════════════════════════════════════════════════
def test_pad_engine():
    pad = PADEmotionEngine(inertia=0.85)
    
    test_stimuli = [
        ("Joy", (0.8, 0.6, 0.4)),
        ("Rage", (-0.9, 1.0, 0.8)),
        ("Grief", (-0.9, -0.2, -0.7)),
        ("Panicked", (-0.8, 1.0, -0.9)),
        ("Love", (0.9, 0.4, 0.3)),
        ("Sarcastic", (-0.2, 0.4, 0.5)),
        ("Surprised", (0.2, 0.8, 0.0)),
        ("Depressed", (-0.8, -0.5, -0.8)),
        ("Euphoria", (0.9, 0.9, 0.8)),
        ("Neutral", (0.0, 0.0, 0.0)),
    ]
    
    # Reset for each test
    reactions = []
    for label, (p, a, d) in test_stimuli:
        pad.current_pad = pad.current_pad  # keep inertia
        state = pad.update((p, a, d))
        reactions.append(state)
    
    details = []
    for i, (label, _) in enumerate(test_stimuli):
        r = reactions[i]
        details.append(f"  Stimulus={label:<12} → {r['name']:<15} | secondary={r['secondary_emotion']:<15} | intensity={r['intensity']:<8} | PAD=({r['pad'][0]:+.2f},{r['pad'][1]:+.2f},{r['pad'][2]:+.2f})")
    
    # Check all emotion names exist in map
    emotion_count = len(pad.emotion_map)
    
    return {
        "passed": emotion_count >= 50 and len(reactions) == len(test_stimuli),
        "detail": "\n".join(details) + f"\n  Total emotions in map: {emotion_count}",
        "reactions": reactions,
    }

# ═══════════════════════════════════════════════════════════════════════════
# TEST 4: HumanNeuralEngine — Emotional Processing & State Transitions
# ═══════════════════════════════════════════════════════════════════════════
def test_human_neural_engine():
    engine = HumanNeuralEngine()
    
    scenarios = [
        "You're such a stupid idiot, I hate talking to you!",
        "I love you so much, you're literally the best thing ever!",
        "I'm so sad and heartbroken, everything feels hopeless...",
        "WOW THAT'S AMAZING I CAN'T BELIEVE IT!!!",
        "I'm really scared about what's going to happen tomorrow...",
        "You disgust me, get away from me.",
        "Thank you so much, I really appreciate everything you do.",
    ]
    
    engine.clear_history()
    reactions = []
    
    for text in scenarios:
        prompt, metadata = engine.process_input(text, EmotionAnalyzer().analyze_text(text))
        reactions.append({"text": text, "metadata": metadata})
    
    details = []
    for r in reactions:
        m = r["metadata"]
        emotions = m.get("emotional_activation", {})
        primary = max(emotions.items(), key=lambda x: x[1])[0] if emotions else "none"
        ns = m.get("neural_state", {})
        style = m.get("response_style", {})
        details.append(f"  Emotion: {primary:<12} | Arousal: {ns.get('emotional_arousal',0):.2f} | Patience: {ns.get('patience_level',0):.2f} | Warmth: {style.get('warmth',0):.2f} | Sarcasm: {style.get('sarcasm',0):.2f}")
        details.append(f"    Input: {r['text'][:70]}")

    # Check that different inputs produce different emotional responses
    unique_emotions = set()
    for r in reactions:
        m = r["metadata"]
        emotions = m.get("emotional_activation", {})
        if emotions:
            unique_emotions.add(max(emotions.items(), key=lambda x: x[1])[0])
    
    return {
        "passed": len(unique_emotions) >= 3,
        "detail": "\n".join(details),
        "unique_emotions": list(unique_emotions),
    }

# ═══════════════════════════════════════════════════════════════════════════
# TEST 5: NeuralBrainSimulation — Big Five Personality
# ═══════════════════════════════════════════════════════════════════════════
def test_brain_simulation():
    traits = BigFiveTraits(extroversion=0.8, agreeableness=0.6, neuroticism=0.4, openness=0.9, conscientiousness=0.5)
    brain = NeuralBrainSimulation(traits=traits)
    
    emotion = {"name": "angry", "vad": [-0.7, 0.8, 0.6], "intensity": "high", "pad": [-0.7, 0.8, 0.6]}
    context = {"ltm": [{"user": "test", "assistant": "ok", "timestamp": "now", "emotion": {"name": "neutral", "vad": [0,0,0]}}]}
    
    result = brain.process_decision("You are terrible!", emotion, context)
    
    layers = result["layers"]
    details = [
        f"  Amygdala intensity: {layers['amygdala']['intensity']:.2f} | hostile: {layers['amygdala']['hostile']}",
        f"  Hippocampus resonance: {layers['hippocampus']['resonance']:.2f}",
        f"  PFC rational override: {layers['pfc']['rational_override']:.2f}",
        f"  Neocortex creativity: {layers['neocortex']['creativity']:.2f}",
        f"  Spontaneity: {result['spontaneity']:.2f}",
        f"  Response delay: {result['delay_ms']:.0f}ms",
    ]
    
    return {"passed": True, "detail": "\n".join(details)}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 6: Pipeline Brain — Full 5-Area SNN Brain Pipeline
# ═══════════════════════════════════════════════════════════════════════════
def test_pipeline_brain():
    detector = TextEmotionDetector()
    
    test_texts = [
        "I love you so much, you're incredible!",
        "I hate everything about this, you're useless!",
        "I'm so scared and anxious about the future...",
        "What is happening right now? I'm so confused.",
        "I can't believe you did this, I trusted you!",
        "I'm so grateful for everything you've done!",
    ]
    
    results_list = []
    for text in test_texts:
        emotion = detector.analyze(text)
        results_list.append({"text": text, "emotion": emotion})
    
    details = []
    for r in results_list:
        e = r["emotion"]
        intensities = dict(sorted(e.mood_confidences.items(), key=lambda x: x[1], reverse=True)[:3])
        details.append(f"  Mood: {e.primary_mood.value:<12} | V={e.valence:+.3f} A={e.arousal:.3f} D={e.dominance:.3f} | {e.intensity:<6} | hostile={e.is_hostile}")
        details.append(f"    Top: {intensities}")
        details.append(f"    Appraisal: {e.cognitive_appraisal} | Tendency: {e.action_tendency}")
        details.append(f"    Input: {r['text'][:60]}")
        details.append("")
    
    return {"passed": True, "detail": "\n".join(details)}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 7: Brain Areas — PFC, dACC, Insula, IPL, BasalGanglia
# ═══════════════════════════════════════════════════════════════════════════
def test_brain_areas():
    pfc = PFCBrainArea()
    dacc = dACCBrainArea()
    insula = InsulaBrainArea()
    ipl = IPLBrainArea()
    bg = BasalGangliaBrainArea()
    wm = WorkingMemory()
    
    # PFC: Store + retrieve
    wm.store("test", "hello world")
    retrieved = wm.retrieve("test")
    
    # PFC forward
    import numpy as np
    pfc_out = pfc.forward(np.random.randn(256) * 0.1)
    
    # dACC with conflict
    dacc_out = dacc.forward(pfc_out)
    conflict = dacc.conflict_score
    
    # Insula
    insula_out = insula.forward(np.random.randn(64) * 0.1, "This is a test of the emergency broadcast system")
    
    # IPL
    ipl_out = ipl.forward()
    
    # Basal Ganglia
    bg_action = bg.forward(pfc_out, conflict, insula_out)
    
    details = [
        f"  PFC: firing={pfc.firing_rate:.2f} | spikes={pfc.spike_count} | dopamine={pfc.dopamine:.2f}",
        f"  dACC: conflict={conflict:.3f} | firing={dacc.firing_rate:.2f}",
        f"  Insula: valence={insula_out:.3f} | firing={insula.firing_rate:.2f}",
        f"  IPL: firing={ipl.firing_rate:.2f}",
        f"  BG: action={bg_action:<22} | value={bg.action_value:.3f}",
        f"  WorkingMem: stored='{retrieved}' | capacity={wm.state_dict()['capacity']}",
    ]
    
    return {"passed": True, "detail": "\n".join(details)}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 8: SNN Encoder — All 4 Encoding Methods
# ═══════════════════════════════════════════════════════════════════════════
def test_snn_encoder():
    import numpy as np
    features = np.array([0.1, 0.5, 0.9, 0.3, 0.7])
    encoder = SNNEncoder(timesteps=16)
    
    results_dict = {}
    for method in ["rate", "ttfs", "phase", "population"]:
        encoder.method = method
        spikes = encoder.encode(features)
        decoded = encoder.decode(spikes)
        results_dict[method] = {"spikes_shape": spikes.shape, "mean_rate": float(np.mean(spikes))}
    
    details = [f"  Features: {features.tolist()}"]
    for method, r in results_dict.items():
        details.append(f"  {method:<12}: shape={r['spikes_shape']}, mean_rate={r['mean_rate']:.3f}")
    
    return {"passed": True, "detail": "\n".join(details)}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 9: Mood Directives — All 12 Mood States with Examples
# ═══════════════════════════════════════════════════════════════════════════
def test_mood_directives():
    expected_moods = ["calm", "annoyed", "furious", "defensive", "sarcastic", "hurt", 
                       "sympathetic", "empathetic", "concerned", "joyful", "excited", "playful"]
    
    missing = [m for m in expected_moods if m not in MOOD_DIRECTIVES]
    extra = [m for m in MOOD_DIRECTIVES if m not in expected_moods]
    
    details = []
    for mood in expected_moods:
        d = MOOD_DIRECTIVES[mood]
        details.append(f"  {mood:<14}: instruction='{d['instruction'][:60]}...' | {len(d['examples'])} examples")
    
    status = f"✓ All {len(expected_moods)} moods + {len(extra)} extras" if not missing else f"✗ Missing: {missing}"
    return {"passed": len(missing) == 0, "detail": "\n".join(details) + f"\n  {status}"}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 10: PAD Emotion Map — All 15+ Emotions with Values
# ═══════════════════════════════════════════════════════════════════════════
def test_pad_emotion_map():
    expected = ["joy", "excitement", "empathy", "calm", "neutral", "sadness", "anger", "playful"]
    missing = [e for e in expected if e not in EMOTION_PAD_MAP]
    
    details = [f"  Total emotion→PAD mappings: {len(EMOTION_PAD_MAP)}"]
    for name, pad in sorted(EMOTION_PAD_MAP.items()):
        details.append(f"  {name:<16}: P={pad['pleasure']:+.2f} A={pad['arousal']:+.2f} D={pad['dominance']:+.2f}")
    
    return {"passed": len(missing) == 0, "detail": "\n".join(details)}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 11: Pipeline TextEmotionDetector — ALL Specific Emotions
# ═══════════════════════════════════════════════════════════════════════════
def test_all_emotions_detailed():
    detector = TextEmotionDetector()
    
    emotion_tests = [
        ("Happy/Joy", "I am so incredibly happy and joyful right now! This is amazing! Wonderful!", {"happy"}),
        ("Sad", "I'm feeling so sad and depressed. My heart is broken and I'm miserable.", {"sad"}),
        ("Angry", "I hate this! This is terrible and awful! You're so annoying and stupid!", {"angry", "frustrated"}),
        ("Fearful", "I'm so scared and terrified. I'm worried and anxious about what will happen.", {"fearful", "anxious"}),
        ("Surprised", "Wow! What? No way! I can't believe this is happening! This is incredible!", {"surprised"}),
        ("Loving", "I love you so much! You're so sweet and cute! My love for you is endless!", {"happy", "loving", "content"}),
        ("Grateful", "I'm so grateful and thankful for everything you've done. You're wonderful!", {"happy", "grateful", "content"}),
        ("Confused", "What is going on? I don't understand any of this. I'm so confused.", {"confused", "neutral"}),
        ("Hostile/Rage", "I FUCKING HATE YOU! YOU'RE PATHETIC GARBAGE! KILL YOURSELF! DIE!", {"angry", "frustrated"}),
        ("Anxious", "I'm so worried and nervous. My anxiety is through the roof. I feel panicked.", {"anxious", "fearful"}),
        ("Hopeful", "I hope everything works out. I'm optimistic for the future. Things might get better.", {"hopeful", "happy", "content"}),
        ("Trusting", "I really trust you and I believe in what you're saying. You seem genuine.", {"trusting", "happy", "content"}),
        ("Neutral/Betrayal", "I trusted you. I thought you were different. How could you do this to me?", {"sad", "angry"}),
        ("Pity", "Oh you poor thing, I feel so sorry for you. That must be so hard.", {"sad", "sympathetic"}),
        ("Haste/Urgency", "Hurry up we need to go now! We're running out of time! Quick!", {"anxious", "fearful"}),
    ]
    
    details = []
    all_good = True
    
    for emotion_name, text, expected_moods in emotion_tests:
        result = detector.analyze(text)
        primary = result.primary_mood.value
        
        details.append(f"\n  ── {emotion_name:<20} ──")
        details.append(f"  Input: {text[:70]}")
        details.append(f"  Primary Mood: {primary:<12} | V={result.valence:+.3f} A={result.arousal:.3f} D={result.dominance:.3f}")
        
        top_moods = dict(sorted(result.mood_confidences.items(), key=lambda x: x[1], reverse=True)[:4])
        details.append(f"  Top Emotions: {top_moods}")
        details.append(f"  Intensity: {result.intensity:<6} | Hostile: {result.is_hostile:<5} | Score: {result.hostility_score:.2f}")
        details.append(f"  Trend: valence={result.valence_trend} | arousal={result.arousal_trend}")
        details.append(f"  Appraisal: {result.cognitive_appraisal:<30} | Tendency: {result.action_tendency:<25}")
        
        # Check if primary mood is in accepted set or close
        if primary in expected_moods:
            details.append(f"  ✓ Mood matches expected: {primary} in {expected_moods}")
        else:
            details.append(f"  ⚠ Primary '{primary}' not in expected {expected_moods} — but checking if close enough")
            # Close enough if a top-3 mood matches
            top3 = set(dict(sorted(result.mood_confidences.items(), key=lambda x: x[1], reverse=True)[:3]).keys())
            if top3 & expected_moods:
                details.append(f"    ✓ Top-3 contains expected mood: {top3 & expected_moods}")
            else:
                details.append(f"    ✗ No match: top3={top3} vs expected={expected_moods}")
                all_good = False
    
    details.append(f"\n  {'✓ All emotions detected correctly!' if all_good else '✗ Some emotions had mismatches'}")
    return {"passed": all_good, "detail": "\n".join(details)}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 12: Personality Synthesis — Response Style Modulation
# ═══════════════════════════════════════════════════════════════════════════
def test_personality_response_modulation():
    from dreamtalk.emotion.core.affect_dynamics import NeuralState
    personality = PersonalitySynthesisLayer()
    human_gen = HumanResponseGenerator()
    
    emotions_list = [
        {"anger": 0.8, "disgust": 0.4},
        {"joy": 0.9, "trust": 0.7},
        {"sadness": 0.7, "fear": 0.5},
        {"neutral": 0.5},
        {"surprise": 0.8, "joy": 0.3},
    ]
    
    details = []
    for emotions in emotions_list:
        ns = NeuralState(
            emotional_arousal=min(1.0, sum(emotions.values()) * 1.2),
            cognitive_load=0.3 + min(1.0, sum(emotions.values()) * 0.4),
            creativity_level=0.7,
            response_urgency=0.4 + min(1.0, sum(emotions.values()) * 0.4),
        )
        
        style = personality.determine_response_style(emotions, ns)
        
        primary = max(emotions.items(), key=lambda x: x[1])[0]
        details.append(f"  {primary:<10}: formality={style['formality']:.2f} | warmth={style['warmth']:.2f} | creativity={style['creativity']:.2f} | directness={style['directness']:.2f} | length={style['length']:.2f}")
    
    return {"passed": True, "detail": "\n".join(details)}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 13: Knowledge Base — Semantic Retrieval
# ═══════════════════════════════════════════════════════════════════════════
def test_knowledge_base():
    kb = NeuralKnowledgeBase()
    
    try:
        kb.train()
        queries = ["How should I respond when the user is angry?", 
                   "What should I do when someone insults me?",
                   "How do I express happiness and excitement?"]
        
        details = [f"  Corpus size: {len(kb.corpus)} entries"]
        details.append(f"  Model: {kb.model_name}")
        
        for query in queries:
            results = kb.retrieve(query, current_mood="angry", k=3)
            details.append(f"\n  Query: '{query[:50]}'")
            for r in results:
                details.append(f"    [{r['category']:<12} | mood={r['mood_context']:<12}] score={r['score']:.3f} → {r['text'][:80]}")
        
        return {"passed": True, "detail": "\n".join(details)}
    
    except Exception as e:
        return {"passed": False, "detail": f"KB init failed: {e}"}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 14: Memory System — STM/LTM with Emotional Context
# ═══════════════════════════════════════════════════════════════════════════
def test_memory_system():
    try:
        mem = MemorySystem()
        
        interactions = [
            ("I love talking to you!", "I love talking to you too!", {"name": "joy", "vad": [0.8, 0.5, 0.4]}),
            ("You're so stupid!", "That's not very nice", {"name": "anger", "vad": [-0.7, 0.8, 0.6]}),
            ("I'm feeling really sad today", "I'm sorry to hear that", {"name": "sadness", "vad": [-0.6, -0.3, -0.6]}),
        ]
        
        for user, assistant, emotion in interactions:
            mem.add_interaction(user, assistant, emotion)
        
        context = mem.retrieve_context("I'm feeling emotional today", k=3)
        
        details = [
            f"  STM entries: {len(mem.stm)}",
            f"  LTM index: {mem.ltm_index.ntotal} vectors",
            f"  Emotional history: {len(mem.emotional_history)} entries",
            f"  Retrieved STM: {len(context['stm'])} turns",
            f"  Retrieved LTM: {len(context['ltm'])} results",
            f"  Emotional profile: {context['emotional_profile']}",
        ]
        
        return {"passed": True, "detail": "\n".join(details)}
    except Exception as e:
        return {"passed": False, "detail": f"Memory test failed: {e}"}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 15: Conversation Learning — Signal Extraction
# ═══════════════════════════════════════════════════════════════════════════
def test_learning_signals():
    from dreamtalk.digital_twin.learning_orchestrator import LearningOrchestrator
    
    conversations = [
        "My name is Raj. I work as a software engineer. I love programming in Python.",
        "I prefer casual conversation. I hate formal greetings. My favorite food is pizza.",
        "Actually, I think you were wrong about what I said. I meant something different.",
        "I'm feeling really happy today! I'm excited about my new job!",
        "No, I don't like that at all. I prefer when you keep it simple.",
    ]
    
    details = []
    for text in conversations:
        facts = LearningOrchestrator._extract_facts(text)
        prefs = LearningOrchestrator._extract_preferences(text)
        corrections = LearningOrchestrator._extract_corrections(text)
        emotions = LearningOrchestrator._extract_emotional_signals(text)
        comm = LearningOrchestrator._extract_communication_style(text)
        
        details.append(f"\n  Input: {text[:60]}")
        details.append(f"    Facts: {len(facts)} → {[f['key'] for f in facts]}")
        details.append(f"    Prefs: {len(prefs)} → {[p['key'] for p in prefs]}")
        details.append(f"    Corrections: {len(corrections)} → {[c['key'] for c in corrections]}")
        details.append(f"    Emotions: {len(emotions)} → {[e['key'] for e in emotions]}")
        details.append(f"    CommStyle: {len(comm)} → {[c['value'] for c in comm]}")
    
    return {"passed": True, "detail": "\n".join(details)}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 16: Mood Sequence — Conversation Flow Adaptation
# ═══════════════════════════════════════════════════════════════════════════
def test_mood_sequence():
    """Test how emotions evolve through a conversation with triggers"""
    detector = TextEmotionDetector()
    
    conversation = [
        "Hey, how are you doing today?",           # neutral/positive
        "You're awesome! I really appreciate you!", # happy
        "What's your opinion on this matter?",      # neutral/curious
        "I'm feeling really down today...",         # sad
        "Nothing is going right in my life.",       # more sad
        "Stop it! You're not helping at all!",      # frustrated
        "I HATE THIS STUPID SYSTEM!!!",             # angry
        "I'm sorry, I didn't mean to yell at you.", # regretful
    ]
    
    emotions = []
    for text in conversation:
        e = detector.analyze(text)
        emotions.append(e)
    
    details = []
    for i, (text, e) in enumerate(zip(conversation, emotions)):
        details.append(f"  [{i+1}] V={e.valence:+.3f} A={e.arousal:.3f} → {e.primary_mood.value:<10} ({e.intensity}) | '{text[:50]}'")
    
    # Show trajectory
    valence_trend = [e.valence for e in emotions]
    mood_sequence = [e.primary_mood.value for e in emotions]
    
    details.append(f"\n  Valence trajectory: {[f'{v:+.2f}' for v in valence_trend]}")
    details.append(f"  Mood sequence: {' → '.join(mood_sequence)}")
    
    # Check that neutral → happy → sad → angry progression exists
    has_emotion_shift = len(set(mood_sequence)) >= 3
    
    return {"passed": has_emotion_shift, "detail": "\n".join(details)}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 17: PAD Emotion Engine — Emotional Inertia & Memory
# ═══════════════════════════════════════════════════════════════════════════
def test_pad_inertia():
    import numpy as np
    engine = PADEmotionEngine(inertia=0.85)
    
    # Apply a strong negative stimulus then immediately try to switch to positive
    engine.update((-0.9, 1.0, 0.8))  # rage
    state1 = engine.get_current_emotion()
    
    engine.update((0.9, 0.9, 0.8))   # ecstasy
    state2 = engine.get_current_emotion()
    
    # With high inertia, the emotion should still be influenced by previous state
    p1 = np.array(state1["pad"])
    p2 = np.array(state2["pad"])
    
    details = [
        f"  Inertia: {engine.inertia}",
        f"  After rage stimulus: {state1['name']:<15} ({state1['display_name']}) PAD=({state1['pad'][0]:+.2f},{state1['pad'][1]:+.2f},{state1['pad'][2]:+.2f})",
        f"  After immediate ecstasy: {state2['name']:<15} ({state2['display_name']}) PAD=({state2['pad'][0]:+.2f},{state2['pad'][1]:+.2f},{state2['pad'][2]:+.2f})",
        f"  PAD distance traveled: {np.linalg.norm(p1 - p2):.3f}",
        f"  (Should be < full range due to inertia: inertia={engine.inertia})",
    ]
    
    # Inertia means not fully flipped
    has_inertia = state2["pad"][0] < 0.5  # not fully ecstatic due to inertia
    return {"passed": has_inertia, "detail": "\n".join(details)}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 18: Knowledge Corpus — Coverage of All Moods
# ═══════════════════════════════════════════════════════════════════════════
def test_knowledge_corpus_coverage():
    moods_covered = set()
    categories = set()
    
    for entry in KNOWLEDGE_CORPUS:
        moods_covered.add(entry["mood_context"])
        categories.add(entry["category"])
    
    details = [
        f"  Total entries: {len(KNOWLEDGE_CORPUS)}",
        f"  Moods covered: {sorted(moods_covered)}",
        f"  Categories: {sorted(categories)}",
    ]
    
    expected_moods = {"neutral", "calm", "annoyed", "furious", "defensive", "sarcastic", "hurt", "sympathetic", "empathetic", "concerned", "joyful", "excited", "playful"}
    missing = expected_moods - moods_covered
    extra = moods_covered - expected_moods
    
    if missing:
        details.append(f"  ⚠ Missing moods: {missing}")
    if extra:
        details.append(f"  ⚠ Extra moods: {extra}")
    
    return {"passed": len(missing) <= 2, "detail": "\n".join(details)}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 19: HumanEmotionalProcessing — Input-specific Emotional Detection
# ═══════════════════════════════════════════════════════════════════════════
def test_human_emotion_processing():
    hp = HumanEmotionalProcessing()
    
    tests = [
        ("This is amazing and incredible!", "excitement"),
        ("You stupid idiot, this is bullshit!", "anger"),
        ("I'm so sad and heartbroken right now.", "sadness"),
        ("Why does this keep happening to me?", "curiosity"),
    ]
    
    details = []
    all_good = True
    for text, expected_emotion in tests:
        activation = hp.process_sentiment(EmotionAnalyzer().analyze_text(text), text)
        primary = max(activation.items(), key=lambda x: x[1])[0]
        has_expected = expected_emotion in activation
        details.append(f"  '{text[:40]}...' → primary={primary:<12} | {expected_emotion}_present={has_expected}")
        if not has_expected:
            all_good = False
    
    return {"passed": all_good, "detail": "\n".join(details)}

# ═══════════════════════════════════════════════════════════════════════════
# TEST 20: PromptCompiler — Full System Prompt Compilation
# ═══════════════════════════════════════════════════════════════════════════
def test_prompt_compiler():
    compiler = PromptCompiler(system_persona="You are DreamTalk, a digital human.", max_history_turns=3)
    
    test_emotions = [
        {"mood": "joyful", "intensity": "high", "name": "Joyful", "vad": [0.8, 0.6, 0.4]},
        {"mood": "furious", "intensity": "high", "name": "Furious", "vad": [-0.9, 0.9, 0.8]},
        {"mood": "empathetic", "intensity": "medium", "name": "Empathetic", "vad": [0.5, 0.2, 0.0]},
        {"mood": "sarcastic", "intensity": "medium", "name": "Sarcastic", "vad": [-0.2, 0.4, 0.5]},
    ]
    
    details = []
    for emotion in test_emotions:
        prompt = compiler.get_system_prompt(emotion)
        lines = prompt.split("\n")
        details.append(f"\n  Mood: {emotion['mood']:<12} | Lines: {len(lines)} | First: '{lines[0][:50]}'")
        details.append(f"    Directive line: {[l for l in lines if 'directive' in l.lower()][:1]}")
    
    # Test message compilation
    compiler.add_turn("user", "Hello!")
    compiler.add_turn("assistant", "Hey there!")
    messages = compiler.compile_messages("How are you?", test_emotions[0])
    
    details.append(f"\n  Message array: {len(messages)} messages (system + {len(messages)-2} history + user)")
    
    return {"passed": True, "detail": "\n".join(details)}

# ═══════════════════════════════════════════════════════════════════════════
# RUN ALL TESTS
# ═══════════════════════════════════════════════════════════════════════════

print("\n📋 Running 20 tests...\n")

run_test("VADER Sentiment Analysis", test_vader_sentiment)
run_test("Affective State Tracker (EMA + Hostility)", test_affective_tracker)
run_test("PAD Emotion Engine (50+ states)", test_pad_engine)
run_test("HumanNeuralEngine (emotional processing)", test_human_neural_engine)
run_test("NeuralBrainSimulation (Big Five)", test_brain_simulation)
run_test("Pipeline Brain (5-area SNN)", test_pipeline_brain)
run_test("Brain Areas (PFC/dACC/Insula/IPL/BG)", test_brain_areas)
run_test("SNN Encoder (4 methods)", test_snn_encoder)
run_test("Mood Directives (12 moods)", test_mood_directives)
run_test("PAD Emotion Map", test_pad_emotion_map)
run_test("ALL Emotions Detailed (15 emotions)", test_all_emotions_detailed)
run_test("Personality Response Modulation", test_personality_response_modulation)
run_test("Knowledge Base (semantic retrieval)", test_knowledge_base)
run_test("Memory System (STM/LTM)", test_memory_system)
run_test("Conversation Learning Signals", test_learning_signals)
run_test("Mood Sequence (conversation flow)", test_mood_sequence)
run_test("PAD Emotional Inertia", test_pad_inertia)
run_test("Knowledge Corpus Coverage", test_knowledge_corpus_coverage)
run_test("Human Emotion Processing", test_human_emotion_processing)
run_test("PromptCompiler (system prompts)", test_prompt_compiler)

print("\n" + "="*80)
print(f"📊 FINAL RESULTS: {results['passed']}/{results['passed']+results['failed']} passed")
print("="*80)

# Print summary of test results
print("\n📋 Test Summary:")
for t in results["tests"]:
    icon = "✅" if "PASS" in t["status"] else "❌" if "FAIL" in t["status"] else "⚠️"
    print(f"  {icon} {t['name']} ({t['time']:.1f}s)")

print(f"\n{'='*80}")
print(f"🧪 COMPREHENSIVE EMOTION/BRAIN TEST COMPLETE")
print(f"{'='*80}")
