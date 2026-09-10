import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("importing brain_pipeline")
from dreamtalk.pipeline.brain_pipeline import PFCBrainArea
print("PFCBrainArea imported")

print("instantiating PFCBrainArea")
p = PFCBrainArea()
print("PFCBrainArea instantiated")
