@echo off
chcp 65001 >nul
title 🐾 Q-WorkMate / LumiPet 專案啟動器
cls

echo ================================================================
echo    🐾 Q-WorkMate - Arduino UNO Q AI 桌面生產力桌寵啟動器
echo ================================================================
echo.

set ADB="C:\Users\w2005\AppData\Local\AppLab\a15\data\packages\arduino\tools\adb\32.0.0\adb.exe"

echo [1/4] 檢查 Arduino UNO Q 連線狀態...
%ADB% get-state >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 尚未檢測到 Arduino UNO Q 板子，請確認 USB 傳輸線已妥善連接電腦！
    echo 請接好板子後，按任意鍵繼續檢查...
    pause
)
echo [V] Arduino UNO Q 已連線！
echo.

echo [2/4] 啟動板端點陣硬體橋接與 AI 桌寵容器 (Docker)...
%ADB% shell "docker start smile-matrix-main-1 qpet" >nul 2>&1
echo [V] 板端點陣硬體與 Q-Pet Agent 已啟動！
echo.

echo [3/4] 啟動 Windows 連線代理服務 (Port 7790)...
powershell -Command "if (-not (Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*proxy_7790.py*' })) { Start-Process -WindowStyle Hidden python -ArgumentList 'f:\Antigravity\AIoT_midterm_project\proxy_7790.py' }"
echo [V] 連線轉發代理就緒 (http://localhost:7790)！
echo.

echo [4/4] 開啟 Web 互動儀表板...
timeout /t 2 >nul
start http://localhost:7790

echo.
echo ================================================================
echo    ✨ 啟動成功！儀表板已在預設瀏覽器中開啟。
echo    若要關閉所有服務與板載點陣，可執行 stop_q_workmate.bat
echo ================================================================
echo.
timeout /t 5
