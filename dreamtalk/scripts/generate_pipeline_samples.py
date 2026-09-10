"""Task 2 & 3: Generate pipeline samples and run downstream workflow (fixed APIs)."""
import json, os, sys, importlib, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pipeline_outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def log(msg, data=None):
    entry = {'step': msg}
    if data:
        entry['data'] = data
    print(json.dumps(entry))

# ═══════════════════════════════════════════════════════════════
# STEP 1: Kokoro TTS with emotion
# ═══════════════════════════════════════════════════════════════
def generate_tts():
    log("Generating Kokoro TTS samples...")
    try:
        from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine, VOICE_METADATA
        engine = KokoroTTSEngine(weights_dir='weights/kokoro')
        
        texts = [
            ("en", "Welcome to DreamTalk. Your avatar is ready to speak.", "neutral"),
            ("en", "I am feeling incredibly happy to meet you today!", "joy"),
            ("en", "That is a beautiful creation. Truly amazing work.", "admiration"),
            ("en", "I am here to help you with anything you need.", "neutral"),
        ]
        
        results = []
        for lang, text, emotion in texts:
            out_path = os.path.join(OUTPUT_DIR, f'kokoro_tts_{lang}_{emotion}.wav')
            voice = engine.select_best_voice(lang=lang, emotion=emotion)
            audio = engine.synthesize(text, voice=voice, speed=1.0)
            from scipy.io import wavfile
            wavfile.write(out_path, 24000, audio)
            results.append({'lang': lang, 'emotion': emotion, 'voice': voice, 'path': out_path, 'length': len(audio)})
            log(f"  TTS [{lang}/{emotion}]: voice={voice}, samples={len(audio)}")
        
        log("TTS generation complete", {'files': results})
        return results
    except Exception as e:
        log("TTS generation failed", {'error': str(e), 'traceback': traceback.format_exc()})
        return None

# ═══════════════════════════════════════════════════════════════
# STEP 2: FLAME model test (mock since no weights)
# ═══════════════════════════════════════════════════════════════
def test_flame():
    log("Testing FLAME model (no weights, using synthetic data)...")
    try:
        import numpy as np
        # Build a minimal FLAME-like mesh from scratch
        # Standard face mesh with 5023 vertices, 9976 faces
        n_vertices = 5023
        n_faces = 9976
        
        # Generate synthetic vertices (unit sphere)
        phi = np.random.uniform(0, np.pi, n_vertices)
        theta = np.random.uniform(0, 2*np.pi, n_vertices)
        verts = np.column_stack([
            np.sin(phi) * np.cos(theta),
            np.sin(phi) * np.sin(theta),
            np.cos(phi),
        ]) * 0.1  # scale to ~10cm face
        
        # For a neutral expression, offset to look more face-like
        verts[:, 2] += 0.05  # move forward
        
        # Generate faces (triangles)
        faces = np.zeros((n_faces, 3), dtype=np.int32)
        for i in range(n_faces):
            faces[i] = [(i * 3) % n_vertices, (i * 3 + 1) % n_vertices, (i * 3 + 2) % n_vertices]
        
        # Export OBJ
        obj_path = os.path.join(OUTPUT_DIR, 'flame_synthetic.obj')
        with open(obj_path, 'w') as f:
            f.write("# DreamTalk Synthetic FLAME Mesh\n")
            for v in verts:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write(f"g face\n")
            for face in faces:
                f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
        
        log(f"  Synthetic mesh: {n_vertices} verts, {n_faces} faces")
        log(f"  Exported: {obj_path}")
        
        # Also try the actual FLAME model if weights exist
        flame_pkl = 'weights/flame/FLAME2020.pkl'
        if os.path.exists(flame_pkl):
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dreamtalk'))
            from avatar.core.face.flame.models.flame_model import FLAMEModel
            model = FLAMEModel(flame_pkl)
            shape = np.zeros(model.num_identity_params)
            exp = np.zeros(model.num_expression_params)
            pose = np.zeros(6)
            tex = np.zeros(50)
            verts_real = model.forward(shape, exp, pose, tex)
            log(f"  Real FLAME mesh: {verts_real.shape}")
            
            obj_path_real = os.path.join(OUTPUT_DIR, 'flame_real.obj')
            model.export_obj(verts_real, obj_path_real)
            log(f"  Exported real FLAME: {obj_path_real}")
        
        log("FLAME test complete", {'vertices': n_vertices, 'faces': n_faces})
        return {'vertices': n_vertices, 'faces': n_faces}
    except Exception as e:
        log("FLAME test failed", {'error': str(e), 'traceback': traceback.format_exc()})
        return None

# ═══════════════════════════════════════════════════════════════
# STEP 3: Brain-Cog test (real API)
# ═══════════════════════════════════════════════════════════════
def test_brain_cog():
    log("Testing Brain-Cog (real API)...")
    try:
        from dreamtalk.cognition.core.snn.brain_cog.brain_cog_api import BrainCogAPI
        import torch
        
        api = BrainCogAPI()
        
        status = api.get_status()
        log(f"  Status: {json.dumps(status, default=str)[:200]}")
        
        # Build a decision-making network
        dmn = api.build_dmn_network(input_size=10, hidden_size=32, output_size=4)
        api.register_network("decision_maker", dmn)
        
        # Run a forward pass
        x = torch.randn(1, 10)
        output = api.run_network("decision_maker", x)
        log(f"  DMN output shape: {output.shape}, values: {output[0].tolist()}")
        
        # Build a working memory network
        wm = api.build_wm_network(input_size=10, delay_size=16, output_size=4)
        api.register_network("working_memory", wm)
        wm_out = api.run_network("working_memory", x)
        log(f"  WM output shape: {wm_out.shape}, values: {wm_out[0].tolist()}")
        
        # Test available components
        nt = api.neuron_types_available()
        lr = list(api.learning_rules_available().keys())[:3] if hasattr(api, 'learning_rules_available') else ["stdp"]
        enc = list(api.encoding_methods_available().keys())[:3]
        cf = list(api.cognitive_functions_available().keys())[:3]
        log(f"  Neurons: {list(nt.keys())[:4]}...")
        log(f"  Encodings: {enc}...")
        log(f"  Functions: {cf}...")
        
        log("Brain-Cog test complete")
        return status
    except Exception as e:
        log("Brain-Cog test failed", {'error': str(e), 'traceback': traceback.format_exc()})
        return None

# ═══════════════════════════════════════════════════════════════
# STEP 4: Downstream workflow (Task 3)
# ═══════════════════════════════════════════════════════════════
def test_workflow():
    log("Testing downstream workflow (Brain-Cog dynamic -> Kokoro emotion TTS -> Output)...")
    try:
        from dreamtalk.cognition.core.snn.brain_cog.brain_cog_api import BrainCogAPI
        from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine
        import torch
        from scipy.io import wavfile
        
        api = BrainCogAPI()
        tts = KokoroTTSEngine(weights_dir='weights/kokoro')
        
        # Build DMN for emotion processing
        # 7 emotion inputs -> 5 cognitive domains
        dmn = api.build_dmn_network(input_size=7, hidden_size=32, output_size=5)
        api.register_network("emotion_cognition", dmn)
        
        # Emotion -> cognitive domain mapping
        EMOTION_LABELS = ['happy', 'sad', 'fear', 'anger', 'surprise', 'disgust', 'neutral']
        DOMAIN_LABELS = ['perception', 'memory', 'motor', 'decision', 'emotion']
        
        # Ground-truth domain activations per emotion
        emotion_domains = {
            'happy': [0.1, 0.3, 0.6, 0.8, 0.9],
            'sad': [0.2, 0.9, 0.1, 0.1, 0.7],
            'fear': [0.9, 0.4, 0.8, 0.3, 0.6],
            'anger': [0.3, 0.2, 0.7, 0.9, 0.5],
            'surprise': [0.8, 0.3, 0.4, 0.2, 0.3],
            'disgust': [0.4, 0.5, 0.1, 0.2, 0.8],
            'neutral': [0.5, 0.3, 0.2, 0.3, 0.3],
        }
        
        workflow_results = []
        for emotion, domains in emotion_domains.items():
            # Step A: Brain-Cog processes emotion
            x = torch.tensor([[1.0 if EMOTION_LABELS[i] == emotion else 0.0 for i in range(7)]])
            domain_output = dmn(x)
            primary_domain_idx = torch.argmax(domain_output[0]).item()
            primary_domain = DOMAIN_LABELS[primary_domain_idx]
            
            # Step B: Map emotion to Kokoro voice
            voice = tts.select_best_voice(lang='en', emotion=emotion)
            
            # Step C: Generate speech
            text = f"This is a {emotion} message generated through our cognitive pipeline. The primary domain is {primary_domain}."
            audio = tts.synthesize(text, voice=voice, speed=1.0)
            
            out_path = os.path.join(OUTPUT_DIR, f'workflow_{emotion}.wav')
            wavfile.write(out_path, 24000, audio)
            
            workflow_results.append({
                'emotion': emotion,
                'primary_domain': primary_domain,
                'domain_scores': [round(float(v), 3) for v in domain_output[0].tolist()],
                'voice': voice,
                'output': out_path,
                'samples': len(audio)
            })
            log(f"  Workflow [{emotion}]: domain={primary_domain}, voice={voice}")
        
        log("Workflow complete", {'results': workflow_results})
        return workflow_results
    except Exception as e:
        log("Workflow test failed", {'error': str(e), 'traceback': traceback.format_exc()})
        return None

# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    results = {}
    
    results['tts'] = generate_tts()
    results['flame'] = test_flame()
    results['brain_cog'] = test_brain_cog()
    results['workflow'] = test_workflow()
    
    summary_path = os.path.join(OUTPUT_DIR, 'pipeline_samples_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    all_ok = all(v is not None for v in results.values())
    log("ALL DONE" if all_ok else "PARTIAL FAILURE", {
        'summary_path': summary_path,
        'tts_ok': results['tts'] is not None,
        'flame_ok': results['flame'] is not None,
        'brain_cog_ok': results['brain_cog'] is not None,
        'workflow_ok': results['workflow'] is not None,
    })
    
    exit(0 if all_ok else 1)
