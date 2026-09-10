"""
DreamTalk — Pipeline Unit Tests
Tests individual pipeline components in isolation.
Run: python -m pytest tests/test_pipeline.py -v
"""
import sys
import os
import time
import asyncio
import unittest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestEmotionAnimation(unittest.TestCase):
    """Test emotion-to-animation mapping."""
    
    def test_import(self):
        from dreamtalk.pipeline.emotion_animation import EmotionToAnimation, AvatarExpression
        self.assertTrue(hasattr(EmotionToAnimation, 'blend'))
    
    def test_neutral_expression(self):
        from dreamtalk.pipeline.emotion_animation import EmotionToAnimation
        converter = EmotionToAnimation()
        expr = converter.blend("neutral", 0.5)
        self.assertEqual(expr.emotion, "neutral")
        self.assertGreater(expr.jaw_open, 0)
    
    def test_happy_expression(self):
        from dreamtalk.pipeline.emotion_animation import EmotionToAnimation
        converter = EmotionToAnimation()
        expr = converter.blend("happy", 0.8)
        self.assertEqual(expr.emotion, "happy")
        self.assertGreater(expr.mouth.get("mouth_smile_left", 0), 0.3)
    
    def test_sad_expression(self):
        from dreamtalk.pipeline.emotion_animation import EmotionToAnimation
        converter = EmotionToAnimation()
        expr = converter.blend("sad", 0.8)
        self.assertEqual(expr.emotion, "sad")
        self.assertGreater(expr.mouth.get("mouth_frown_left", 0), 0.2)
    
    def test_smooth_interpolation(self):
        from dreamtalk.pipeline.emotion_animation import EmotionToAnimation
        converter = EmotionToAnimation()
        expr1 = converter.blend("happy", 0.5)
        expr2 = converter.blend("sad", 0.5)
        smoothed = converter.smooth(expr1, expr2, 0.5)
        # Smoothed should be between the two
        self.assertIsNotNone(smoothed)
        self.assertIn("mouth_smile_left", smoothed.mouth)


class TestSessionManager(unittest.TestCase):
    """Test session management."""
    
    def test_create_session(self):
        from dreamtalk.pipeline.session_manager import SessionManager
        mgr = SessionManager()
        session = mgr.create_session(user_id="test-user")
        self.assertIsNotNone(session.session_id)
        self.assertEqual(session.user_id, "test-user")
    
    def test_add_messages(self):
        from dreamtalk.pipeline.session_manager import SessionManager
        mgr = SessionManager()
        session = mgr.create_session(user_id="test-user")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")
        self.assertEqual(len(session.messages), 2)
    
    def test_get_history(self):
        from dreamtalk.pipeline.session_manager import SessionManager
        mgr = SessionManager()
        session = mgr.create_session(user_id="test-user")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")
        session.add_message("user", "How are you?")
        history = mgr.get_history(session.session_id)
        self.assertEqual(len(history), 3)
    
    def test_clear_session(self):
        from dreamtalk.pipeline.session_manager import SessionManager
        mgr = SessionManager()
        session = mgr.create_session(user_id="test-user")
        session.add_message("user", "Hello")
        mgr.clear_session(session.session_id)
        history = mgr.get_history(session.session_id)
        self.assertEqual(len(history), 0)


class TestResilience(unittest.TestCase):
    """Test resilience patterns (circuit breaker, retry)."""
    
    def test_circuit_breaker_closed(self):
        from dreamtalk.pipeline.resilience import CircuitBreaker
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        self.assertEqual(cb.state, "closed")
        result = cb.call(lambda: "success")
        self.assertEqual(result, "success")
    
    def test_circuit_breaker_opens(self):
        from dreamtalk.pipeline.resilience import CircuitBreaker
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        
        # Fail twice to trip the breaker
        for _ in range(2):
            try:
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
            except ValueError:
                pass
        
        self.assertEqual(cb.state, "open")
        
        # Next call should raise CircuitBreakerOpen
        from dreamtalk.pipeline.resilience import CircuitBreakerOpen
        with self.assertRaises(CircuitBreakerOpen):
            cb.call(lambda: "should not run")
    
    def test_retry_success(self):
        from dreamtalk.pipeline.resilience import retry_with_backoff
        attempt = [0]
        def flaky():
            attempt[0] += 1
            if attempt[0] < 3:
                raise ValueError("not yet")
            return "done"
        
        result = retry_with_backoff(flaky, max_retries=5, base_delay=0.01)
        self.assertEqual(result, "done")
        self.assertEqual(attempt[0], 3)
    
    def test_retry_exhaustion(self):
        from dreamtalk.pipeline.resilience import retry_with_backoff
        def always_fail():
            raise ValueError("always")
        
        with self.assertRaises(ValueError):
            retry_with_backoff(always_fail, max_retries=2, base_delay=0.01)


class TestModelManager(unittest.TestCase):
    """Test model loading manager."""
    
    def test_singleton(self):
        from dreamtalk.pipeline.model_manager import get_model_manager
        mgr1 = get_model_manager()
        mgr2 = get_model_manager()
        self.assertIs(mgr1, mgr2)
    
    def test_register_model(self):
        from dreamtalk.pipeline.model_manager import get_model_manager
        mgr = get_model_manager()
        mgr.register_model("test_model", factory=lambda: {"loaded": True})
        self.assertIn("test_model", mgr.list_models())


class TestAnalytics(unittest.TestCase):
    """Test analytics collector."""
    
    def test_record_emotion(self):
        from dreamtalk.pipeline.analytics import get_analytics
        analytics = get_analytics()
        analytics.record_emotion("happy", valence=0.8, arousal=0.6)
        data = analytics.get_emotion_analytics(window_minutes=5)
        self.assertIn("emotions", data)
        self.assertGreater(data["total_events"], 0)
    
    def test_record_brain_activity(self):
        from dreamtalk.pipeline.analytics import get_analytics
        analytics = get_analytics()
        analytics.record_brain_activity("pfc", firing_rate=15.5, action="respond_confirm")
        data = analytics.get_brain_analytics()
        self.assertIn("brain_areas", data)


class TestHealthMonitor(unittest.TestCase):
    """Test pipeline health monitor."""
    
    def test_get_monitor(self):
        from dreamtalk.pipeline.health import get_health_monitor
        monitor = get_health_monitor()
        self.assertIsNotNone(monitor)
    
    def test_singleton(self):
        from dreamtalk.pipeline.health import get_health_monitor
        m1 = get_health_monitor()
        m2 = get_health_monitor()
        self.assertIs(m1, m2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
