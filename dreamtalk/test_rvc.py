#!/usr/bin/env python
"""Test RVC installation - fairseq import, weight availability."""
import os, sys, traceback
sys.setrecursionlimit(3000)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

print("=" * 50)
print("Testing fairseq import...")
try:
    import fairseq
    print(f"  fairseq: {fairseq.__version__} OK")
except Exception as e:
    print(f"  FAIL fairseq: {e}")
    traceback.print_exc()
    sys.exit(1)

print("Testing checkpoint_utils...")
try:
    from fairseq.checkpoint_utils import load_model_ensemble_and_task
    print("  checkpoint_utils: OK")
except Exception as e:
    print(f"  FAIL checkpoint_utils: {e}")
    traceback.print_exc()
    sys.exit(1)

print("Testing RVC converters...")
try:
    from voice.core.vc.rvc.rvc_converter import check_weights_available, get_best_pretrained_path
    w = check_weights_available()
    print("  RVC weights:")
    for k, v in w.items():
        print(f"    {k}: {'YES' if v else 'MISSING'}")
    print(f"  Best generator: {get_best_pretrained_path()}")
except Exception as e:
    print(f"  FAIL RVC: {e}")
    traceback.print_exc()
    sys.exit(1)

print("=" * 50)
print("ALL RVC TESTS PASSED")
print("=" * 50)
