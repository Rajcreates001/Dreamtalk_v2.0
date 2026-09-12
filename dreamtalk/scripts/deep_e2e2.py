"""DreamTalk deep E2E, part 2: languages, emotions, brain memory, persistence.

Reuses the profile created by deep_e2e.py (state.json).
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deep_e2e import (  # noqa: E402
    OUT, req, rec, results, asset, speaker_features, cos, VOICE, load_state,
)

SHORT = {
    "hi": "Namaste, aap kaise hain?", "bn": "নমস্কার, আপনি কেমন আছেন?",
    "ta": "வணக்கம், எப்படி இருக்கிறீர்கள்?", "te": "నమస్కారం, ఎలా ఉన్నారు?",
    "kn": "ನಮಸ್ಕಾರ, ಹೇಗಿದ್ದೀರಿ?", "ml": "നമസ്കാരം, സുഖമാണോ?",
    "mr": "नमस्कार, तुम्ही कसे आहात?", "gu": "નમસ્તે, કેમ છો?",
    "pa": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ?", "or": "ନମସ୍କାର, ଆପଣ କେମିତି ଅଛନ୍ତି?",
    "as": "নমস্কাৰ, আপুনি কেনে আছে?", "ur": "السلام علیکم، آپ کیسے ہیں؟",
    "sa": "नमस्ते, कथम् असि?", "ne": "नमस्ते, तपाईं कस्तो हुनुहुन्छ?",
    "kok": "नमस्कार, तूं कसो आसा?", "mai": "प्रणाम, अहाँ कोना छी?",
    "sd": "سلام، توهان ڪيئن آهيو؟", "ks": "آداب، تُہہِ چھِوٕ کِتھ پاٹھؠ؟",
    "doi": "नमस्कार, तुस कि’यां ओ?", "brx": "खुलुमबाइ, नों माबोरै दं?",
    "mni": "খুরুমজরি, নহাক করম্না লৈরিবগে?", "sat": "ᱡᱚᱦᱟᱨ, ᱟᱢ ᱪᱮᱫ ᱞᱮᱠᱟ ᱢᱮᱱᱟᱢᱟ?",
    "en": "Hello, how are you?",
}


def phase5(s):
    print("\n=== PHASE 5 — all 22 scheduled languages + English ===")
    token, pid = s["token"], s["pid"]
    st, langs = req("GET", "/api/v1/avatar/languages")
    codes = sorted((langs or {}).get("languages", {}).keys())
    rec("languages advertised", len(codes) >= 23, f"{len(codes)}: {codes}")

    rows, cloned_n, ok_n = [], 0, 0
    for c in codes:
        text = SHORT.get(c, "Namaste.")
        t0 = time.time()
        st, r = req("POST", f"/api/v1/avatar/profiles/{pid}/respond", token=token, body={
            "message": text, "language": c, "synthesize": True,
            "render_video": False, "strict_clone": False,
        }, timeout=900)
        if st != 200 or not isinstance(r, dict):
            rows.append((c, "HTTP %s" % st, "-", 0, 0, 0.0))
            print(f"  {c:4s} FAIL HTTP {st}")
            continue
        a = r.get("audio") or {}
        lip = r.get("lipsync") or []
        dur = float(a.get("duration") or r.get("lipsync_duration") or 0)
        ok_n += 1
        cloned_n += bool(a.get("cloned"))
        rows.append((c, a.get("engine"), bool(a.get("cloned")), len(lip), round(dur, 1),
                     round(time.time() - t0, 1)))
        print(f"  {c:4s} engine={str(a.get('engine')):10s} cloned={str(bool(a.get('cloned'))):5s} "
              f"visemes={len(lip):3d} dur={dur:5.1f}s  {time.time()-t0:5.1f}s")

    json.dump(rows, open(os.path.join(OUT, "languages.json"), "w"), indent=1)
    rec("every language returns speech", ok_n == len(codes), f"{ok_n}/{len(codes)}")
    rec("every language returns visemes", all(r[3] > 0 for r in rows if r[1] != "-"),
        f"min visemes={min((r[3] for r in rows if r[1] != '-'), default=0)}")
    rec("cloned-voice coverage reported honestly", cloned_n > 0,
        f"{cloned_n}/{len(codes)} languages use the cloned voice; "
        f"the rest fall back and are flagged cloned=false")


EMOTIONS = ["neutral", "calm", "happy", "excited", "sad", "angry",
            "surprised", "fearful", "disgusted", "loving", "frustrated", "confused"]


def phase6(s):
    print("\n=== PHASE 6 — emotions (prosody actually measured) ===")
    token, pid = s["token"], s["pid"]
    import numpy as np
    stats = {}
    for emo in EMOTIONS:
        st, r = req("POST", f"/api/v1/avatar/profiles/{pid}/respond", token=token, body={
            "message": "Main aaj yahaan hoon.", "language": "hi", "emotion": emo,
            "synthesize": True, "render_video": False, "strict_clone": False,
        }, timeout=900)
        if st != 200:
            print(f"  {emo:11s} FAIL HTTP {st}")
            continue
        a = (r or {}).get("audio") or {}
        url = r.get("audio_url") or a.get("audio_url")
        dest = os.path.join(OUT, f"emo_{emo}.wav")
        if not asset(url, token, dest):
            print(f"  {emo:11s} FAIL download")
            continue
        _v, sfeat = speaker_features(dest)
        stats[emo] = sfeat
        print(f"  {emo:11s} emotion_out={str((r or {}).get('emotion')):11s} "
              f"f0={sfeat.get('f0_med'):6.1f}Hz rms={sfeat.get('rms'):.4f} dur={sfeat.get('dur'):.1f}s")

    rec("all emotions synthesize", len(stats) == len(EMOTIONS), f"{len(stats)}/{len(EMOTIONS)}")
    if len(stats) >= 3:
        f0 = [v["f0_med"] for v in stats.values()]
        rms = [v["rms"] for v in stats.values()]
        rec("prosody differs across emotions",
            (np.std(f0) > 1.0) or (np.std(rms) > 0.005),
            f"f0 spread={np.std(f0):.1f}Hz [{min(f0):.0f}-{max(f0):.0f}] "
            f"rms spread={np.std(rms):.4f}")
    json.dump(stats, open(os.path.join(OUT, "emotions.json"), "w"), indent=1)


def phase7(s):
    print("\n=== PHASE 7 — brain: conversational memory ===")
    token, pid = s["token"], s["pid"]
    secret = "My favourite colour is turquoise and my dog is called Bruno."
    turns = []

    def say(msg, history):
        st, r = req("POST", f"/api/v1/avatar/profiles/{pid}/respond", token=token, body={
            "message": msg, "language": "en", "history": history,
            "synthesize": False, "render_video": False, "strict_clone": False,
        }, timeout=900)
        txt = (r or {}).get("text") or (r or {}).get("response") or ""
        return st, txt

    st, a1 = say(secret, [])
    turns += [{"role": "user", "content": secret}, {"role": "assistant", "content": a1}]
    rec("turn 1 (state a fact)", st == 200 and bool(a1), a1[:90])

    st, a2 = say("What is my dog's name?", turns)
    turns += [{"role": "user", "content": "What is my dog's name?"},
              {"role": "assistant", "content": a2}]
    rec("turn 2 recalls the name (in-context)", "bruno" in a2.lower(), a2[:110])

    st, a3 = say("And what colour did I say I liked?", turns)
    rec("turn 3 recalls the colour (in-context)", "turquoise" in a3.lower(), a3[:110])

    # Server-side memory: ask again with NO history, so recall can only come
    # from the backend's own conversation memory, not the prompt.
    st, a4 = say("Do you remember my dog's name?", [])
    rec("turn 4 recalls with NO history (server-side memory)",
        "bruno" in a4.lower(), a4[:130])


def phase8(s):
    print("\n=== PHASE 8 — persistence: profile + assets survive ===")
    token, pid = s["token"], s["pid"]
    st, lst = req("GET", "/api/v1/avatar/profiles", token=token)
    profs = (lst or {}).get("profiles", []) if isinstance(lst, dict) else []
    mine = [p for p in profs if p.get("id") == pid]
    rec("profile listed for the user", bool(mine), f"{len(profs)} profile(s)")

    st, man = req("GET", f"/api/v1/avatar/profiles/{pid}/manifest", token=token)
    render = (man or {}).get("render", {}) if isinstance(man, dict) else {}
    urls = {k: render.get(k) for k in ("glb_url", "mesh_url", "texture_url", "primary_image_url")}
    rec("manifest returns asset URLs", all(urls.values()),
        ", ".join(f"{k}={'yes' if v else 'NO'}" for k, v in urls.items()))

    got = {}
    for k, u in urls.items():
        if not u:
            continue
        got[k] = asset(u, token, os.path.join(OUT, f"persist_{k}.bin"))
    rec("every stored asset re-downloads", all(v > 0 for v in got.values()),
        ", ".join(f"{k}={v/1024:.0f}KB" for k, v in got.items()))

    a = (mine[0].get("appearance") if mine else {}) or {}
    rec("blendshape names persisted on the profile",
        len(a.get("blendshape_names") or []) == 10,
        f"{a.get('blendshape_names')}")


PHASES = {"5": phase5, "6": phase6, "7": phase7, "8": phase8}

if __name__ == "__main__":
    state = load_state()
    if not state.get("pid"):
        sys.exit("no profile in state.json — run deep_e2e.py 1 first")
    for ph in (sys.argv[1:] or ["5", "6", "7", "8"]):
        PHASES[ph](state)
    print("\n" + "=" * 66)
    p = sum(1 for _, ok, _ in results if ok)
    print(f"SUMMARY: {p} passed, {len(results)-p} failed, {len(results)} total")
    for st, ok, d in results:
        if not ok:
            print(f"  FAIL {st}: {d}")
    print("=" * 66)
    sys.exit(0 if p == len(results) else 1)
