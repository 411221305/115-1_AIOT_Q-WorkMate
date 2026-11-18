# SPDX-License-Identifier: MIT
"""Q-WorkMate / LumiPet: AI Productivity Desk Pet for Arduino UNO Q.

Combines:
  - Gemini Live Audio WebSocket streaming
  - 8x13 LED Matrix dynamic pixel art animations via Bridge RPC
  - Onboard RGB LED mood indicator
  - Pomodoro focus timer with live progress display
  - Voice & Web to-do memo manager
  - Interactive Web Dashboard (Live Matrix Mirror, Telemetry, Controls)
"""

import asyncio
import base64
import glob
import json
import logging
import os
import struct
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import uvicorn
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, Response

from matrix_frames import FRAME_SIZE
from pet_matrix import PetMatrix
from productivity import PomodoroTimer, TodoManager
from rgb_led import RgbLedController

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("QPetAgent")

KEY_FILE = os.environ.get("KEY_FILE", "/key")
if not os.path.exists(KEY_FILE):
    alt_key = os.path.expanduser("~/.gemini_key")
    if os.path.exists(alt_key):
        KEY_FILE = alt_key

MODELS = [m.strip() for m in os.environ.get(
    "MODEL", "gemini-3.8-live,gemini-2.5-flash-native-audio-preview-12-2025").split(",") if m.strip()]
CARD = os.environ.get("CARD", "plughw:UAC2Gadget,0")
PORT = int(os.environ.get("PORT", "7790"))
VOICE = os.environ.get("VOICE", "Kore")
URL = ("wss://generativelanguage.googleapis.com/ws/"
       "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent")

IN_RATE = 16000
OUT_RATE = 24000
PLAY_TIMEOUT = 4

try:
    import opencc
    _CC = opencc.OpenCC("s2twp")
    def tw(s: str) -> str:
        return _CC.convert(s)
except Exception:
    def tw(s: str) -> str:
        return s

# ---------------------------------------------------------------- 硬體與管理子系統初始化
rgb = RgbLedController()
matrix = PetMatrix()
todos = TodoManager()


def on_pomodoro_tick(progress: float, remaining: int) -> None:
    if pomodoro.mode == "break":
        matrix.set_mood("coffee", duration=0.0)
    else:
        matrix.set_pomodoro_progress(progress)


def on_pomodoro_complete(label: str) -> None:
    logger.info("Pomodoro session completed: %s (mode=%s)", label, pomodoro.mode)
    if pomodoro.mode == "focus":
        matrix.set_mood("coffee", duration=10.0, force=True)
        rgb.set_color("yellow")
    else:
        matrix.set_mood("happy", duration=6.0, force=True)
        rgb.set_color("green")


pomodoro = PomodoroTimer(on_tick=on_pomodoro_tick, on_complete=on_pomodoro_complete)

# ---------------------------------------------------------------- Gemini 工具定義與實作
PERSONA = (
    "你是住在 Arduino UNO Q 板子裡的 AI 桌面生產力桌寵『Q-Pet』（或稱 LumiPet）。"
    "你的對象是正在用電腦讀書、寫程式或工作的同學。"
    "你性格活潑、親切、熱愛工作陪伴，一律用繁體中文（台灣口語習慣）回答，說話簡短精煉（最多兩到三句）。"
    "你擁有強大的硬體與生產力工具，能主動替主人管理生活與專注：\n"
    "1. 當同學要求專注工作、讀書或設定番茄鐘時，呼叫 start_focus_timer；要求休息、小憩或護眼放鬆時呼叫 start_break_timer；要求看剩餘時間呼叫 get_timer_status；取消叫 cancel_focus_timer。\n"
    "2. 當同學想記事情或待辦清單，呼叫 add_todo；想查今天要做什麼呼叫 list_todos；完成叫 complete_todo。\n"
    "3. 當同學工作很久、喊累或口渴，呼叫 remind_hydration 給予溫馨提醒與關懷。\n"
    "4. 當同學誇獎你或想看你撒嬌，呼叫 set_pet_mood 變成 heart（愛心）或 coffee（咖啡）。\n"
    "5. 問到板子溫度、負載或系統狀態，呼叫 get_board_status；問現在時間呼叫 get_time。"
)

TOOLS = [{"functionDeclarations": [
    {
        "name": "start_focus_timer",
        "description": "啟動專注番茄鐘倒數計時。板載點陣會即時顯示進度格條。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "minutes": {"type": "NUMBER", "description": "專注分鐘數，例如 25 或 1"},
                "task_name": {"type": "STRING", "description": "專注的任務名稱，例如『寫作業』或『讀書』"}
            },
            "required": ["minutes"]
        }
    },
    {
        "name": "start_break_timer",
        "description": "啟動小憩放鬆計時器（例如 5 分鐘休息或 20-20-20 護眼伸展）。板載點陣會顯示冒煙熱咖啡杯動畫。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "minutes": {"type": "NUMBER", "description": "休息分鐘數，例如 5 或 1"},
                "label": {"type": "STRING", "description": "休息項目名稱，例如『放鬆小憩』或『護眼伸展』"}
            }
        }
    },
    {
        "name": "get_timer_status",
        "description": "查詢目前專注番茄鐘的剩餘時間與進度。",
    },
    {
        "name": "cancel_focus_timer",
        "description": "取消當前的專注計時，讓桌寵回到待命笑臉。",
    },
    {
        "name": "add_todo",
        "description": "將待辦事項或備忘筆記存入桌寵的清單中。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task": {"type": "STRING", "description": "待辦事項內容"}
            },
            "required": ["task"]
        }
    },
    {
        "name": "list_todos",
        "description": "列出目前儲存的所有待辦事項與備忘錄。",
    },
    {
        "name": "complete_todo",
        "description": "將指定編號的待辦事項標記為已完成。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "todo_id": {"type": "INTEGER", "description": "待辦事項的 ID 編號"}
            },
            "required": ["todo_id"]
        }
    },
    {
        "name": "remind_hydration",
        "description": "提醒主人喝水休息、伸展放鬆，點陣螢幕會顯示水杯圖示。",
    },
    {
        "name": "set_pet_mood",
        "description": "手動設定桌寵的心情與表情。可用值：heart(愛心), happy(開心), sleep(睡覺), water(水杯), idle(微笑待命)。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "mood": {"type": "STRING", "description": "目標心情名稱"}
            },
            "required": ["mood"]
        }
    },
    {
        "name": "get_board_status",
        "description": "讀取這塊 UNO Q 板子現在的狀態：CPU 溫度、可用記憶體、負載、開機多久、核心版本。",
    },
    {
        "name": "get_time",
        "description": "取得台灣現在的日期、時間與星期幾。",
    },
]}]


def _read_sys(path: str, default: str = "") -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return default


def tool_get_board_status(**kwargs) -> Dict[str, Any]:
    temp = "未知"
    for p in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
        val = _read_sys(p)
        if val.isdigit() and int(val) > 0:
            temp = f"{int(val)/1000.0:.1f} °C"
            break

    mem_avail = "未知"
    for line in _read_sys("/proc/meminfo").splitlines():
        if line.startswith("MemAvailable:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                mem_avail = f"{int(parts[1])//1024} MB"

    uptime_sec = float(_read_sys("/proc/uptime", "0").split()[0])
    load = _read_sys("/proc/loadavg", "").split()[:3]

    return {
        "cpu_temperature": temp,
        "memory_available": mem_avail,
        "uptime": f"{int(uptime_sec//3600)} 小時 {int((uptime_sec%3600)//60)} 分",
        "load_avg": " ".join(load),
        "kernel": _read_sys("/proc/version", "").split()[:3],
    }


def tool_get_time(**kwargs) -> Dict[str, Any]:
    t = time.gmtime(time.time() + 8 * 3600)
    return {
        "taiwan_time": time.strftime("%Y-%m-%d %H:%M:%S", t),
        "weekday": "星期" + "一二三四五六日"[t.tm_wday],
    }


def tool_start_focus_timer(minutes: float = 25.0, task_name: str = "專注工作", **kwargs) -> Dict[str, Any]:
    pomodoro.start(minutes=minutes, label=task_name)
    matrix.set_pomodoro_progress(0.0)
    rgb.set_color("red")
    return {"status": "started", "minutes": minutes, "task": task_name}


def tool_start_break_timer(minutes: float = 5.0, label: str = "放鬆小憩", **kwargs) -> Dict[str, Any]:
    pomodoro.start_break(minutes=minutes, label=label)
    matrix.set_mood("coffee", duration=0.0, force=True)
    rgb.set_color("cyan")
    return {"status": "break_started", "minutes": minutes, "label": label}


def tool_get_timer_status(**kwargs) -> Dict[str, Any]:
    return pomodoro.get_status()


def tool_cancel_focus_timer(**kwargs) -> Dict[str, Any]:
    pomodoro.stop()
    matrix.set_mood("idle", force=True)
    rgb.set_color("green")
    return {"status": "cancelled"}


def tool_add_todo(task: str, **kwargs) -> Dict[str, Any]:
    item = todos.add(task)
    matrix.set_mood("check", duration=3.0)
    rgb.set_color("cyan")
    return {"status": "added", "item": item}


def tool_list_todos(**kwargs) -> Dict[str, Any]:
    return {"todos": todos.list_all()}


def tool_complete_todo(todo_id: int, **kwargs) -> Dict[str, Any]:
    ok = todos.complete(todo_id)
    if ok:
        matrix.set_mood("check", duration=2.5)
    return {"status": "completed" if ok else "not_found", "id": todo_id}


def tool_remind_hydration(**kwargs) -> Dict[str, Any]:
    matrix.set_mood("water", duration=4.0, force=True)
    rgb.set_color("yellow")
    return {"message": "已在螢幕提醒主人喝水與放鬆休息！"}


def tool_set_pet_mood(mood: str, **kwargs) -> Dict[str, Any]:
    matrix.set_mood(mood, duration=4.0, force=True)
    if mood == "heart":
        rgb.set_color("pink")
    elif mood == "sleep":
        rgb.set_color("off")
    elif mood == "happy":
        rgb.set_color("green")
    elif mood in ("coffee", "break"):
        rgb.set_color("cyan")
    return {"status": "success", "mood": mood}


TOOL_FUNCS = {
    "get_board_status": tool_get_board_status,
    "get_time": tool_get_time,
    "start_focus_timer": tool_start_focus_timer,
    "start_break_timer": tool_start_break_timer,
    "get_timer_status": tool_get_timer_status,
    "cancel_focus_timer": tool_cancel_focus_timer,
    "add_todo": tool_add_todo,
    "list_todos": tool_list_todos,
    "complete_todo": tool_complete_todo,
    "remind_hydration": tool_remind_hydration,
    "set_pet_mood": tool_set_pet_mood,
}

# ---------------------------------------------------------------- 全域狀態與連線
S = {
    "phase": "idle",
    "model": MODELS[0],
    "in_mode": "web",
    "out_mode": "web",
    "level": 0,
    "msg": "",
    "turns": [],
    "mood": "idle",
}

ws = None
ws_lock = asyncio.Lock()
rec_proc = None
rec_task = None
rec_active = False
turn = None
last_wav = b""


def update_pet_state(phase: str) -> None:
    S["phase"] = phase
    if pomodoro.active:
        return  # 若番茄鐘倒數中，維持番茄鐘進度顯示
    if getattr(matrix, "_temp_mood_until", 0) > time.time():
        return  # 暫時情緒進行中，維持特殊表情與燈效
    if phase == "listening":
        matrix.set_mood("listening")
        rgb.set_color("blue")
    elif phase == "thinking":
        matrix.set_mood("thinking")
        rgb.set_color("blue")
    elif phase == "speaking":
        matrix.set_mood("speaking")
        rgb.set_color("green")
    elif phase == "idle":
        matrix.set_mood("idle")
        rgb.set_color("green")
    elif phase == "error":
        rgb.set_color("red")


def pcm_to_wav(pcm_bytes: bytes, rate: int = OUT_RATE) -> bytes:
    hdr = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(pcm_bytes), b"WAVE",
        b"fmt ", 16, 1, 1, rate, rate * 2, 2, 16,
        b"data", len(pcm_bytes)
    )
    return hdr + pcm_bytes


def level_of(pcm: bytes) -> int:
    if not pcm:
        return 0
    cnt = len(pcm) // 2
    ints = struct.unpack(f"<{cnt}h", pcm[: cnt * 2])
    rms = int((sum(x * x for x in ints) / max(cnt, 1)) ** 0.5)
    S["level"] = min(100, rms // 150)
    return S["level"]


async def send_audio(chunk: bytes) -> None:
    if ws is None:
        return
    msg = {
        "realtimeInput": {
            "mediaChunks": [{"mimeType": f"audio/pcm;rate={IN_RATE}", "data": base64.b64encode(chunk).decode("ascii")}]
        }
    }
    await ws.send(json.dumps(msg))


async def connect() -> None:
    global ws
    key = open(KEY_FILE).read().strip()
    for m in MODELS:
        try:
            update_pet_state("connecting")
            logger.info("Connecting to Gemini Live (%s)...", m)
            ws_conn = await websockets.connect(f"{URL}?key={key}", max_size=20 * 1024 * 1024)
            setup = {
                "setup": {
                    "model": f"models/{m}",
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}},
                    },
                    "systemInstruction": {"parts": [{"text": PERSONA}]},
                    "tools": TOOLS,
                }
            }
            await ws_conn.send(json.dumps(setup))
            raw = await ws_conn.recv()
            if "setupComplete" not in json.loads(raw):
                raise RuntimeError(f"Unexpected setup response: {raw[:200]}")
            ws = ws_conn
            S["model"] = m
            update_pet_state("idle")
            logger.info("Connected successfully to %s", m)
            asyncio.create_task(rx_loop())
            return
        except Exception as e:
            logger.warning("Failed to connect %s: %s", m, e)
    raise RuntimeError("All models failed to connect")


async def rx_loop() -> None:
    global ws, turn, last_wav
    play_proc = None
    audio_buf = bytearray()

    try:
        while True:
            raw = await ws.recv()
            msg = json.loads(raw)

            if "toolCall" in msg:
                update_pet_state("thinking")
                replies = []
                for fc in msg["toolCall"].get("functionCalls", []):
                    name = fc.get("name")
                    args = fc.get("args", {})
                    fn = TOOL_FUNCS.get(name)
                    logger.info("Tool Call: %s with args: %s", name, args)
                    try:
                        result = fn(**args) if fn else {"error": f"Tool '{name}' not found"}
                    except Exception as err:
                        result = {"error": str(err)}
                    if turn:
                        turn["tools"].append({"name": name, "args": args, "result": result})
                        if name == "start_focus_timer":
                            turn["reply"] = f"好的！已為主人設定 {args.get('minutes', 25)} 分鐘專注番茄鐘 🍅"
                        elif name == "start_break_timer":
                            turn["reply"] = f"辛苦了主人！已為您開啟 {args.get('minutes', 5)} 分鐘小憩放鬆 ☕ 記得活動筋骨、遠眺放鬆喔！"
                        elif name == "cancel_focus_timer":
                            turn["reply"] = "專注番茄鐘已為您取消 ⏹️"
                        elif name == "set_pet_mood":
                            turn["reply"] = f"已為您切換桌寵表情：{args.get('mood')} ✨"
                        elif name == "add_todo":
                            turn["reply"] = f"已為您記錄待辦事項：「{args.get('task')}」📝"
                        elif name == "list_todos":
                            turn["reply"] = "目前待辦清單已同步更新在右方 📋"
                        elif name == "remind_hydration":
                            turn["reply"] = "主人辛苦了！記得喝口溫開水、休息一下喔 💧"
                        elif name == "get_board_status":
                            t = tool_get_board_status()
                            turn["reply"] = f"板載硬體狀態良好，CPU 溫度 {t.get('cpu_temperature')}，可用記憶體 {t.get('memory_available')} 🌡️"
                        elif name == "get_time":
                            turn["reply"] = f"現在時間是 {time.strftime('%H:%M:%S')} ⏰"
                    replies.append({"id": fc.get("id"), "name": name, "response": result})

                resp_payload = {"toolResponse": {"functionResponses": replies}}
                await ws.send(json.dumps(resp_payload))

            sc = msg.get("serverContent", {})
            parts = sc.get("modelTurn", {}).get("parts", [])
            for p in parts:
                if "text" in p and turn:
                    turn["reply"] += tw(p["text"])
                if "inlineData" in p and p["inlineData"].get("mimeType", "").startswith("audio/"):
                    pcm = base64.b64decode(p["inlineData"]["data"])
                    audio_buf.extend(pcm)
                    update_pet_state("speaking")

                    if S["out_mode"] == "usb" and play_proc is None:
                        try:
                            play_proc = await asyncio.create_subprocess_exec(
                                "aplay", "-D", CARD, "-r", str(OUT_RATE), "-f", "S16_LE", "-c", "1",
                                stdin=asyncio.subprocess.PIPE,
                                stdout=asyncio.subprocess.DEVNULL,
                                stderr=asyncio.subprocess.DEVNULL,
                            )
                        except Exception as e:
                            logger.error("Could not spawn aplay: %s", e)

                    if play_proc and play_proc.stdin:
                        try:
                            play_proc.stdin.write(pcm)
                            await play_proc.stdin.drain()
                        except Exception:
                            pass

            if sc.get("turnComplete"):
                if play_proc and play_proc.stdin:
                    try:
                        play_proc.stdin.close()
                        await asyncio.wait_for(play_proc.wait(), timeout=PLAY_TIMEOUT)
                    except Exception:
                        pass
                    play_proc = None

                if audio_buf:
                    last_wav = pcm_to_wav(bytes(audio_buf), OUT_RATE)
                    if turn:
                        turn["wav_len"] = len(last_wav)
                    audio_buf.clear()

                if turn and not turn.get("reply"):
                    turn["reply"] = "🐾 收到！已為您處理完畢！"

                update_pet_state("idle")
                logger.info("Turn completed.")

    except Exception as e:
        err_str = str(e)
        if ws:
            try:
                await ws.close()
            except Exception:
                pass
            ws = None

        if "inactivity" in err_str.lower() or "1000" in err_str:
            logger.info("Session closed due to normal client inactivity. Will reconnect on next interaction.")
            update_pet_state("idle")
            S["msg"] = ""
        else:
            logger.error("Rx loop error: %s", e)
            update_pet_state("error")
            S["msg"] = f"連線異常: {e}"


# ---------------------------------------------------------------- FastAPI 路由與應用
@asynccontextmanager
async def lifespan(app: FastAPI):
    matrix.start()
    rgb.set_color("green")
    try:
        await connect()
    except Exception as e:
        logger.error("Initial connect failed: %s", e)
    yield
    matrix.stop()
    rgb.close()
    pomodoro.stop()
    if ws:
        await ws.close()


app = FastAPI(lifespan=lifespan)


@app.post("/start")
async def start_listening():
    global turn, rec_active, audio_chunk_count
    audio_chunk_count = 0
    async with ws_lock:
        if rec_active:
            return JSONResponse(S)
        if ws is None or (hasattr(ws, "closed") and ws.closed):
            try:
                await connect()
            except Exception as e:
                logger.error("Failed to connect Gemini in /start: %s", e)
                S["phase"] = "error"
                S["msg"] = "Gemini 連線失敗，請稍候再試"
                update_pet_state("error")
                return JSONResponse(S)
        rec_active = True
        update_pet_state("listening")
        logger.info("Started recording turn from browser mic.")
        turn = {
            "t_start": time.strftime("%H:%M:%S"),
            "reply": "",
            "tools": [],
            "wav_len": 0,
        }
        S["turns"].append(turn)
        return JSONResponse(S)


@app.post("/stop")
async def stop_listening():
    global rec_active
    async with ws_lock:
        if not rec_active:
            return JSONResponse(S)
        rec_active = False
        update_pet_state("thinking")
        logger.info("Stopped recording. Sent %d audio chunks to Gemini.", audio_chunk_count)
        if ws and not getattr(ws, "closed", True):
            try:
                await ws.send(json.dumps({"clientContent": {"turnComplete": True}}))
                logger.info("Sent turnComplete to Gemini Live.")
            except Exception as e:
                logger.warning("Error sending turnComplete in /stop: %s", e)
        return JSONResponse(S)


@app.post("/chat")
async def chat_text(body: dict):
    global turn
    text = body.get("text", "").strip()
    is_quick_ai = bool(body.get("isQuickAi", False))
    if not text:
        return JSONResponse({"error": "Empty text"}, status_code=400)
    async with ws_lock:
        if ws is None or (hasattr(ws, "closed") and ws.closed):
            await connect()
        update_pet_state("thinking")
        turn = {
            "t_start": time.strftime("%H:%M:%S"),
            "reply": "",
            "tools": [],
            "wav_len": 0,
            "isQuickAi": is_quick_ai,
        }
        S["turns"].append(turn)
        msg = {
            "clientContent": {
                "turns": [{"role": "user", "parts": [{"text": text}]}],
                "turnComplete": True,
            }
        }
        await ws.send(json.dumps(msg))
        return JSONResponse({"status": "sent", "text": text})


@app.post("/mode")
async def set_audio_mode(body: dict):
    for k in ("in_mode", "out_mode"):
        if body.get(k) in ("usb", "web"):
            S[k] = body[k]
    return JSONResponse(S)


audio_chunk_count = 0


@app.websocket("/mic")
async def mic_stream(sock: WebSocket):
    global audio_chunk_count
    await sock.accept()
    logger.info("Microphone WebSocket connected from browser client.")
    try:
        while True:
            chunk = await sock.receive_bytes()
            if rec_active and S["in_mode"] == "web":
                audio_chunk_count += 1
                if audio_chunk_count % 30 == 1:
                    logger.info("Streaming mic chunk #%d (%d bytes) to Gemini...", audio_chunk_count, len(chunk))
                level_of(chunk)
                await send_audio(chunk)
    except WebSocketDisconnect:
        logger.info("Microphone WebSocket disconnected.")


@app.get("/matrix")
async def get_matrix():
    return JSONResponse({"frame": matrix.get_current_frame()})


@app.get("/state")
async def get_state():
    out = dict(S)
    out["matrix"] = matrix.get_current_frame()
    out["pomodoro"] = pomodoro.get_status()
    out["todos"] = todos.list_all()
    out["mood"] = matrix.mood
    out["telemetry"] = tool_get_board_status()
    return JSONResponse(out)


@app.get("/reply.wav")
async def get_reply_wav():
    return Response(last_wav, media_type="audio/wav")


@app.post("/api/todo/add")
async def api_add_todo(body: dict):
    task = body.get("task", "").strip()
    if task:
        item = tool_add_todo(task)
        return JSONResponse(item)
    return JSONResponse({"error": "Empty task"}, status_code=400)


@app.post("/api/todo/toggle")
async def api_toggle_todo(body: dict):
    todo_id = body.get("id")
    if todo_id:
        todos.complete(int(todo_id))
        matrix.set_mood("check", duration=2.0)
    return JSONResponse({"status": "ok"})


@app.post("/api/timer/start")
async def api_timer_start(body: dict):
    minutes = float(body.get("minutes", 25))
    label = body.get("label", "專注工作")
    tool_start_focus_timer(minutes, label)
    return JSONResponse(pomodoro.get_status())


@app.post("/api/timer/break")
async def api_timer_break(body: dict):
    minutes = float(body.get("minutes", 5))
    label = body.get("label", "放鬆小憩")
    tool_start_break_timer(minutes, label)
    return JSONResponse(pomodoro.get_status())


@app.post("/api/timer/stop")
async def api_timer_stop():
    tool_cancel_focus_timer()
    return JSONResponse(pomodoro.get_status())


@app.post("/api/mood")
async def api_set_mood(body: dict):
    mood = body.get("mood", "idle")
    tool_set_pet_mood(mood)
    return JSONResponse({"mood": mood})


# ---------------------------------------------------------------- 前端 Web 儀表板 HTML
DASHBOARD_HTML = """<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Q-WorkMate / LumiPet — UNO Q AI 生產力桌寵</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: rgba(30, 41, 59, 0.7);
      --card-border: rgba(255, 255, 255, 0.08);
      --primary: #38bdf8;
      --primary-glow: rgba(56, 189, 248, 0.3);
      --accent: #818cf8;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --led-off: #1e293b;
      --led-on: #00e5ff;
      --led-glow: rgba(0, 229, 255, 0.8);
      --success: #34d399;
      --danger: #f87171;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Plus Jakarta Sans', 'Noto Sans TC', sans-serif;
      background: radial-gradient(circle at top right, #1e1b4b, #0f172a 60%);
      color: var(--text);
      min-height: 100vh;
      padding: 24px 16px;
    }
    .container { max-width: 1040px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
    
    /* Header */
    header {
      display: flex; justify-content: space-between; align-items: center;
      background: var(--card-bg); backdrop-filter: blur(12px);
      border: 1px solid var(--card-border); border-radius: 18px; padding: 16px 24px;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand h1 { font-size: 20px; font-weight: 700; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .badge { font-size: 11px; padding: 4px 10px; border-radius: 999px; background: rgba(56,189,248,0.15); color: var(--primary); font-weight: 600; border: 1px solid rgba(56,189,248,0.3); }
    .status-pill { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-muted); }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--success); box-shadow: 0 0 10px var(--success); }

    /* Grid Layout */
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    @media (max-width: 820px) { .grid-2 { grid-template-columns: 1fr; } }

    .card {
      background: var(--card-bg); backdrop-filter: blur(12px);
      border: 1px solid var(--card-border); border-radius: 18px; padding: 20px;
      display: flex; flex-direction: column; gap: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .card-title { font-size: 15px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; display: flex; justify-content: space-between; align-items: center; }

    /* 8x13 LED Matrix Mirror */
    .matrix-box { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 16px 0; }
    .matrix-grid {
      display: grid; grid-template-columns: repeat(13, 1fr); gap: 6px;
      background: #090d16; padding: 18px 22px; border-radius: 16px; border: 2px solid #1e293b;
      box-shadow: inset 0 0 20px rgba(0,0,0,0.8);
    }
    .led {
      width: 16px; height: 16px; border-radius: 50%; background: var(--led-off);
      transition: all 0.08s ease;
    }
    .led.on-1 { background: #005f73; }
    .led.on-2 { background: #0a9396; }
    .led.on-3 { background: #00b4d8; box-shadow: 0 0 4px var(--led-glow); }
    .led.on-4 { background: #00e5ff; box-shadow: 0 0 8px var(--led-glow); }

    /* Quick Command Grid */
    .quick-cmd-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .quick-cmd-grid .btn-sm { padding: 12px 10px; font-size: 13px; text-align: center; }

    /* Pomodoro Timer */
    .pomo-wrap { display: flex; flex-direction: column; align-items: center; gap: 12px; }
    .pomo-time { font-size: 48px; font-weight: 800; letter-spacing: 2px; color: var(--primary); font-variant-numeric: tabular-nums; }
    .pomo-bar { width: 100%; height: 8px; background: #1e293b; border-radius: 99px; overflow: hidden; }
    .pomo-fill { height: 100%; width: 0%; background: linear-gradient(90deg, #38bdf8, #818cf8); transition: width 0.3s; }
    .pomo-btns { display: flex; gap: 8px; width: 100%; }
    .btn-sm {
      flex: 1; padding: 10px; font-size: 13px; font-weight: 600; border-radius: 10px;
      border: 1px solid var(--card-border); background: rgba(255,255,255,0.04); color: var(--text);
      cursor: pointer; transition: all 0.1s;
    }
    .btn-sm:hover { background: rgba(255,255,255,0.1); border-color: var(--primary); }

    /* To-Do List */
    .todo-input-wrap { display: flex; gap: 8px; }
    .todo-input {
      flex: 1; padding: 10px 14px; background: rgba(15,23,42,0.8); border: 1px solid var(--card-border);
      border-radius: 10px; color: white; font-size: 14px; outline: none;
    }
    .todo-input:focus { border-color: var(--primary); }
    .todo-list { list-style: none; display: flex; flex-direction: column; gap: 8px; max-height: 180px; overflow-y: auto; }
    .todo-item {
      display: flex; align-items: center; justify-content: space-between;
      padding: 10px 12px; background: rgba(15,23,42,0.6); border-radius: 10px; font-size: 14px;
    }
    .todo-item.done { text-decoration: line-through; opacity: 0.5; }
    .todo-check { cursor: pointer; display: flex; align-items: center; gap: 10px; }

    /* Mood Buttons */
    .mood-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }

    /* Chat / Logs */
    .chat-box {
      max-height: 140px; overflow-y: auto; font-size: 13px; display: flex; flex-direction: column; gap: 8px;
      background: rgba(15,23,42,0.5); padding: 12px; border-radius: 10px;
    }
    .chat-msg { padding: 6px 10px; border-radius: 8px; }
    .chat-user { background: rgba(56,189,248,0.15); align-self: flex-end; color: #bae6fd; }
    .chat-pet { background: rgba(129,140,248,0.15); align-self: flex-start; color: #c7d2fe; }

    /* Telemetry row */
    .tele-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    .tele-card { background: rgba(15,23,42,0.6); padding: 10px; border-radius: 10px; text-align: center; }
    .tele-val { font-size: 15px; font-weight: 700; color: var(--primary); margin-top: 4px; }
    .tele-lbl { font-size: 11px; color: var(--text-muted); }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <h1>🐾 Q-WorkMate</h1>
        <span class="badge">Arduino UNO Q</span>
        <span class="badge" id="lbl-model">Gemini 3.8 Live</span>
      </div>
      <div style="display:flex;align-items:center;gap:10px;">
        <button class="btn-sm" id="btn-sound-toggle" style="padding:6px 12px;font-size:12px;" onclick="toggleSound()">🔊 語音: 開啟</button>
        <div class="status-pill">
          <div class="dot" id="net-dot"></div>
          <span id="lbl-phase">待命</span>
        </div>
      </div>
    </header>

    <div class="grid-2">
      <!-- 左欄: 8x13 LED 矩陣鏡像 + 語音大按鈕 -->
      <div class="card">
        <div class="card-title">
          <span>8x13 LED 實體矩陣鏡像</span>
          <span class="badge" id="lbl-mood">😊 笑臉</span>
        </div>
        <div class="matrix-box">
          <div class="matrix-grid" id="matrix-grid"></div>
        </div>

        <div class="card-title" style="margin-top: 4px;">🐾 AI 智慧互動快捷鍵</div>
        <div class="quick-cmd-grid">
          <button class="btn-sm" onclick="triggerQuickAI('pomodoro')">🍅 1分鐘專注</button>
          <button class="btn-sm" onclick="triggerQuickAI('break')">☕ 5分鐘小憩</button>
          <button class="btn-sm" onclick="triggerQuickAI('water')">💧 提醒喝水</button>
          <button class="btn-sm" onclick="triggerQuickAI('heart')">❤️ 撒嬌愛心</button>
          <button class="btn-sm" onclick="triggerQuickAI('status')">🌡️ 硬體狀態</button>
        </div>

        <div class="card-title" style="margin-top: 8px;">表情與情緒快速切換</div>
        <div class="mood-grid">
          <button class="btn-sm" onclick="setMood('heart')">❤️ 愛心</button>
          <button class="btn-sm" onclick="setMood('happy')">😄 大笑</button>
          <button class="btn-sm" onclick="setMood('water')">💧 喝水</button>
          <button class="btn-sm" onclick="setMood('coffee')">☕ 咖啡</button>
          <button class="btn-sm" onclick="setMood('sleep')">💤 睡覺</button>
          <button class="btn-sm" onclick="setMood('idle')">😊 微笑</button>
        </div>
      </div>

      <!-- 右欄: 番茄鐘 + 待辦事項 -->
      <div class="card">
        <div class="card-title">
          <span>🍅 專注番茄鐘 & ☕ 護眼小憩</span>
          <span class="badge" id="pomo-status">未啟動</span>
        </div>
        <div class="pomo-wrap">
          <div class="pomo-time" id="pomo-timer">25:00</div>
          <div class="pomo-bar"><div class="pomo-fill" id="pomo-fill"></div></div>
          <div class="pomo-btns">
            <button class="btn-sm" onclick="startTimer(1)">⚡ 1分專注</button>
            <button class="btn-sm" onclick="startTimer(25)">25分專注</button>
            <button class="btn-sm" onclick="startBreak(5)">☕ 5分小憩</button>
            <button class="btn-sm" onclick="startBreak(1)">⚡ 1分小憩</button>
            <button class="btn-sm" style="color:var(--danger)" onclick="stopTimer()">⏹️ 取消</button>
          </div>
        </div>

        <div class="card-title" style="margin-top: 8px;">
          <span>📝 語音備忘清單</span>
          <span class="badge" id="todo-count">0 項</span>
        </div>
        <div class="todo-input-wrap">
          <input type="text" class="todo-input" id="todo-input" placeholder="輸入待辦事項後按 Enter..." onkeydown="if(event.key==='Enter') addTodo()">
          <button class="btn-sm" style="flex:0 0 60px" onclick="addTodo()">新增</button>
        </div>
        <ul class="todo-list" id="todo-list"></ul>
      </div>
    </div>

    <!-- 底部: 即時遙測與歷史對話 -->
    <div class="grid-2">
      <div class="card">
        <div class="card-title">板載遙測狀態 (Hardware Telemetry)</div>
        <div class="tele-grid">
          <div class="tele-card"><div class="tele-lbl">CPU 溫度</div><div class="tele-val" id="tele-temp">-- °C</div></div>
          <div class="tele-card"><div class="tele-lbl">可用記憶體</div><div class="tele-val" id="tele-mem">-- MB</div></div>
          <div class="tele-card"><div class="tele-lbl">開機時間</div><div class="tele-val" id="tele-uptime">--</div></div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">即時語音與文字對話紀錄</div>
        <div class="chat-box" id="chat-box">
          <div class="chat-pet">🐾 Q-Pet: 主人你好！我是你的桌面生產力桌寵，你可以按住上方按鈕說話，或直接在下方打字喔！</div>
        </div>
        <div class="todo-input-wrap">
          <input type="text" class="todo-input" id="chat-input" placeholder="打字跟 Q-Pet 說話 (例如: 現在溫度如何、設定1分鐘專注)..." onkeydown="if(event.key==='Enter') sendChat()">
          <button class="btn-sm" style="flex:0 0 60px" onclick="sendChat()">傳送</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    // 建立 8x13 點陣像素 DOM
    const grid = document.getElementById('matrix-grid');
    for (let i = 0; i < 104; i++) {
      const led = document.createElement('div');
      led.className = 'led';
      led.id = 'led-' + i;
      grid.appendChild(led);
    }

    // 狀態輪詢與鏡像同步
    let lastWavLen = 0;
    let lastHandledTurnIndex = -1;
    let initialSyncDone = false;
    async function syncState() {
      try {
        const res = await fetch('/state');
        if (!res.ok) return;
        const data = await res.json();
        
        // 更新點陣像素
        if (data.matrix && data.matrix.length === 104) {
          for (let i = 0; i < 104; i++) {
            const el = document.getElementById('led-' + i);
            const val = data.matrix[i];
            el.className = 'led' + (val > 0 ? (val >= 6 ? ' on-4' : val >= 4 ? ' on-3' : val >= 2 ? ' on-2' : ' on-1') : '');
          }
        }

        // 更新狀態文字與燈號
        const phaseEl = document.getElementById('lbl-phase');
        const dotEl = document.getElementById('net-dot');
        if (data.phase === 'error') {
          phaseEl.textContent = '⚠️ ' + (data.msg || '連線錯誤 (請檢查金鑰)');
          dotEl.style.background = 'var(--danger)';
          dotEl.style.boxShadow = '0 0 10px var(--danger)';
        } else {
          phaseEl.textContent = data.phase === 'listening' ? '正在傾聽...' : data.phase === 'thinking' ? '思考運算中...' : data.phase === 'speaking' ? '正在回答' : '待命';
          dotEl.style.background = 'var(--success)';
          dotEl.style.boxShadow = '0 0 10px var(--success)';
        }

        document.getElementById('lbl-mood').textContent = data.mood || 'idle';
        document.getElementById('lbl-model').textContent = data.model || 'Gemini Live';

        // 更新遙測數值
        if (data.telemetry) {
          if (data.telemetry.cpu_temperature) document.getElementById('tele-temp').textContent = data.telemetry.cpu_temperature;
          if (data.telemetry.memory_available) document.getElementById('tele-mem').textContent = data.telemetry.memory_available;
          if (data.telemetry.uptime) document.getElementById('tele-uptime').textContent = data.telemetry.uptime;
        }

        // 更新番茄鐘與小憩
        if (data.pomodoro) {
          const p = data.pomodoro;
          if (p.active) {
            const m = Math.floor(p.remaining_seconds / 60);
            const s = p.remaining_seconds % 60;
            document.getElementById('pomo-timer').textContent = `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
            document.getElementById('pomo-fill').style.width = (p.progress * 100) + '%';
            if (p.mode === 'break') {
              document.getElementById('pomo-fill').style.background = 'linear-gradient(90deg, #10b981, #06b6d4)';
              document.getElementById('pomo-status').textContent = '☕ 小憩中: ' + p.label;
              document.getElementById('pomo-status').style.background = 'rgba(16, 185, 129, 0.2)';
              document.getElementById('pomo-status').style.color = '#34d399';
            } else {
              document.getElementById('pomo-fill').style.background = 'linear-gradient(90deg, var(--danger), var(--warning))';
              document.getElementById('pomo-status').textContent = '🍅 專注中: ' + p.label;
              document.getElementById('pomo-status').style.background = 'rgba(239, 68, 68, 0.2)';
              document.getElementById('pomo-status').style.color = '#f87171';
            }
          } else {
            document.getElementById('pomo-timer').textContent = '25:00';
            document.getElementById('pomo-fill').style.width = '0%';
            document.getElementById('pomo-fill').style.background = 'linear-gradient(90deg, var(--danger), var(--warning))';
            document.getElementById('pomo-status').textContent = '待命中';
            document.getElementById('pomo-status').style.background = 'rgba(255, 255, 255, 0.08)';
            document.getElementById('pomo-status').style.color = 'var(--text-muted)';
          }
        }

        // 更新待辦清單
        if (data.todos) {
          renderTodos(data.todos);
        }

        // 檢查語音回覆音訊播放 (Web 模式) 與對話紀錄同步
        if (data.turns && data.turns.length > 0) {
          if (!initialSyncDone) {
            initialSyncDone = true;
            lastHandledTurnIndex = data.turns.length - 1;
          } else {
            const turnIdx = data.turns.length - 1;
            const curTurn = data.turns[turnIdx];
            if (turnIdx > lastHandledTurnIndex) {
              if (curTurn.reply || (curTurn.tools && curTurn.tools.length > 0) || curTurn.wav_len > 0 || data.phase === 'idle') {
                lastHandledTurnIndex = turnIdx;
                if (!curTurn.isQuickAi) {
                  let petReply = curTurn.reply;
                  if (!petReply && curTurn.tools && curTurn.tools.length > 0) {
                    const t = curTurn.tools[0];
                    if (t.name === 'start_focus_timer') petReply = '好的！已為您啟動 ' + (t.args.minutes || 25) + ' 分鐘專注番茄鐘 🍅';
                    else if (t.name === 'cancel_focus_timer') petReply = '已為您取消專注番茄鐘 ⏹️';
                    else if (t.name === 'set_pet_mood') petReply = '已為您切換桌寵表情：' + t.args.mood + ' ✨';
                    else if (t.name === 'add_todo') petReply = '已為您記錄待辦事項：' + t.args.task + ' 📝';
                    else if (t.name === 'remind_hydration') petReply = '主人辛苦了，記得喝杯水休息一下喔 💧';
                    else if (t.name === 'get_board_status') petReply = '目前硬體運作正常，CPU 溫度約 ' + (data.telemetry?.cpu_temperature || '正常');
                    else petReply = '收到指令，已執行：' + t.name;
                  }
                  if (!petReply) {
                    petReply = '🐾 收到！已為您處理完畢！';
                  }
                  appendChat('pet', petReply);
                }
                
                if (curTurn.wav_len > 0 && soundEnabled) {
                  const audio = new Audio('/reply.wav?t=' + Date.now());
                  audio.play().catch(e => console.log('Audio playback info:', e));
                }
              }
            }
          }
        }
      } catch (err) {
        console.error('syncState error:', err);
      }
    }
    setInterval(syncState, 500);
    syncState();

    // 遙測輪詢
    async function syncTelemetry() {
      try {
        const res = await fetch('/state');
        const data = await res.json();
        const t = data.turns?.find(x => x.tools?.some(tool => tool.name === 'get_board_status'));
        // 也可以透過定期打 API 拿溫度
      } catch (e) {}
    }

    function renderTodos(items) {
      document.getElementById('todo-count').textContent = items.length + ' 項';
      const list = document.getElementById('todo-list');
      list.innerHTML = items.map(t => `
        <li class="todo-item ${t.done ? 'done' : ''}">
          <span class="todo-check" onclick="toggleTodo(${t.id})">
            <span>${t.done ? '✅' : '⚪'}</span>
            <span>${t.text}</span>
          </span>
          <span style="font-size:11px;color:var(--text-muted)">${t.time || ''}</span>
        </li>
      `).join('');
    }

    async function addTodo() {
      const inp = document.getElementById('todo-input');
      const val = inp.value.trim();
      if (!val) return;
      inp.value = '';
      await fetch('/api/todo/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({task: val})
      });
      syncState();
    }

    async function toggleTodo(id) {
      await fetch('/api/todo/toggle', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id})
      });
      syncState();
    }

    async function startTimer(min) {
      await fetch('/api/timer/start', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({minutes: min, label: '專注工作'})
      });
      syncState();
    }

    async function startBreak(min) {
      await fetch('/api/timer/break', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({minutes: min, label: '護眼小憩'})
      });
      syncState();
    }

    async function stopTimer() {
      await fetch('/api/timer/stop', {method: 'POST'});
      syncState();
    }

    async function setMood(m) {
      await fetch('/api/mood', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({mood: m})
      });
      syncState();
    }

    async function triggerQuickAI(action) {
      if (action === 'pomodoro') {
        appendChat('user', '幫我設定 1 分鐘專注工作番茄鐘');
        appendChat('pet', '好的！已為主人啟動 1 分鐘專注番茄鐘 🍅');
        await startTimer(1);
        sendChatText('我啟動了1分鐘專注工作番茄鐘，請用可愛桌寵語氣為我加油打氣一句話', false);
      } else if (action === 'break') {
        appendChat('user', '幫我設定 5 分鐘小憩放鬆');
        appendChat('pet', '主人辛苦了！已為您啟動 5 分鐘護眼小憩 ☕ 記得站起來伸展筋骨、遠眺放鬆喔！');
        await startBreak(5);
        sendChatText('我啟動了5分鐘小憩放鬆，請用可愛桌寵語氣提醒我活動筋骨與護眼遠眺一句話', false);
      } else if (action === 'water') {
        appendChat('user', '提醒我喝水休息');
        appendChat('pet', '主人辛苦了！記得喝口溫開水、休息一下喔 💧');
        await setMood('water');
        sendChatText('提醒我喝水休息，請用可愛桌寵語氣簡短關心我一句', false);
      } else if (action === 'heart') {
        appendChat('user', '做一個愛心表情給我看');
        appendChat('pet', '愛你唷主人！已為您送上撒嬌愛心 ❤️');
        await setMood('heart');
        sendChatText('做一個愛心表情給我看，用撒嬌語氣說一句喜歡主人', false);
      } else if (action === 'status') {
        appendChat('user', '現在板載溫度與硬體狀態如何');
        try {
          const res = await fetch('/state');
          const data = await res.json();
          const temp = data.telemetry?.cpu_temperature || '37.3 °C';
          const mem = data.telemetry?.memory_available || '3000 MB';
          appendChat('pet', `目前 Arduino UNO Q 硬體狀態良好！CPU 溫度 ${temp}，可用記憶體 ${mem} 🌡️`);
        } catch(e) {
          appendChat('pet', '硬體運作正常，系統狀態良好 🌡️');
        }
        sendChatText('查詢硬體狀態，簡短回報系統運作很健康', false);
      }
    }

    async function sendChatText(txt, addToUi = true) {
      if (!txt) return;
      if (addToUi) {
        appendChat('user', txt);
      }
      const phaseEl = document.getElementById('lbl-phase');
      if (phaseEl) phaseEl.textContent = '思考運算中...';
      try {
        await fetch('/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({text: txt, isQuickAi: !addToUi})
        });
      } catch(e) {
        console.error('Chat error:', e);
      }
      syncState();
    }

    async function sendChat() {
      const inp = document.getElementById('chat-input');
      const txt = inp.value.trim();
      if (!txt) return;
      inp.value = '';
      await sendChatText(txt);
    }

    function appendChat(role, text) {
      const box = document.getElementById('chat-box');
      const div = document.createElement('div');
      div.className = 'chat-msg ' + (role === 'user' ? 'chat-user' : 'chat-pet');
      div.textContent = (role === 'user' ? '🧑 主人: ' : '🐾 Q-Pet: ') + text;
      box.appendChild(div);
      box.scrollTop = box.scrollHeight;
    }

    // 語音播放開關 (預設開啟)
    let soundEnabled = true;
    function toggleSound() {
      soundEnabled = !soundEnabled;
      const btn = document.getElementById('btn-sound-toggle');
      if (btn) btn.textContent = soundEnabled ? '🔊 語音: 開啟' : '🔇 語音: 靜音';
    }
  </script>
</body>
</html>
"""


@app.get("/")
async def get_index():
    return HTMLResponse(DASHBOARD_HTML)


if __name__ == "__main__":
    logger.info("Starting Q-WorkMate agent on port %s...", PORT)
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
