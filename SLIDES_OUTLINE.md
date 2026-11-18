# 🐾 AIoT 期中專題簡報大綱 (Presentation Slides Outline)

**專題題目**：Q-WorkMate / LumiPet：基於 Arduino UNO Q 雙核邊緣運算與 Gemini Live 之 AI 智慧生產力桌寵  
**投影片檔案**：[AIoT_Midterm_Q-WorkMate.pptx](file:///f:/Antigravity/AIoT_midterm_project/AIoT_Midterm_Q-WorkMate.pptx)  
**開源專案網址**：https://github.com/411221305/115-1_AIOT_Q-WorkMate  

---

## 投影片頁數結構 (共 9 頁，16:9 專業科技暗色調)

### 📌 第 1 頁：封面 (Title & Overview)
- **專案名稱**：`Q-WorkMate / LumiPet`
- **副標題**：基於 Arduino UNO Q 雙核心架構與 Gemini Live 之 AI 智慧生產力桌寵
- **核心技術**：Arduino UNO Q · Qualcomm Dragonwing ARM64 · STM32U585 MCU · Zephyr RTOS · Gemini 3.8 Live API · FastAPI
- **去識別化確認**：嚴格無學生姓名與學號，附上公開 GitHub 倉庫連結。

---

### 📌 第 2 頁：動機與問題痛點 (Motivation & Problem)
- **現有產品痛點**：
  - 現有語音助理（Siri / Alexa）多為無螢幕或冷冰冰音響，缺乏實體桌面的情緒陪伴感。
  - 傳統桌面番茄鐘功能孤立、無自然語言溝通能力，無法動態調整時程。
  - 長時間遠距伏案工作容易缺乏規律休息提醒，導致久坐疲勞與用眼過度。
- **Q-WorkMate 的創新解方**：
  - 打造「住在晶片裡的實體 AI 伴侶」，8x13 點陣表情賦予生命感。
  - 結合多階段時程表，兼具「專注番茄鐘」與「護眼小憩管家」。
  - 善用 UNO Q 純板載硬體（LED 點陣、RGB 氛圍燈、熱感測器），無需外接零件即可達成極高完成度。

---

### 📌 第 3 頁：雙核心異質硬體架構 (Dual-Brain Hardware Architecture)
- **Linux 應用運算層 (High-Level Intelligence)**：
  - Qualcomm Dragonwing QRB2210 (4x ARM Cortex-A53 @ Debian 13 Linux)。
  - 負責 Docker 容器化 Agent、FastAPI 伺服器、WebSocket 直連 Gemini 3.8 Live。
- **STM32 即時控制層 (Real-Time Control)**：
  - STMicroelectronics STM32U585 (ARM Cortex-M33 @ Zephyr RTOS)。
  - 透過 `Arduino_RouterBridge` RPC 響應 `draw` 指令，微秒級精準驅動 8x13 LED 矩陣。
- **板載人機互動模組 (Peripherals)**：
  - 8x13 藍色 LED 點陣（104 顆獨立亮度 LED，0~7 階灰階）。
  - 板載 RGB 氛圍指示燈（專注紅、小憩青藍、完成綠、思考藍）。

---

### 📌 第 4 頁：軟體與雲端通訊架構 (Software & Cloud AI)
- **Gemini 3.8 Live 雙向即時串流**：
  - 使用 `BidiGenerateContent` WebSocket 協議，低延遲雙向即時對話。
  - 繁體中文情感人設（活潑親切的專屬桌寵 Persona）。
  - Function Calling 工具庫：`start_focus_timer`、`start_break_timer`、`set_schedule`、`add_todo`、`get_board_status`。
- **跨行程 Bridge RPC 橋接管道**：
  - 容器透過 `/var/run/arduino-router.sock` 通訊。
  - MsgPack 二進制協議封裝：將 104 點陣像素轉化為 `bytes(frame)` 二進制型別，對齊 C++ `std::vector<uint8_t>`。
  - 表情保護機制（`_temp_mood_until`）：解決語音 `speaking` 覆蓋特殊表情動畫的並行衝突。

---

### 📌 第 5 頁：核心功能一：時程表與番茄鐘 (Focus & Break Timeline)
- **專注番茄鐘與 5 分鐘小憩**：
  - 26 格即時動態進度格條。
  - 獨家雙幀「熱氣蒸騰冒煙熱咖啡杯（☕）」動畫。
  - 20-20-20 護眼伸展指引，專注紅燈與小憩青藍呼吸燈沉浸式切換。
- **自然語言時程表排程 (Timeline Queue)**：
  - 口語化輸入：「先專注寫作業 25 分鐘，再休息 5 分鐘，接著專注 25 分鐘」，AI 自動拆解多階段時程。
  - 第一階段倒數完畢後，系統自動無縫銜接至第二階段並切換表情與燈效。
  - 支援「⚡ 測試時程 (1分+1分)」方便錄影演示，亦支援手動追加與隨時暫停。

---

### 📌 第 6 頁：核心功能二：情緒引擎與備忘清單 (Emotions & Memo)
- **8x13 擬人化動態表情引擎**：
  - 待命呼吸笑臉（每 3.5 秒自動眨眼）、雷達旋轉思考波形、心跳撒嬌愛心、定時喝水提醒、睡眠呼嚕 (Zzz)。
- **智慧備忘清單與任務管理**：
  - 隨手新增備忘，任務完成時點陣播放立體打勾（✔）動畫！
  - 每一筆事項具備獨立 `🗑️` 刪除按鈕，標題列提供 `🧹 清除已完成` 一鍵整理。
  - JSON 檔案本地持久化於板載 eMMC，重啟後不遺失。

---

### 📌 第 7 頁：Web 現代化雙向互動儀表板 (Interactive Dashboard)
- **1:1 虛擬點陣螢幕鏡像 (Matrix Mirror)**：瀏覽器即時同步 UNO Q 實體 LED 矩陣每一幀。
- **AI 智慧快捷指令卡**：一鍵觸發 1分鐘專注、5分鐘小憩、規劃時程、喝水提醒、撒嬌愛心、硬體狀態。
- **即時全雙工對話框**：文字輸入與桌寵回答氣泡紀錄，支援語音播放與一鍵靜音切換。
- **板載硬體即時遙測**：CPU 溫度 (℃)、可用記憶體 (MB)、運行時間與負載平均值。

---

### 📌 第 8 頁：關鍵技術挑戰與解決方案 (Technical Challenges)
1. **跨晶片 Bridge RPC 型別不相容**：改採 `bytes(frame)` 成功適配 Zephyr C++ `std::vector<uint8_t>`。
2. **多線程動畫與語音講話狀態衝突**：設計 `_temp_mood_until` 時間保護鎖，避免語音串流瞬間覆蓋表情。
3. **純文字輸入與 Gemini Live 協議適配**：後端封裝 `clientContent` 封包，並在工具執行後合成精準中文回覆。
4. **極致硬體壓榨**：完全不依賴外接額外零件，純利用板載資源達到軟硬整合頂級水準。

---

### 📌 第 9 頁：成果總結與未來展望 (Summary & Roadmap)
- **專題成果總結**：
  - 100% 達成專案指標，打造具備生命力與生產力閉環的 AI 桌面伴侶。
  - 融合異質雙核心 (Linux + RTOS)、RPC 橋接、Gemini 3.8 Live、Docker 與 FastAPI。
  - 嚴格遵守資安與開源標準，程式碼已同步至 GitHub。
- **未來展望**：
  - 接入 USB 鏡頭達成視線與坐姿追蹤。
  - 結合 BLE 廣播推播至智慧手錶。
  - 透過 Qwiic 介面外接環境溫濕度與 CO2 感測器。
