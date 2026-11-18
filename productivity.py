# SPDX-License-Identifier: MIT
"""Productivity Modules: Pomodoro Timer, To-Do List, and Health Coach."""

import json
import logging
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Productivity")

TODO_FILE = os.path.expanduser("~/pet_todos.json")


class TodoManager:
    """Manages persistent to-do items stored as JSON."""

    def __init__(self, file_path: str = TODO_FILE):
        self.file_path = file_path
        self._lock = threading.RLock()
        self.todos: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.todos = json.load(f)
            except Exception as e:
                logger.error("Failed to load todos from %s: %s", self.file_path, e)
                self.todos = []
        else:
            self.todos = []

    def _save(self) -> None:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.todos, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save todos to %s: %s", self.file_path, e)

    def add(self, text: str) -> Dict[str, Any]:
        with self._lock:
            next_id = max([t.get("id", 0) for t in self.todos], default=0) + 1
            item = {
                "id": next_id,
                "text": text.strip(),
                "done": False,
                "time": time.strftime("%H:%M"),
            }
            self.todos.append(item)
            self._save()
            return item

    def list_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.todos)

    def complete(self, todo_id: int) -> bool:
        with self._lock:
            for item in self.todos:
                if item.get("id") == todo_id:
                    item["done"] = True
                    self._save()
                    return True
            return False

    def toggle(self, todo_id: int) -> bool:
        with self._lock:
            for item in self.todos:
                if item.get("id") == todo_id:
                    item["done"] = not item.get("done", False)
                    self._save()
                    return True
            return False

    def clear_completed(self) -> int:
        with self._lock:
            before_len = len(self.todos)
            self.todos = [t for t in self.todos if not t.get("done", False)]
            if len(self.todos) != before_len:
                self._save()
            return before_len - len(self.todos)

    def remove(self, todo_id: int) -> bool:
        with self._lock:
            before_len = len(self.todos)
            self.todos = [t for t in self.todos if t.get("id") != todo_id]
            if len(self.todos) != before_len:
                self._save()
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self.todos.clear()
            self._save()


class PomodoroTimer:
    """Non-blocking Pomodoro Focus Timer with progress callbacks."""

    def __init__(
        self,
        on_tick: Optional[Callable[[float, int], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None,
    ):
        self.on_tick = on_tick          # (progress: 0.0~1.0, remaining_sec: int)
        self.on_complete = on_complete  # (label: str)
        self.active = False
        self.mode = "focus"             # "focus" or "break"
        self.label = "專注工作"
        self.total_seconds = 0
        self.end_time = 0.0
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()

    def start(self, minutes: float = 25.0, label: str = "專注工作", mode: str = "focus") -> None:
        self.stop()
        with self._lock:
            self.mode = mode
            self.label = label
            self.total_seconds = int(max(10, minutes * 60))
            self.end_time = time.time() + self.total_seconds
            self.active = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            logger.info("Started Pomodoro [%s]: %s minutes for '%s'", mode, minutes, label)

    def start_break(self, minutes: float = 5.0, label: str = "放鬆小憩") -> None:
        self.start(minutes=minutes, label=label, mode="break")

    def stop(self) -> None:
        with self._lock:
            if self.active:
                self._stop_event.set()
                self.active = False
                if self._thread and self._thread.is_alive() and self._thread != threading.current_thread():
                    self._thread.join(timeout=0.5)
                logger.info("Stopped Pomodoro timer.")

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            if not self.active:
                return {
                    "active": False,
                    "mode": self.mode,
                    "remaining_seconds": 0,
                    "total_seconds": self.total_seconds,
                    "progress": 0.0,
                    "label": self.label,
                }
            remaining = max(0, int(round(self.end_time - time.time())))
            elapsed = self.total_seconds - remaining
            progress = max(0.0, min(1.0, elapsed / self.total_seconds if self.total_seconds else 0.0))
            return {
                "active": True,
                "mode": self.mode,
                "remaining_seconds": remaining,
                "total_seconds": self.total_seconds,
                "progress": progress,
                "label": self.label,
            }

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            now = time.time()
            remaining = max(0, int(round(self.end_time - now)))
            elapsed = self.total_seconds - remaining
            progress = max(0.0, min(1.0, elapsed / self.total_seconds if self.total_seconds else 0.0))

            if self.on_tick:
                try:
                    self.on_tick(progress, remaining)
                except Exception as e:
                    logger.error("Error in on_tick callback: %s", e)

            if remaining <= 0:
                with self._lock:
                    self.active = False
                logger.info("Pomodoro completed: '%s'", self.label)
                if self.on_complete:
                    try:
                        self.on_complete(self.label)
                    except Exception as e:
                        logger.error("Error in on_complete callback: %s", e)
                break

            time.sleep(1.0)


SCHEDULE_FILE = os.path.expanduser("~/pet_schedule.json")


class ScheduleManager:
    """Manages an ordered queue of focus & break blocks (Timeline)."""

    def __init__(
        self,
        timer: PomodoroTimer,
        file_path: str = SCHEDULE_FILE,
        on_block_advance: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_schedule_complete: Optional[Callable[[], None]] = None,
    ):
        self.timer = timer
        self.file_path = file_path
        self.on_block_advance = on_block_advance
        self.on_schedule_complete = on_schedule_complete
        self._lock = threading.RLock()
        self.blocks: List[Dict[str, Any]] = []
        self.current_index: int = -1
        self.active: bool = False
        self._load()

        orig_on_complete = timer.on_complete

        def _handle_complete(label: str) -> None:
            if orig_on_complete:
                try:
                    orig_on_complete(label)
                except Exception as e:
                    logger.error("Error in orig on_complete: %s", e)
            self._on_timer_completed()

        timer.on_complete = _handle_complete

    def _load(self) -> None:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.blocks = data.get("blocks", [])
                    self.current_index = data.get("current_index", -1)
            except Exception as e:
                logger.error("Failed to load schedule: %s", e)
                self.blocks = []
                self.current_index = -1
        else:
            self.blocks = [
                {"id": 1, "type": "focus", "duration": 25, "label": "專注工作", "status": "pending"},
                {"id": 2, "type": "break", "duration": 5, "label": "護眼小憩", "status": "pending"},
                {"id": 3, "type": "focus", "duration": 25, "label": "專注複習", "status": "pending"},
            ]
            self.current_index = -1

    def _save(self) -> None:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({"blocks": self.blocks, "current_index": self.current_index}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save schedule: %s", e)

    def add_block(self, block_type: str, duration: float, label: str) -> Dict[str, Any]:
        with self._lock:
            next_id = max([b.get("id", 0) for b in self.blocks], default=0) + 1
            block = {
                "id": next_id,
                "type": "break" if block_type == "break" else "focus",
                "duration": float(duration),
                "label": label.strip() or ("專注工作" if block_type == "focus" else "護眼小憩"),
                "status": "pending",
            }
            self.blocks.append(block)
            self._save()
            return block

    def set_blocks(self, blocks_data: List[Dict[str, Any]], auto_start: bool = True) -> List[Dict[str, Any]]:
        self.stop()
        with self._lock:
            self.blocks = []
            for i, b in enumerate(blocks_data, start=1):
                self.blocks.append({
                    "id": i,
                    "type": "break" if b.get("type") == "break" else "focus",
                    "duration": float(b.get("duration", 25)),
                    "label": str(b.get("label", "專注工作")).strip(),
                    "status": "pending",
                })
            self.current_index = -1
            self._save()
        if auto_start and self.blocks:
            self.start_index(0)
        return list(self.blocks)

    def start_index(self, index: int = 0) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self.blocks or index < 0 or index >= len(self.blocks):
                return None
            self.current_index = index
            for i, b in enumerate(self.blocks):
                if i < index:
                    b["status"] = "completed"
                elif i == index:
                    b["status"] = "running"
                else:
                    b["status"] = "pending"
            cur = self.blocks[self.current_index]
            self.active = True
            self._save()

        if cur["type"] == "break":
            self.timer.start_break(minutes=cur["duration"], label=cur["label"])
        else:
            self.timer.start(minutes=cur["duration"], label=cur["label"], mode="focus")

        if self.on_block_advance:
            try:
                self.on_block_advance(cur)
            except Exception as e:
                logger.error("Error in on_block_advance: %s", e)
        return cur

    def next_block(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            next_idx = self.current_index + 1
            if next_idx >= len(self.blocks):
                if 0 <= self.current_index < len(self.blocks):
                    self.blocks[self.current_index]["status"] = "completed"
                self.active = False
                self.current_index = -1
                self._save()
                should_finish = True
            else:
                should_finish = False

        if should_finish:
            self.timer.stop()
            logger.info("Schedule completed all blocks.")
            if self.on_schedule_complete:
                try:
                    self.on_schedule_complete()
                except Exception as e:
                    logger.error("Error in on_schedule_complete: %s", e)
            return None

        return self.start_index(next_idx)

    def stop(self) -> None:
        with self._lock:
            self.active = False
            if 0 <= self.current_index < len(self.blocks):
                if self.blocks[self.current_index]["status"] == "running":
                    self.blocks[self.current_index]["status"] = "pending"
            self._save()
        self.timer.stop()

    def clear(self) -> None:
        self.stop()
        with self._lock:
            self.blocks = []
            self.current_index = -1
            self._save()

    def _on_timer_completed(self) -> None:
        with self._lock:
            if not self.active or self.current_index < 0 or self.current_index >= len(self.blocks):
                return
            self.blocks[self.current_index]["status"] = "completed"
            self._save()
        self.next_block()

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            cur_block = self.blocks[self.current_index] if 0 <= self.current_index < len(self.blocks) else None
            return {
                "active": self.active,
                "current_index": self.current_index,
                "current_block": cur_block,
                "blocks": list(self.blocks),
            }
