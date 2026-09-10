# Dreamtalk - Face Engine
# Extracted from LivePortrait
import time


class Timer:
    def __init__(self):
        self.start_time = None
        self.elapsed = 0

    def start(self):
        self.start_time = time.time()

    def stop(self):
        if self.start_time is not None:
            self.elapsed = time.time() - self.start_time
            self.start_time = None
        return self.elapsed

    def reset(self):
        self.start_time = None
        self.elapsed = 0
