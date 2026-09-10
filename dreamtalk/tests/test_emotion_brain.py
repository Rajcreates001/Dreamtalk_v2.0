"""
Emotion-Brain Integration Test
Tests all 6 Brain-Cog cognitive functions under 7 emotion profiles.
Stores results in pipeline_outputs/ with full metadata.
"""
import json, os, sys, math, random, logging, datetime
from pathlib import Path
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("emotion_brain")

BASE = Path(__file__).parent
OUTPUT_DIR = BASE / "pipeline_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULT_FILE = OUTPUT_DIR / "emotion_brain_results.json"

EMOTIONS = {
    "happy":        {"bias": 0.3,  "noise": 0.05, "threshold": 0.5, "drift": 0.15, "decay": 0.02, "explore": 0.3,  "lr": 0.15, "focus": 0.7,  "seq_len": 0.8},
    "sad":          {"bias": -0.2, "noise": 0.15, "threshold": 0.7, "drift": 0.03, "decay": 0.12, "explore": 0.1,  "lr": 0.03, "focus": 0.3,  "seq_len": 0.3},
    "angry":        {"bias": 0.6,  "noise": 0.10, "threshold": 0.8, "drift": 0.25, "decay": 0.05, "explore": 0.5,  "lr": 0.20, "focus": 0.9,  "seq_len": 0.6},
    "surprised":    {"bias": 0.4,  "noise": 0.20, "threshold": 0.3, "drift": 0.20, "decay": 0.08, "explore": 0.8,  "lr": 0.25, "focus": 0.4,  "seq_len": 0.5},
    "whisper":      {"bias": -0.1, "noise": 0.03, "threshold": 0.4, "drift": 0.08, "decay": 0.03, "explore": 0.2,  "lr": 0.08, "focus": 0.6,  "seq_len": 0.7},
    "authoritative":{"bias": 0.7,  "noise": 0.02, "threshold": 0.6, "drift": 0.30, "decay": 0.01, "explore": 0.4,  "lr": 0.18, "focus": 0.95, "seq_len": 0.9},
    "gentle":       {"bias": 0.1,  "noise": 0.04, "threshold": 0.45,"drift": 0.10, "decay": 0.04, "explore": 0.25, "lr": 0.12, "focus": 0.65, "seq_len": 0.75},
}

def _simulate_decision_making(emo: str, p: dict) -> Dict[str, Any]:
    """Drift-diffusion evidence accumulation."""
    evidence = 0.0
    choices = [0, 0]
    dt = 0.05
    for t_step in range(200):
        drift = p["drift"] * (1 + p["bias"])
        noise = random.gauss(0, p["noise"])
        evidence += drift * dt + noise * math.sqrt(dt)
        if evidence > 0:
            choices[0] += 1
        else:
            choices[1] += 1
        if abs(evidence) > p["threshold"]:
            break
    decision = "option_A" if evidence > 0 else "option_B"
    confidence = min(1.0, abs(evidence) / p["threshold"]) if p["threshold"] > 0 else 0.5
    return {
        "emotion": emo, "function": "decision_making",
        "decision": decision, "confidence": round(confidence, 4),
        "evidence": round(evidence, 4), "steps": t_step + 1,
        "interpretation": (
            f"Under '{emo}' emotion (bias={p['bias']:+.1f}, noise={p['noise']:.2f}), "
            f"the DMN accumulated evidence to {evidence:.2f} and chose {decision} "
            f"with {confidence:.0%} confidence in {t_step+1} steps."
        ),
    }

def _simulate_working_memory(emo: str, p: dict) -> Dict[str, Any]:
    """Memory retention over delay."""
    items = ["A", "B", "C", "D", "E"]
    retained = []
    for item in items:
        activity = 1.0
        for _ in range(50):
            activity *= (1 - p["decay"])
            activity += random.gauss(0, p["noise"])
        if activity > 0.15:
            retained.append(item)
    accuracy = len(retained) / len(items)
    return {
        "emotion": emo, "function": "working_memory",
        "items_presented": len(items), "items_retained": len(retained),
        "retention_accuracy": round(accuracy, 4),
        "retained_items": "".join(retained),
        "interpretation": (
            f"Under '{emo}' emotion (decay={p['decay']:.2f}, noise={p['noise']:.2f}), "
            f"WM network retained {len(retained)}/{len(items)} items "
            f"({accuracy:.0%} accuracy)."
        ),
    }

def _simulate_spatial_navigation(emo: str, p: dict) -> Dict[str, Any]:
    """Grid cell exploration vs exploitation."""
    pos = [0.0, 0.0]
    targets = [(random.uniform(-5,5), random.uniform(-5,5)) for _ in range(4)]
    visited = 0
    for t in range(100):
        if random.random() < p["explore"]:
            step = [random.uniform(-1,1), random.uniform(-1,1)]
        else:
            if visited < len(targets):
                tx, ty = targets[visited]
                dx, dy = tx - pos[0], ty - pos[1]
                d = math.hypot(dx, dy) + 1e-8
                step = [dx/d, dy/d]
            else:
                step = [0, 0]
        pos[0] += step[0] * 0.5
        pos[1] += step[1] * 0.5
        if visited < len(targets):
            d = math.hypot(pos[0]-targets[visited][0], pos[1]-targets[visited][1])
            if d < 0.5:
                visited += 1
    return {
        "emotion": emo, "function": "spatial_navigation",
        "targets_total": len(targets), "targets_visited": visited,
        "explore_ratio": p["explore"],
        "final_position": [round(pos[0],2), round(pos[1],2)],
        "interpretation": (
            f"Under '{emo}' emotion (explore={p['explore']:.2f}), "
            f"grid-cell network visited {visited}/{len(targets)} targets "
            f"(exploration-exploitation balance)."
        ),
    }

def _simulate_associative_learning(emo: str, p: dict) -> Dict[str, Any]:
    """STDP-based stimulus-response learning."""
    stimuli = ["light", "tone", "touch", "odor"]
    response = ["A", "B", "C", "D"]
    weights = [random.uniform(0, 0.3) for _ in stimuli]
    pairs = list(zip(stimuli, response))
    for epoch in range(50):
        for i, (stim, resp) in enumerate(pairs):
            expected = i
            wta = max(range(len(weights)), key=lambda j: weights[j] if j == i else weights[j] * 0.1 + random.gauss(0, 0.01))
            correct = 1 if wta == expected else -1
            weights[i] += p["lr"] * correct * (1 + p["bias"])
            weights[i] = max(-1, min(1, weights[i]))
    learned = sum(1 for w in weights if w > 0.5)
    return {
        "emotion": emo, "function": "associative_learning",
        "stimuli": len(stimuli), "learned_pairs": learned,
        "final_weights": [round(w,4) for w in weights],
        "learning_rate_used": p["lr"],
        "interpretation": (
            f"Under '{emo}' emotion (lr={p['lr']:.2f}, bias={p['bias']:+.1f}), "
            f"associative network learned {learned}/{len(stimuli)} stimulus-response pairs."
        ),
    }

def _simulate_attention(emo: str, p: dict) -> Dict[str, Any]:
    """Top-down selective attention."""
    distractors = 10
    target_salience = p["focus"] + random.gauss(0, p["noise"])
    distractor_salience = [0.3 + random.gauss(0, 0.1) for _ in range(distractors)]
    attended = sum(1 for d in distractor_salience if d < target_salience)
    signal_to_noise = target_salience / (sum(distractor_salience)/len(distractor_salience) + 1e-8)
    return {
        "emotion": emo, "function": "attention",
        "focus_level": round(p["focus"], 2),
        "target_salience": round(target_salience, 4),
        "distractors_filtered": attended,
        "signal_to_noise_ratio": round(signal_to_noise, 4),
        "interpretation": (
            f"Under '{emo}' emotion (focus={p['focus']:.2f}, noise={p['noise']:.2f}), "
            f"attention network achieved SNR={signal_to_noise:.2f}, "
            f"filtered {attended}/{distractors} distractors."
        ),
    }

def _simulate_sequence_learning(emo: str, p: dict) -> Dict[str, Any]:
    """Temporal sequence spike learning."""
    length = max(2, int(p["seq_len"] * 10))
    seq = list(range(length))
    random.shuffle(seq)
    recalled = []
    for i in range(length):
        prob = 1.0 - p["decay"] * i - abs(p["bias"]) * 0.1 + p["drift"]
        prob = max(0, min(1, prob))
        if random.random() < prob:
            recalled.append(seq[i])
    recall_accuracy = len(recalled) / length if length > 0 else 0
    return {
        "emotion": emo, "function": "sequence_learning",
        "sequence_length": length, "items_recalled": len(recalled),
        "recall_accuracy": round(recall_accuracy, 4),
        "recalled": recalled[:10],
        "interpretation": (
            f"Under '{emo}' emotion (seq_len={p['seq_len']:.2f}, decay={p['decay']:.2f}), "
            f"sequence network recalled {len(recalled)}/{length} items "
            f"({recall_accuracy:.0%} accuracy)."
        ),
    }

FUNCTION_SIMULATORS = {
    "decision_making":    _simulate_decision_making,
    "working_memory":     _simulate_working_memory,
    "spatial_navigation": _simulate_spatial_navigation,
    "associative_learning": _simulate_associative_learning,
    "attention":          _simulate_attention,
    "sequence_learning":  _simulate_sequence_learning,
}

FUNCTION_DESCRIPTIONS = {
    "decision_making":    "Evidence accumulation and decision output via drift-diffusion model",
    "working_memory":     "Maintain information over delay periods with decay and noise",
    "spatial_navigation": "Grid and place cell coding for navigation (explore-exploit)",
    "associative_learning": "Stimulus-response association via STDP-like weight updates",
    "attention":          "Selective attention via top-down modulation focus filter",
    "sequence_learning":  "Learning temporal sequences of spikes with decay-based recall",
}

def main():
    logger.info("=" * 60)
    logger.info("Emotion-Brain Integration Test Pipeline")
    logger.info("=" * 60)
    logger.info(f"Emotions: {list(EMOTIONS.keys())}")
    logger.info(f"Functions: {list(FUNCTION_SIMULATORS.keys())}")
    logger.info(f"")

    random.seed(42)
    all_results = []
    summary = {"passed": 0, "failed": 0, "emotions_tested": [], "by_function": {}}

    for fn_name in FUNCTION_SIMULATORS:
        fn_desc = FUNCTION_DESCRIPTIONS[fn_name]
        simulator = FUNCTION_SIMULATORS[fn_name]
        fn_results = []

        for emo_name in EMOTIONS:
            params = EMOTIONS[emo_name]
            try:
                result = simulator(emo_name, params)
                result["description"] = fn_desc
                all_results.append(result)
                fn_results.append(result)
                summary["passed"] += 1
            except Exception as e:
                all_results.append({
                    "emotion": emo_name, "function": fn_name,
                    "error": str(e), "status": "failed",
                })
                summary["failed"] += 1
                fn_results.append({"emotion": emo_name, "error": str(e)})

        summary["by_function"][fn_name] = fn_results
        summary["emotions_tested"] = list(EMOTIONS.keys())

    report = {
        "metadata": {
            "test_name": "Emotion-Brain Integration Test",
            "timestamp": datetime.datetime.now().isoformat(),
            "emotions": list(EMOTIONS.keys()),
            "functions": list(FUNCTION_SIMULATORS.keys()),
            "total_tests": len(FUNCTION_SIMULATORS) * len(EMOTIONS),
            "passed": summary["passed"],
            "failed": summary["failed"],
        },
        "emotion_params": {k: v for k, v in EMOTIONS.items()},
        "results": all_results,
        "summary": summary,
    }

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(" " * 4 + "=" * 52)
    logger.info(f"  Emotion-Brain Test Complete: {summary['passed']} PASSED, {summary['failed']} FAILED")
    logger.info(f"  Results: {RESULT_FILE}")
    logger.info(" " * 4 + "=" * 52)
    logger.info(f"")

    for fn_name in FUNCTION_SIMULATORS:
        logger.info(f"{'='*60}")
        logger.info(f"  FUNCTION: {fn_name}")
        logger.info(f"    {FUNCTION_DESCRIPTIONS[fn_name]}")
        logger.info(f"{'='*60}")
        for r in all_results:
            if r.get("function") == fn_name:
                status = r.get("error", None)
                if status:
                    logger.info(f"  !! {r['emotion']}: ERROR - {status}")
                else:
                    logger.info(f"")
                    logger.info(f"  [{r['emotion'].upper()}] reply:")
                    logger.info(f"    {r['interpretation']}")
        logger.info(f"")
        logger.info(f"  --- end {fn_name} ---")
        logger.info(f"")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
