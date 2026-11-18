# SPDX-License-Identifier: MIT
"""Generate Professional 16:9 Presentation Slides for AIoT Midterm Project."""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# 16:9 Widescreen dimensions
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

# Color Palette
BG_COLOR = RGBColor(15, 23, 42)        # #0F172A
CARD_BG = RGBColor(30, 41, 59)         # #1E293B
CARD_BORDER = RGBColor(51, 65, 85)     # #334155
TEXT_WHITE = RGBColor(241, 245, 249)   # #F1F5F9
TEXT_MUTED = RGBColor(148, 163, 184)   # #94A3B8
COLOR_CYAN = RGBColor(56, 189, 248)    # #38BDF8
COLOR_INDIGO = RGBColor(129, 140, 248) # #818CF8
COLOR_GREEN = RGBColor(52, 211, 153)   # #34D399
COLOR_AMBER = RGBColor(251, 191, 36)   # #FBBF24
COLOR_RED = RGBColor(248, 113, 113)    # #F87171

FONT_TITLE = "Microsoft JhengHei"
FONT_BODY = "Microsoft JhengHei"


def set_bg(slide):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT)
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG_COLOR
    bg.line.fill.background()
    return bg


def add_header(slide, title: str, category: str = "AIoT MIDTERM PROJECT"):
    # Category tag
    tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.45), Inches(8), Inches(0.35))
    tf_tag = tag_box.text_frame
    tf_tag.word_wrap = True
    p_tag = tf_tag.paragraphs[0]
    p_tag.text = category.upper()
    p_tag.font.name = FONT_TITLE
    p_tag.font.size = Pt(11)
    p_tag.font.bold = True
    p_tag.font.color.rgb = COLOR_CYAN

    # Main Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11), Inches(0.8))
    tf_title = title_box.text_frame
    tf_title.word_wrap = True
    p_title = tf_title.paragraphs[0]
    p_title.text = title
    p_title.font.name = FONT_TITLE
    p_title.font.size = Pt(24)
    p_title.font.bold = True
    p_title.font.color.rgb = TEXT_WHITE

    # Divider line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.6), Inches(11.733), Inches(0.02))
    line.fill.solid()
    line.fill.fore_color.rgb = CARD_BORDER
    line.line.fill.background()


def add_card(slide, left, top, width, height, title: str, items: list, accent_color=COLOR_CYAN):
    # Card Background shape
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = CARD_BG
    card.line.color.rgb = CARD_BORDER
    card.line.width = Pt(1)

    # Text container
    tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.2), width - Inches(0.4), height - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP

    # Title
    p_title = tf.paragraphs[0]
    p_title.text = title
    p_title.font.name = FONT_TITLE
    p_title.font.size = Pt(16)
    p_title.font.bold = True
    p_title.font.color.rgb = accent_color
    p_title.space_after = Pt(10)

    # Bullet points
    for item in items:
        p = tf.add_paragraph()
        p.text = "• " + item
        p.font.name = FONT_BODY
        p.font.size = Pt(12.5)
        p.font.color.rgb = TEXT_WHITE
        p.space_after = Pt(6)


def build_presentation(output_path: str):
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    blank_layout = prs.slide_layouts[6]

    # ------------------------------------------------------------- Slide 1: 封面
    s1 = prs.slides.add_slide(blank_layout)
    set_bg(s1)

    # Badge Pill
    pill = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(1.4), Inches(3.6), Inches(0.45))
    pill.fill.solid()
    pill.fill.fore_color.rgb = RGBColor(30, 58, 95)
    pill.line.color.rgb = COLOR_CYAN
    tf_pill = pill.text_frame
    p_pill = tf_pill.paragraphs[0]
    p_pill.text = "⚡ Arduino UNO Q × Gemini 3.8 Live"
    p_pill.font.name = FONT_TITLE
    p_pill.font.size = Pt(12)
    p_pill.font.bold = True
    p_pill.font.color.rgb = COLOR_CYAN
    p_pill.alignment = PP_ALIGN.CENTER

    # Project Title
    tb1 = s1.shapes.add_textbox(Inches(1.0), Inches(2.1), Inches(11.3), Inches(1.6))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.text = "Q-WorkMate / LumiPet"
    p1.font.name = FONT_TITLE
    p1.font.size = Pt(44)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE

    p1_sub = tf1.add_paragraph()
    p1_sub.text = "基於 Arduino UNO Q 雙核邊緣運算與 Gemini Live 之 AI 智慧生產力桌寵"
    p1_sub.font.name = FONT_TITLE
    p1_sub.font.size = Pt(20)
    p1_sub.font.color.rgb = COLOR_CYAN
    p1_sub.space_before = Pt(8)

    # Overview box
    box_desc = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(4.0), Inches(11.3), Inches(1.6))
    box_desc.fill.solid()
    box_desc.fill.fore_color.rgb = CARD_BG
    box_desc.line.color.rgb = CARD_BORDER
    tf_desc = box_desc.text_frame
    tf_desc.word_wrap = True
    p_desc1 = tf_desc.paragraphs[0]
    p_desc1.text = "專案核心特色："
    p_desc1.font.name = FONT_TITLE
    p_desc1.font.size = Pt(14)
    p_desc1.font.bold = True
    p_desc1.font.color.rgb = COLOR_INDIGO
    p_desc1.space_after = Pt(4)

    p_desc2 = tf_desc.add_paragraph()
    p_desc2.text = "8x13 LED 實體動態表情 · 冒煙咖啡杯護眼小憩 · 專注與休息時程表 · 繁中自然語言排程 · 即時硬體遙測"
    p_desc2.font.name = FONT_BODY
    p_desc2.font.size = Pt(13)
    p_desc2.font.color.rgb = TEXT_WHITE

    p_desc3 = tf_desc.add_paragraph()
    p_desc3.text = "GitHub 開源專案：https://github.com/411221305/115-1_AIOT_Q-WorkMate"
    p_desc3.font.name = FONT_BODY
    p_desc3.font.size = Pt(12)
    p_desc3.font.color.rgb = COLOR_GREEN
    p_desc3.space_before = Pt(6)

    # Footer note
    ft = s1.shapes.add_textbox(Inches(1.0), Inches(6.0), Inches(11.3), Inches(0.5))
    p_ft = ft.text_frame.paragraphs[0]
    p_ft.text = "115-1 AIoT 課程期中專題報告 · 完整去識別化開源作品"
    p_ft.font.name = FONT_TITLE
    p_ft.font.size = Pt(11)
    p_ft.font.color.rgb = TEXT_MUTED

    # ------------------------------------------------------------- Slide 2: 動機與問題
    s2 = prs.slides.add_slide(blank_layout)
    set_bg(s2)
    add_header(s2, "研究動機與痛點分析 (Motivation & Problem)")

    add_card(s2, Inches(0.8), Inches(1.9), Inches(5.6), Inches(4.8), "❌ 現有產品的局限與痛點", [
        "智慧音箱冷冰冰：多為無螢幕或制式介面，缺乏實體桌面的情緒伴隨感。",
        "傳統番茄鐘功能孤立：機械式倒數，無法動態調整時程，也無法用語音或文字自然溝通。",
        "長時間伏案工作疲倦：學生與工作者常忘記適度休息，容易產生久坐疲倦與用眼過度。",
        "邊緣運算潛力未發揮：市面小型物聯網裝置多依賴雲端全代管，缺乏即時反應與硬體聯動。"
    ], COLOR_RED)

    add_card(s2, Inches(6.9), Inches(1.9), Inches(5.6), Inches(4.8), "💡 Q-WorkMate 的創新解方", [
        "有溫度的心靈桌寵：住在 UNO Q 晶片中的智慧桌面精靈，8x13 點陣提供生動眨眼與笑臉。",
        "科學化生產力時程表：串聯專注番茄鐘與護眼小憩，支援自然語言口語化多階段自動排程。",
        "雙核心異質無縫協同：Linux 高階大腦負責 AI 與網路，STM32U5 負責微秒級零延遲硬體動畫。",
        "純軟體免外接零件：完美善用板載 8x13 LED 矩陣與 RGB 氛圍燈，無須外接麵包板即達極高完成度。"
    ], COLOR_GREEN)

    # ------------------------------------------------------------- Slide 3: 雙核心硬體架構
    s3 = prs.slides.add_slide(blank_layout)
    set_bg(s3)
    add_header(s3, "雙核心異質硬體架構 (Dual-Brain Hardware)")

    add_card(s3, Inches(0.8), Inches(1.9), Inches(3.7), Inches(4.8), "🧠 Linux 應用運算層", [
        "晶片：Qualcomm Dragonwing QRB2210",
        "核心：Quad-core ARM Cortex-A53",
        "作業系統：Debian 13 Linux",
        "記憶體：4GB LPDDR4 / 16GB eMMC",
        "職責分工：",
        "• 執行 Docker 容器化 Agent",
        "• FastAPI 輕量非同步 Web 伺服器",
        "• WebSocket 直連 Gemini 3.8 Live",
        "• 讀取 /sys 溫度與記憶體遙測數據"
    ], COLOR_CYAN)

    add_card(s3, Inches(4.8), Inches(1.9), Inches(3.7), Inches(4.8), "⚡ STM32 即時控制層", [
        "晶片：STMicroelectronics STM32U585",
        "核心：ARM Cortex-M33 @ 160MHz",
        "即時系統：Zephyr RTOS",
        "通訊通道：Arduino RouterBridge RPC",
        "職責分工：",
        "• 註冊並響應 draw 遠端過程調用",
        "• 毫秒級更新 8x13 LED 點陣顯存",
        "• 精準呼吸光與多層幀動畫繪製",
        "• 保證即使 Linux 忙碌仍不卡頓"
    ], COLOR_INDIGO)

    add_card(s3, Inches(8.8), Inches(1.9), Inches(3.7), Inches(4.8), "💡 板載人機互動模組", [
        "8x13 藍色 LED 點陣矩陣：",
        "• 共 104 顆獨立亮度 LED",
        "• 支援 0~7 階動態灰階明暗變化",
        "• 繪製待命眨眼、冒煙咖啡、進度條",
        "板載 RGB 氛圍指示燈：",
        "• 熱血專注紅：番茄鐘倒數中",
        "• 放鬆青藍色：5分鐘小憩護眼",
        "• 活力翠綠色：待辦事項打勾慶祝",
        "• 思考閃爍藍：AI 即時雲端運算"
    ], COLOR_AMBER)

    # ------------------------------------------------------------- Slide 4: 軟體與雲端通訊
    s4 = prs.slides.add_slide(blank_layout)
    set_bg(s4)
    add_header(s4, "軟體架構與 Gemini Live 整合 (Software & Cloud AI)")

    add_card(s4, Inches(0.8), Inches(1.9), Inches(5.6), Inches(4.8), "☁️ Gemini 3.8 Live 雙向即時串流", [
        "WebSocket 雙向傳輸：使用 Google BidiGenerateContent 協議，極低延遲即時回應。",
        "繁體中文情感人設：專屬桌寵 Persona，活潑熱情、用詞精準，隨時關懷主人身心狀態。",
        "Function Calling 工具自主決策：",
        "• start_focus_timer：啟動專注計時",
        "• start_break_timer：啟動護眼小憩",
        "• set_schedule：自然語言多階段排程",
        "• add_todo / delete_todo：備忘管理",
        "• get_board_status：即時硬體溫度遙測"
    ], COLOR_CYAN)

    add_card(s4, Inches(6.9), Inches(1.9), Inches(5.6), Inches(4.8), "🔄 跨行程 Bridge RPC 橋接管道", [
        "Unix Domain Socket 通訊：",
        "• 容器透過 /var/run/arduino-router.sock 與板載路由器通訊。",
        "MsgPack 二進制協議封裝：",
        "• 將 104 點陣像素轉化為 bytes(frame) 傳送，成功適配 MCU 端 C++ std::vector<uint8_t>。",
        "表情鎖定保護機制 (_temp_mood_until)：",
        "• 解決了語音講話 speaking 狀態覆蓋愛心或咖啡表情的並行衝突難題，保證動畫完整呈現。"
    ], COLOR_INDIGO)

    # ------------------------------------------------------------- Slide 5: 核心功能一：時程表與番茄鐘
    s5 = prs.slides.add_slide(blank_layout)
    set_bg(s5)
    add_header(s5, "核心功能亮點：專注與休息時程表 (Focus & Break Timeline)")

    add_card(s5, Inches(0.8), Inches(1.9), Inches(5.6), Inches(4.8), "🍅 專注番茄鐘與 ☕ 5分鐘小憩", [
        "專注倒數進度格條：8x13 點陣矩陣隨時間流逝即時點亮 26 格進度光條，專注狀態一目了然。",
        "熱氣蒸騰冒煙咖啡杯：專利雙幀動畫，小憩時點陣呈現熱咖啡杯與裊裊上升的蒸氣。",
        "護眼 20-20-20 伸展指引：小憩觸發時，Gemini 語音溫馨提醒站立活動、遠眺放鬆。",
        "RGB 氛圍光雙重切換：專注紅燈 ➔ 小憩青藍呼吸燈，營造完美的沉浸式辦公氛圍。"
    ], COLOR_AMBER)

    add_card(s5, Inches(6.9), Inches(1.9), Inches(5.6), Inches(4.8), "📅 自然語言時程表排程 (Timeline)", [
        "口語化一鍵排程：在對話框輸入「幫我排時程：25分寫程式、5分小憩、25分複習」，AI 自動結構化解析。",
        "多階段自動無縫銜接：第一階段倒數完成後，系統自動切換至第二階段並切換對應點陣表情與燈光。",
        "一鍵預設情境：提供「⚡ 測試時程 (1分+1分)」與「🍅 經典番茄時程」，方便即時演示與日常工作。",
        "階段手動控制：支援隨時「跳至下一階段」、「隨時暫停」與「手動追加區塊」。"
    ], COLOR_GREEN)

    # ------------------------------------------------------------- Slide 6: 核心功能二：情緒與備忘清單
    s6 = prs.slides.add_slide(blank_layout)
    set_bg(s6)
    add_header(s6, "核心功能亮點：動態表情引擎與備忘清單 (Emotions & Memo)")

    add_card(s6, Inches(0.8), Inches(1.9), Inches(5.6), Inches(4.8), "😊 8x13 擬人化動態表情引擎", [
        "自然定時眨眼笑臉：每 3.5 秒自動眨眼 0.2 秒，宛如桌面上的真實寵物在默默陪伴。",
        "雷達旋轉思考波形：AI 收到訊息並進行神經網路運算時，點陣即時呈現動態旋轉雷達。",
        "撒嬌愛心與大笑反饋：受到讚美時顯現動態心跳愛心 (♥)，給予主人滿滿情緒價值。",
        "定時喝水提醒：長時間工作自動播放水滴降落動畫，呵護身體健康。",
        "睡眠打呼 (Zzz)：夜間或休息狀態進入舒緩打呼動畫。"
    ], COLOR_CYAN)

    add_card(s6, Inches(6.9), Inches(1.9), Inches(5.6), Inches(4.8), "📝 智慧備忘清單與任務管理", [
        "隨手新增待辦：透過聊天對話或快速輸入框，將突發靈感或作業任務即時存檔。",
        "實體點陣打勾慶祝：點擊完成待辦時，8x13 點陣矩陣立即播放立體打勾 (✔) 動畫，激發成就感！",
        "單項快速刪除：每一筆事項皆具備專屬 🗑️ 刪除鍵，維持清單乾淨。",
        "一鍵掃除已完成 (🧹)：一鍵清理所有已劃線完成的事項，保持工作介面高效清爽。",
        "JSON 本地持久化：檔案持久存於板載 eMMC，重啟後待辦事項依然完整保留。"
    ], COLOR_INDIGO)

    # ------------------------------------------------------------- Slide 7: Web 現代化雙向互動儀表板
    s7 = prs.slides.add_slide(blank_layout)
    set_bg(s7)
    add_header(s7, "現代化 Web 雙向互動儀表板 (Interactive Dashboard)")

    add_card(s7, Inches(0.8), Inches(1.9), Inches(3.7), Inches(4.8), "🖥️ 8x13 實體點陣鏡像", [
        "1:1 實時像素鏡像：",
        "• 瀏覽器前端毫秒級同步 UNO Q 實體 LED 矩陣亮度與每一幀動態動畫。",
        "AI 快捷指令互動卡：",
        "• 🍅 1分鐘專注",
        "• ☕ 5分鐘小憩",
        "• 📅 規劃時程",
        "• 💧 提醒喝水",
        "• ❤️ 撒嬌愛心",
        "• 🌡️ 硬體狀態"
    ], COLOR_CYAN)

    add_card(s7, Inches(4.8), Inches(1.9), Inches(3.7), Inches(4.8), "💬 即時對話與語音播放", [
        "全雙工對話氣泡：",
        "• 主人指令與桌寵回答即時以現代化氣泡保留在右下側對話框。",
        "語音播放控制：",
        "• 內建音訊串流播放器，Gemini 語音自動朗讀。",
        "• 提供右上角『🔊 語音開關』，一鍵靜音或恢復語音播報。",
        "工具調用透明化：",
        "• 系統自動將後端執行的工具動作轉化為親切中文回報。"
    ], COLOR_GREEN)

    add_card(s7, Inches(8.8), Inches(1.9), Inches(3.7), Inches(4.8), "🌡️ 板載硬體遙測狀態", [
        "實時晶片健康監控：",
        "• CPU 核心溫度 (℃)",
        "• 系統可用記憶體 (MB)",
        "• 開機運行累計時間",
        "• Linux 系統負載平均值",
        "AI 主動狀態感知：",
        "• 詢問「板子會燙嗎？」，AI 會即時調用工具讀取感測器，回報真實硬體狀況！"
    ], COLOR_AMBER)

    # ------------------------------------------------------------- Slide 8: 技術挑戰與解決方案
    s8 = prs.slides.add_slide(blank_layout)
    set_bg(s8)
    add_header(s8, "關鍵技術挑戰與解決方案 (Technical Challenges)")

    add_card(s8, Inches(0.8), Inches(1.9), Inches(5.6), Inches(2.3), "挑戰 1：跨晶片 Bridge RPC 參數型別適配", [
        "問題：Python 傳遞原生 list 時，MsgPack 轉發出現 RpcError: Wrong type parameter。",
        "解法：嚴格使用 bytes(frame) 二進制型別打包，成功對齊 Zephyr C++ vector<uint8_t> 介面。"
    ], COLOR_CYAN)

    add_card(s8, Inches(6.9), Inches(1.9), Inches(5.6), Inches(2.3), "挑戰 2：多線程動畫與語音講話狀態衝突", [
        "問題：Gemini 回傳音訊時觸發 speaking 狀態，瞬間洗掉愛心與咖啡動畫（不到0.1秒）。",
        "解法：設計 _temp_mood_until 時間保護鎖，鎖定期間常規狀態不得覆蓋特殊情緒。"
    ], COLOR_AMBER)

    add_card(s8, Inches(0.8), Inches(4.4), Inches(5.6), Inches(2.3), "挑戰 3：純文字輸入與 Gemini Live 協議適配", [
        "問題：Gemini 3.8 Live WebSocket 在純文字對話時需兼顧即時工具呼叫與音訊生成。",
        "解法：後端封裝 clientContent 封包，並在工具執行後即時合成精準中文回覆狀態。"
    ], COLOR_GREEN)

    add_card(s8, Inches(6.9), Inches(4.4), Inches(5.6), Inches(2.3), "挑戰 4：免外接感測器的純板載極限壓榨", [
        "優勢：完全無需額外採購感測器或外接麵包板，純利用 UNO Q 板載 8x13 矩陣、RGB 燈與熱感測器達到最高完成度！"
    ], COLOR_INDIGO)

    # ------------------------------------------------------------- Slide 9: 成果總結與未來展望
    s9 = prs.slides.add_slide(blank_layout)
    set_bg(s9)
    add_header(s9, "成果總結與未來展望 (Summary & Roadmap)")

    add_card(s9, Inches(0.8), Inches(1.9), Inches(5.6), Inches(4.8), "🏆 專題成果總結", [
        "100% 達成專案設定指標：成功打造兼具生產力管理與情緒陪伴的實體 AI 桌面伴侶。",
        "技術深度紮實：融合異質雙核心 (Linux + RTOS)、微秒級 Bridge RPC、Gemini Live API、Docker 容器化與 FastAPI 架構。",
        "開源規範嚴密：全專案去識別化，無敏感金鑰洩漏，已發布於 GitHub 公開倉庫。",
        "高實用性與趣味性：冒煙熱咖啡與生動眨眼動畫，在同類物聯網專題中具備極佳的展示效果！"
    ], COLOR_GREEN)

    add_card(s9, Inches(6.9), Inches(1.9), Inches(5.6), Inches(4.8), "🔮 未來功能擴充路線 (Roadmap)", [
        "電腦視覺視線追蹤 (Vision AI)：",
        "• 接入 USB 廣角鏡頭，桌寵眼睛可隨主人坐姿與移動即時追蹤視線。",
        "BLE 穿戴裝置連動 (Smart Wearable)：",
        "• 專注或休息結束時，透過 BLE 將震動提醒即時同步推播至智慧手錶。",
        "環境感測擴充 (Environment Sensing)：",
        "• 透過 Qwiic 介面外接 SHT40 溫濕度或 CO2 感測器，太悶時主動提醒開窗通風。"
    ], COLOR_CYAN)

    prs.save(output_path)
    print(f"Presentation saved successfully to: {output_path}")


if __name__ == "__main__":
    out_file = os.path.join(os.path.dirname(__file__), "AIoT_Midterm_Q-WorkMate.pptx")
    build_presentation(out_file)
