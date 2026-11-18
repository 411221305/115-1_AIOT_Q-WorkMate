# SPDX-License-Identifier: MIT
"""Pet LED Matrix Animation Manager for Arduino UNO Q.

Connects to the MCU via Arduino_RouterBridge RPC ('draw' method).
Runs an asynchronous animation thread to render dynamic emotions and status.
"""

import logging
import threading
import time
from typing import List, Optional

from matrix_frames import (
    FRAME_BLINK,
    FRAME_CHECK,
    FRAME_HEART,
    FRAME_LISTEN,
    FRAME_SIZE,
    FRAME_SLEEP,
    FRAME_SMILE,
    FRAME_WATER,
    SPEAKING_FRAMES,
    THINKING_FRAMES,
    make_pomodoro_frame,
)

logger = logging.getLogger("PetMatrix")


class PetMatrix:
    """Controls the 8x13 LED Matrix animations and exposes live frame buffer."""

    def __init__(self, bridge_address: Optional[str] = None):
        self.bridge = None
        self.bridge_connected = False
        self.current_frame: List[int] = list(FRAME_SMILE)
        self.mood = "idle"  # idle, listening, thinking, speaking, heart, pomodoro, water, check, sleep
        self.pomodoro_progress = 0.0  # 0.0 to 1.0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._temp_mood_until = 0.0
        self._thread: Optional[threading.Thread] = None

        self._init_bridge(bridge_address)

    def _init_bridge(self, bridge_address: Optional[str] = None) -> None:
        try:
            from arduino.router_bridge import Bridge

            self.bridge = Bridge(address=bridge_address) if bridge_address else Bridge()
            self.bridge.connect()
            self.bridge_connected = True
            logger.info("Successfully connected to Arduino Router Bridge.")
        except Exception as e:
            logger.warning("Could not connect to Arduino Bridge (%s). Running in virtual matrix mode.", e)
            self.bridge = None
            self.bridge_connected = False

    def draw_raw(self, frame: List[int]) -> None:
        """Immediately draws a 104-byte frame to both local cache and hardware."""
        if len(frame) != FRAME_SIZE:
            frame = (frame + [0] * FRAME_SIZE)[:FRAME_SIZE]
        with self._lock:
            self.current_frame = list(frame)

        if self.bridge_connected and self.bridge:
            try:
                self.bridge.call("draw", bytes(frame))
            except Exception as e:
                logger.error("Bridge RPC call 'draw' failed: %s", e)

    def set_mood(self, mood: str, duration: float = 0.0) -> None:
        """Set the pet mood/emotion.
        
        If duration > 0, reverts to 'idle' after duration seconds.
        """
        mood = mood.lower()
        with self._lock:
            self.mood = mood
            if duration > 0:
                self._temp_mood_until = time.time() + duration
            else:
                self._temp_mood_until = 0.0
        logger.info("Pet mood changed to: %s (duration=%s)", mood, duration)

    def set_pomodoro_progress(self, progress: float) -> None:
        """Update countdown progress (0.0=empty, 1.0=full)."""
        with self._lock:
            self.pomodoro_progress = max(0.0, min(1.0, progress))
            self.mood = "pomodoro"

    def get_current_frame(self) -> List[int]:
        """Returns the current 104-pixel frame for Web Dashboard mirror."""
        with self._lock:
            return list(self.current_frame)

    def start(self) -> None:
        """Starts the animation loop thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._animation_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stops the animation loop and disconnects bridge."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        if self.bridge_connected and self.bridge:
            try:
                self.bridge.disconnect()
            except Exception:
                pass
            self.bridge_connected = False

    def _animation_loop(self) -> None:
        last_blink_time = time.time()
        is_blinking = False
        think_idx = 0
        speak_idx = 0

        while not self._stop_event.is_set():
            now = time.time()

            with self._lock:
                # 暫時情緒到期檢查
                if self._temp_mood_until > 0 and now >= self._temp_mood_until:
                    self.mood = "idle"
                    self._temp_mood_until = 0.0

                current_mood = self.mood
                progress = self.pomodoro_progress

            # 依目前 mood 繪製合適的動畫幀
            if current_mood == "idle":
                # 待命呼吸與定時眨眼 (每 3.5 秒眨 0.2 秒)
                if not is_blinking and (now - last_blink_time >= 3.5):
                    is_blinking = True
                    last_blink_time = now
                    self.draw_raw(FRAME_BLINK)
                elif is_blinking and (now - last_blink_time >= 0.2):
                    is_blinking = False
                    last_blink_time = now
                    self.draw_raw(FRAME_SMILE)
                elif not is_blinking:
                    self.draw_raw(FRAME_SMILE)
                time.sleep(0.1)

            elif current_mood == "listening":
                self.draw_raw(FRAME_LISTEN)
                time.sleep(0.15)

            elif current_mood == "thinking":
                self.draw_raw(THINKING_FRAMES[think_idx])
                think_idx = (think_idx + 1) % len(THINKING_FRAMES)
                time.sleep(0.12)

            elif current_mood == "speaking":
                self.draw_raw(SPEAKING_FRAMES[speak_idx])
                speak_idx = (speak_idx + 1) % len(SPEAKING_FRAMES)
                time.sleep(0.15)

            elif current_mood == "heart":
                self.draw_raw(FRAME_HEART)
                time.sleep(0.2)

            elif current_mood == "water":
                self.draw_raw(FRAME_WATER)
                time.sleep(0.2)

            elif current_mood == "check":
                self.draw_raw(FRAME_CHECK)
                time.sleep(0.2)

            elif current_mood == "sleep":
                self.draw_raw(FRAME_SLEEP)
                time.sleep(0.3)

            elif current_mood == "pomodoro":
                self.draw_raw(make_pomodoro_frame(progress))
                time.sleep(0.5)

            else:
                self.draw_raw(FRAME_SMILE)
                time.sleep(0.2)
