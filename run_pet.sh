#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Q-WorkMate / LumiPet 一鍵啟動腳本 (在 UNO Q 板上執行)

set -e

# 檢查金鑰檔案
if [ ! -f "$HOME/.gemini_key" ]; then
    echo "⚠️ 尚未在 ~/.gemini_key 找到 Gemini 金鑰！"
    echo "請先執行: read -s -p '請貼上 Gemini API Key: ' K; printf %s \"\$K\" > ~/.gemini_key; chmod 600 ~/.gemini_key; echo"
    exit 1
fi

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMG=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep python-apps-base | head -1)

if [ -z "$IMG" ]; then
    echo "❌ 找不到 python-apps-base 映像檔！"
    exit 1
fi

echo "🚀 正在使用映像檔 $IMG 啟動 Q-WorkMate AI 桌面生產力桌寵..."
echo "📍 專案目錄: $APP_DIR"

# 確保先前的容器已清除
docker rm -f qpet 2>/dev/null || true

# 啟動容器
docker run --rm -it \
    --name qpet \
    -u 0 \
    --network host \
    --device /dev/snd \
    -v "$APP_DIR":/app \
    -v "$HOME/.gemini_key":/key:ro \
    -v /var/run/arduino-router.sock:/var/run/arduino-router.sock \
    -v /sys/devices/platform/leds/leds:/sys/devices/platform/leds/leds \
    -e KEY_FILE=/key \
    -e CARD=plughw:UAC2Gadget,0 \
    -e PORT=7790 \
    --entrypoint python3 \
    "$IMG" /app/desk_pet_agent.py
