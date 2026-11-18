# AIoT 期中專題簡報大綱 (Slides Outline)
專題題目：**Q-WorkMate / LumiPet：基於 Arduino UNO Q 雙核邊緣運算與 Gemini Live 之 AI 智慧生產力桌寵**

---

## 投影片頁數規劃（建議 8 ~ 10 頁，簡明扼要、結構完整）

### 【第 1 頁：封面 (Title)】
- **專案名稱**：Q-WorkMate / LumiPet
- **副標題**：基於 Arduino UNO Q 雙核心架構與 Gemini Live 之 AI 智慧生產力桌寵
- **核心技術標籤**：Arduino UNO Q · Qualcomm Dragonwing · STM32U585 · Zephyr RTOS · Gemini Live · Bridge RPC · FastAPI

---

### 【第 2 頁：動機與背景 (Motivation & Problem)】
- **痛點現況**：
  - 現有的智慧語音助理（如 Siri, Alexa）多為純語音或冷冰冰的螢幕介面，缺乏實體桌面伴隨感。
  - 傳統桌面番茄鐘或小夜燈功能單一、缺乏互動與自然語言理解。
  - 現代學生與遠距工作者長時間面對電腦，容易因缺乏定時專注與休息提醒而產生疲倦感。
- **我們的想法**：
  - 打造一隻**住在硬體裡的實體 AI 伴侶**，既具備陪伴情緒價值，又是一個稱職的「專注番茄鐘」與「語音隨手筆記管家」。

---

### 【第 3 頁：系統硬體架構 (Hardware Architecture)】
- **使用平台**：Arduino UNO Q 旗艦開發板
- **雙核心異質架構優勢**：
  1. **MPU 應用處理端**：Qualcomm Dragonwing QRB2210 (Quad-core Cortex-A53 @ Debian 13 Linux)，負責高階網路串流、Docker 容器與 Gemini 多模態語音處理。
  2. **MCU 即時控制端**：STMicroelectronics STM32U585 (Cortex-M33 @ Zephyr RTOS)，負責 8x13 LED 矩陣的微秒級即時掃描更新。
  3. **板載人機介面**：8x13 藍色 LED 點陣（繪製動態表情與計時進度條）+ 板載 RGB LED（提供心情光影氛圍）。

---

### 【第 4 頁：軟體與通訊架構 (Software & Communication)】
- **三大核心通訊閉環**：
  1. **雲端大腦 (Cloud Intelligence)**：
     - 使用 Google Gemini Live WebSocket 協議（`BidiGenerateContent`），達成低延遲雙向即時對話。
     - 整合自訂 Function Calling 工具集（番茄鐘、待辦事項、狀態感知）。
  2. **邊緣運算與後台 (Edge Backend)**：
     - FastAPI + WebSocket 構建輕量後台。
     - 雙模音訊管線（支援 UAC2 USB 音效卡與 WebRTC 瀏覽器麥克風）。
  3. **跨晶片橋接 (Bridge RPC)**：
     - 利用 `Arduino_RouterBridge` 透過 Unix Domain Socket (`/var/run/arduino-router.sock`) 呼叫 MCU 端的 `draw` 介面，將 Python 像素幀轉譯為硬體顯示。

---

### 【第 5 頁：核心功能展示 (Core Features)】
- **1. 擬人化動態表情系統**：
  - 待命眨眼、專注傾聽、雷達旋轉思考、說話音波、愛心讚許、打哈欠睡覺。
- **2. 智慧番茄鐘專注助手**：
  - 語音自訂分鐘數；點陣動態顯現 26 階進度格條；倒數結束自動觸發喝水休息語音。
- **3. 語音隨手待辦備忘錄**：
  - 說一句話即可新增待辦；隨時查詢未完成任務；網頁看板即時同步劃掉。
- **4. 硬體遙測與溫度感知**：
  - AI 隨時讀取核心晶片熱感測器 (`/sys/class/thermal`)，關心板子也關心主人。

---

### 【第 6 頁：Web 互動儀表板 (Interactive Dashboard)】
- **視覺化三大模組**：
  - **虛擬點陣螢幕鏡像 (Matrix Mirror)**：網頁上 1:1 實時還原 UNO Q 實體 LED 矩陣亮度與動畫。
  - **生產力控制中心**：一鍵啟動 15/25/45 分鐘番茄鐘、即時待辦事項新增與勾選。
  - **即時遙測儀表**：CPU 溫度、可用記憶體、系統運行時間即時監看。

---

### 【第 7 頁：技術難點與解決方案 (Challenges & Solutions)】
- **難點 1：跨晶片 Bridge RPC 參數型別適配**
  - *問題*：Python 端傳送一般 list 時，MsgPack 轉發型別不匹配 (`RpcError: Wrong type parameter`)。
  - *解法*：將 Python 數組打包為 `bytes(frame)` 二進制型別，成功契合 C++ `std::vector<uint8_t>`。
- **難點 2：雙模音訊適配與無外接音效卡相容**
  - *解法*：架構內建 WebRTC AudioContext 擷取機制，讓電腦即使未設定 USB 聆聽裝置也能透過瀏覽器流暢對話。
- **難點 3：非同步動畫與語音對話不衝突**
  - *解法*：將點陣動畫引擎獨立為守護執行緒 (`threading.Thread`)，與 FastAPI/Gemini WebSocket 異步迴圈解耦，保持極致順暢。

---

### 【第 8 頁：成果總結與未來展望 (Summary & Future Work)】
- **成果總結**：
  - 100% 達成自主定義之專題目標。
  - 善用 UNO Q 雙核軟硬體潛能，不需額外感測器即呈現最高水準的軟硬整合。
  - 符合無金鑰、無學號姓名之資安標準。
- **未來展望**：
  - 接入 USB 視訊鏡頭實現臉部追蹤與視線對焦。
  - 結合 BLE 廣播，將番茄鐘進度推播至智慧手錶或手機 App。
